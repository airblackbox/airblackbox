/**
 * `.air-evidence` bundle v1: the signed, self-verifying export.
 *
 * Layout and manifest are the Python SDK's, member for member, so the
 * Python verifier (`air-blackbox verify`) and the browser verifier at
 * https://airblackbox.ai/verify read bundles from either SDK:
 *
 *     manifest.json                 counts, period, anchor, per-file digests, signature
 *     records/actions.jsonl         one canonical record per line, chain order
 *     verification/chain.json       head hash, record list, verification at export
 *     verification/receipts.json    every receipt, with the signing key
 *     verification/public_key.pem   the Ed25519 key as SubjectPublicKeyInfo PEM
 *     mapping/sb26-189.json         which statutory duty each record category evidences
 *
 * The manifest signature covers the SHA-256 of the manifest with the
 * signature removed, serialised compactly with sorted keys; every other
 * member is digested in the manifest, so one signature covers the bundle.
 */
import { createHash, randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import { zipSync } from "fflate";

import { pythonJson, pythonJsonCompact, pythonJsonPretty } from "./canonical.js";
import type { ChainRecord, ChainVerification } from "./chain.js";
import type { AnchorResult } from "./anchor.js";
import { publicKeyPem, type ReceiptSigner } from "./receipt.js";

const SCREENING_ACTIONS = new Set(["advance_candidate", "reject_candidate", "score_candidate", "rank_candidates", "schedule_interview"]);
const ADVERSE_ACTIONS = new Set(["reject_candidate"]);

type Rec = Record<string, unknown>;

function screening(r: Rec): Rec | undefined {
  const s = r["screening"];
  return s && typeof s === "object" ? (s as Rec) : undefined;
}

export function isAdverseDecision(r: Rec): boolean {
  if (ADVERSE_ACTIONS.has(String(r["action"]))) return true;
  return screening(r)?.["decision_type"] === "reject";
}

function reviewer(r: Rec): string {
  return String(screening(r)?.["human_reviewer"] ?? "");
}

export function categorizeRecord(r: Rec): "blocked_action" | "human_approval" | "screening_decision" | "agent_action" {
  if (r["status"] === "blocked") return "blocked_action";
  const action = String(r["action"] ?? "");
  if (action === "human_approval") return "human_approval";
  if ("screening" in r || SCREENING_ACTIONS.has(action)) return "screening_decision";
  return "agent_action";
}

/** Canonical manifest bytes for signing: signature removed, sorted, compact. */
export function canonicalManifestBytes(manifest: Rec): Buffer {
  const { signature: _omit, ...stripped } = manifest;
  return Buffer.from(pythonJsonCompact(stripped), "utf8");
}

/** created + 4 years, Feb 29 clamped to 28 (California FEHA retention floor). */
export function retentionUntil(created: Date, years = 4): string {
  const y = created.getUTCFullYear() + years;
  const m = created.getUTCMonth();
  let d = created.getUTCDate();
  if (m === 1 && d === 29) d = 28;
  return new Date(Date.UTC(y, m, d)).toISOString().slice(0, 10);
}

function sha256(data: string | Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

function loadMapping(): string {
  const file = fileURLToPath(new URL("../mappings/sb26-189.json", import.meta.url));
  return fs.readFileSync(file, "utf8");
}

export interface BundleOptions {
  /** Chained records in write order, each normally carrying a receipt. */
  chainEntries: ChainRecord[];
  tenant: string;
  signer: ReceiptSigner;
  chainVerification: ChainVerification & { fully_intact: boolean };
  system?: { name?: string; high_risk_rationale?: string; deployer?: string };
  anchor?: AnchorManifest;
  outputDir?: string;
}

export type AnchorManifest =
  | { anchored: true; head: string; seq_max: number; tsa_url: string; timestamp?: string; tsr_b64: string }
  | { anchored: false; reason?: string; head?: string; seq_max?: number; error?: string };

export function anchorManifestFrom(result: AnchorResult, seqMax: number): AnchorManifest {
  if (result.ok && result.tsr && result.tsa_url) {
    const m: AnchorManifest = { anchored: true, head: result.head, seq_max: seqMax, tsa_url: result.tsa_url, tsr_b64: result.tsr.toString("base64") };
    if (result.timestamp) m.timestamp = result.timestamp;
    return m;
  }
  return { anchored: false, head: result.head, seq_max: seqMax, error: result.error ?? "unknown" };
}

/** Write a v1 bundle; returns its path and the signed manifest. */
export function generateEvidenceBundleV1(options: BundleOptions): { path: string; manifest: Rec } {
  const { chainEntries, tenant, signer } = options;
  const now = new Date();
  const createdAt = now.toISOString().replace(/\.\d{3}Z$/, "Z");

  // records/actions.jsonl: canonical lines, chain order. Python writes
  // json.dumps(r, sort_keys=True, default=str) and the browser verifier
  // reads the lines as-is, so the canonical form is what goes in.
  let actionsJsonl = chainEntries.map((r) => pythonJson(r)).join("\n");
  if (actionsJsonl) actionsJsonl += "\n";

  const cats = chainEntries.map((r) => categorizeRecord(r as Rec));
  const screeningRecords = chainEntries.filter((_, i) => cats[i] === "screening_decision") as Rec[];
  const adverse = screeningRecords.filter(isAdverseDecision);
  const counts = {
    actions: chainEntries.length,
    screening_decisions: screeningRecords.length,
    blocked_actions: cats.filter((c) => c === "blocked_action").length,
    human_approvals: cats.filter((c) => c === "human_approval").length,
    adverse_decisions: adverse.length,
    adverse_decisions_missing_reviewer: adverse.filter((r) => !reviewer(r)).length,
    engine_outputs_without_reviewer: screeningRecords.filter((r) => !isAdverseDecision(r) && !reviewer(r)).length,
    screening_decisions_missing_reviewer: screeningRecords.filter((r) => !reviewer(r)).length,
  };

  const timestamps = chainEntries.map((r) => String(r.timestamp ?? "")).filter(Boolean).sort();
  const chainDoc = JSON.stringify({
    algorithm: "HMAC-SHA256(key, prev_hash || json.dumps(record_without_chain_hash, sort_keys=True)); prev_hash starts at b'genesis' and advances to the raw digest each step",
    head_hash: chainEntries.length ? String(chainEntries[chainEntries.length - 1]!.chain_hash ?? "") : "",
    records: chainEntries.map((r) => ({ run_id: String(r.run_id ?? ""), chain_hash: String(r.chain_hash ?? "") })),
    verification_at_export: options.chainVerification,
  }, null, 2);

  const receiptsDoc = JSON.stringify({
    signing_method: signer.method,
    public_key_hex: signer.publicKeyHex ?? "",
    note: "Each receipt's authorization_sig covers the canonical authorization payload (receipt_id, agent_id, action_name, action_category, payload_hash, covenant_hash, decision, authorized, parent_receipt_id, created_at) serialized with sort_keys=True. Verifiable with the public key alone.",
    receipts: chainEntries.filter((r) => r["receipt"]).map((r) => ({ run_id: String(r.run_id ?? ""), ...(r["receipt"] as Rec) })),
  }, null, 2);

  const pem = signer.publicKeyHex
    ? publicKeyPem(signer.publicKeyHex)
    : "-----BEGIN AIR PUBLIC KEY HEX-----\n\n-----END AIR PUBLIC KEY HEX-----\n";
  const mappingDoc = loadMapping();

  const files: Record<string, string> = {
    "records/actions.jsonl": sha256(actionsJsonl),
    "verification/chain.json": sha256(chainDoc),
    "verification/receipts.json": sha256(receiptsDoc),
    "verification/public_key.pem": sha256(pem),
    "mapping/sb26-189.json": sha256(mappingDoc),
  };

  const system = options.system ?? {};
  const manifest: Rec = {
    bundle_version: "1.0",
    bundle_id: randomUUID(),
    created_at: createdAt,
    tenant,
    system: {
      name: system.name || "deployer-supplied",
      high_risk_rationale: system.high_risk_rationale || "deployer-supplied",
      deployer: system.deployer || "deployer-supplied",
      period_covered: { from: timestamps[0] ?? "", to: timestamps[timestamps.length - 1] ?? "" },
    },
    counts,
    retention_until: retentionUntil(now),
    retention_note: "4-year floor per California FEHA automated-decision-system record-keeping rules (SB 26-189, which replaced the repealed SB 24-205, sets no explicit retention period); computed from export time.",
    frameworks: ["CO-SB26-189"],
    review_note: "adverse_decisions_missing_reviewer is the compliance-relevant count: decisions that ended a candidacy with no named human reviewer. engine_outputs_without_reviewer counts scoring and ranking, which are inputs to a decision rather than the decision, and are legitimately reviewer-less. screening_decisions_missing_reviewer is the coarse total of both, kept for compatibility with bundles exported before the split.",
    outcome_monitoring: "deployer-supplied",
    anchor: options.anchor ?? { status: "absent" },
    files,
  };

  const digest = sha256(canonicalManifestBytes(manifest));
  manifest["signature"] = {
    alg: signer.method,
    upgrade_path: "ML-DSA-65",
    signed_digest: digest,
    encoding: "hex",
    value: signer.sign(Buffer.from(digest, "hex")),
    public_key_hex: signer.publicKeyHex ?? "",
  };

  const stamp = now.toISOString().replace(/[:T]/g, (c) => (c === "T" ? "-" : "")).slice(0, 17);
  const name = `bundle-${stamp}-${tenant}-${String(manifest["bundle_id"]).slice(0, 8)}.air-evidence`;
  const outDir = options.outputDir ?? ".";
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, name);
  const enc = (s: string): Uint8Array => new Uint8Array(Buffer.from(s, "utf8"));
  const zip = zipSync({
    // Canonical scalars, so the verifier's re-serialisation matches the signed digest.
    "manifest.json": enc(pythonJsonPretty(manifest)),
    "records/actions.jsonl": enc(actionsJsonl),
    "verification/chain.json": enc(chainDoc),
    "verification/receipts.json": enc(receiptsDoc),
    "verification/public_key.pem": enc(pem),
    "mapping/sb26-189.json": enc(mappingDoc),
  }, { level: 6 });
  fs.writeFileSync(outPath, zip);
  return { path: path.resolve(outPath), manifest };
}
