/**
 * `.air-evidence` bundle v1: the signed, self-verifying export.
 *
 * Layout and manifest are the Python SDK's, member for member, so the
 * Python verifier (`air-evidence verify`) and the browser verifier at
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
import { createHash, randomUUID, type Hash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

import { Zip, ZipDeflate, zipSync } from "fflate";

import { parsePreserving, pythonJson, pythonJsonCompact, pythonJsonPretty } from "./canonical.js";
import { chainStep, GENESIS_DIGEST, Pacer, type ChainRecord, type ChainVerification, type RecordIndexEntry } from "./chain.js";
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

const CHAIN_ALGORITHM = "HMAC-SHA256(key, prev_hash || json.dumps(record_without_chain_hash, sort_keys=True)); prev_hash starts at b'genesis' and advances to the raw digest each step";
const RECEIPTS_NOTE = "Each receipt's authorization_sig covers the canonical authorization payload (receipt_id, agent_id, action_name, action_category, payload_hash, covenant_hash, decision, authorized, parent_receipt_id, created_at) serialized with sort_keys=True. Verifiable with the public key alone.";

/** The manifest's counts, accumulated one record at a time. */
class Counts {
  private actions = 0;
  private screening = 0;
  private blocked = 0;
  private approvals = 0;
  private adverse = 0;
  private adverseNoReviewer = 0;
  private engineNoReviewer = 0;
  private screeningNoReviewer = 0;
  private first = "";
  private last = "";

  add(r: Rec): void {
    this.actions++;
    const cat = categorizeRecord(r);
    if (cat === "blocked_action") this.blocked++;
    else if (cat === "human_approval") this.approvals++;
    else if (cat === "screening_decision") {
      this.screening++;
      const named = !!reviewer(r);
      if (!named) this.screeningNoReviewer++;
      if (isAdverseDecision(r)) {
        this.adverse++;
        if (!named) this.adverseNoReviewer++;
      } else if (!named) this.engineNoReviewer++;
    }
    const ts = String(r["timestamp"] ?? "");
    if (ts) {
      if (!this.first || ts < this.first) this.first = ts;
      if (!this.last || ts > this.last) this.last = ts;
    }
  }

  get counts(): Rec {
    return {
      actions: this.actions,
      screening_decisions: this.screening,
      blocked_actions: this.blocked,
      human_approvals: this.approvals,
      adverse_decisions: this.adverse,
      adverse_decisions_missing_reviewer: this.adverseNoReviewer,
      engine_outputs_without_reviewer: this.engineNoReviewer,
      screening_decisions_missing_reviewer: this.screeningNoReviewer,
    };
  }

  get period(): { from: string; to: string } {
    return { from: this.first, to: this.last };
  }
}

function pemFor(signer: ReceiptSigner): string {
  return signer.publicKeyHex
    ? publicKeyPem(signer.publicKeyHex)
    : "-----BEGIN AIR PUBLIC KEY HEX-----\n\n-----END AIR PUBLIC KEY HEX-----\n";
}

/** The manifest, signed: everything but the member digests is fixed by the format. */
function signedManifest(args: {
  now: Date; tenant: string; system: BundleOptions["system"]; counts: Rec; period: { from: string; to: string };
  anchor?: AnchorManifest; files: Record<string, string>; signer: ReceiptSigner;
}): Rec {
  const system = args.system ?? {};
  const manifest: Rec = {
    bundle_version: "1.0",
    bundle_id: randomUUID(),
    created_at: args.now.toISOString().replace(/\.\d{3}Z$/, "Z"),
    tenant: args.tenant,
    system: {
      name: system.name || "deployer-supplied",
      high_risk_rationale: system.high_risk_rationale || "deployer-supplied",
      deployer: system.deployer || "deployer-supplied",
      period_covered: args.period,
    },
    counts: args.counts,
    retention_until: retentionUntil(args.now),
    retention_note: "4-year floor per California FEHA automated-decision-system record-keeping rules (SB 26-189, which replaced the repealed SB 24-205, sets no explicit retention period); computed from export time.",
    frameworks: ["CO-SB26-189"],
    review_note: "adverse_decisions_missing_reviewer is the compliance-relevant count: decisions that ended a candidacy with no named human reviewer. engine_outputs_without_reviewer counts scoring and ranking, which are inputs to a decision rather than the decision, and are legitimately reviewer-less. screening_decisions_missing_reviewer is the coarse total of both, kept for compatibility with bundles exported before the split.",
    outcome_monitoring: "deployer-supplied",
    anchor: args.anchor ?? { status: "absent" },
    files: args.files,
  };
  const digest = sha256(canonicalManifestBytes(manifest));
  manifest["signature"] = {
    alg: args.signer.method,
    upgrade_path: "ML-DSA-65",
    signed_digest: digest,
    encoding: "hex",
    value: args.signer.sign(Buffer.from(digest, "hex")),
    public_key_hex: args.signer.publicKeyHex ?? "",
  };
  return manifest;
}

function bundleFileName(now: Date, tenant: string, bundleId: string): string {
  const stamp = now.toISOString().replace(/[:T]/g, (c) => (c === "T" ? "-" : "")).slice(0, 17);
  // The tenant is a recorder name ("acme/support" is a fine name): keep it
  // to file-name characters so it cannot point the bundle somewhere else.
  const safeTenant = tenant.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 80) || "agent";
  return `bundle-${stamp}-${safeTenant}-${bundleId.slice(0, 8)}.air-evidence`;
}

/**
 * JSON.stringify(value, null, 2) as it would appear nested `depth` levels
 * deep inside another JSON.stringify(_, null, 2) document.
 */
function nestedJson(value: unknown, depth: number): string {
  return JSON.stringify(value, null, 2).replace(/\n/g, "\n" + "  ".repeat(depth));
}

/**
 * Write a v1 bundle from records already in memory; returns its path and the
 * signed manifest. Recorder.export streams from the runs directory instead
 * (streamEvidenceBundleV1); the two write the same members byte for byte.
 */
export function generateEvidenceBundleV1(options: BundleOptions): { path: string; manifest: Rec } {
  const { chainEntries, tenant, signer } = options;
  const now = new Date();

  // records/actions.jsonl: canonical lines, chain order. Python writes
  // json.dumps(r, sort_keys=True, default=str) and the browser verifier
  // reads the lines as-is, so the canonical form is what goes in.
  let actionsJsonl = chainEntries.map((r) => pythonJson(r)).join("\n");
  if (actionsJsonl) actionsJsonl += "\n";

  const tally = new Counts();
  for (const r of chainEntries) tally.add(r as Rec);

  const chainDoc = JSON.stringify({
    algorithm: CHAIN_ALGORITHM,
    head_hash: chainEntries.length ? String(chainEntries[chainEntries.length - 1]!.chain_hash ?? "") : "",
    records: chainEntries.map((r) => ({ run_id: String(r.run_id ?? ""), chain_hash: String(r.chain_hash ?? "") })),
    verification_at_export: options.chainVerification,
  }, null, 2);

  const receiptsDoc = JSON.stringify({
    signing_method: signer.method,
    public_key_hex: signer.publicKeyHex ?? "",
    note: RECEIPTS_NOTE,
    receipts: chainEntries.filter((r) => r["receipt"]).map((r) => ({ run_id: String(r.run_id ?? ""), ...(r["receipt"] as Rec) })),
  }, null, 2);

  const pem = pemFor(signer);
  const mappingDoc = loadMapping();

  const files: Record<string, string> = {
    "records/actions.jsonl": sha256(actionsJsonl),
    "verification/chain.json": sha256(chainDoc),
    "verification/receipts.json": sha256(receiptsDoc),
    "verification/public_key.pem": sha256(pem),
    "mapping/sb26-189.json": sha256(mappingDoc),
  };

  const manifest = signedManifest({ now, tenant, system: options.system, counts: tally.counts, period: tally.period, anchor: options.anchor, files, signer });

  const outDir = options.outputDir ?? ".";
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, bundleFileName(now, tenant, String(manifest["bundle_id"])));
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

export interface StreamBundleOptions {
  runsDir: string;
  /** The directory's index in verification order (indexRecords). */
  entries: RecordIndexEntry[];
  /** Record files the index could not read; reported, and the bundle marked not intact. */
  unreadable: string[];
  /** HMAC key for the chain, to verify while writing. */
  signingKey: string;
  tenant: string;
  signer: ReceiptSigner;
  system?: BundleOptions["system"];
  anchor?: AnchorManifest;
  outputDir?: string;
  /** Further reasons the history is incomplete (the recorder's own head check). */
  problems?: string[];
  /**
   * The export gives the event loop a turn whenever about 20 ms of work has
   * gone by; this also caps the records between turns. Default: no cap.
   */
  yieldEvery?: number;
}

const CHUNK = 1 << 16;

/** One zip member, written through a streaming deflater with a running SHA-256. */
class StreamMember {
  private readonly file: ZipDeflate;
  private readonly hash: Hash = createHash("sha256");
  private pending: string[] = [];
  private pendingLength = 0;

  constructor(zip: Zip, name: string) {
    this.file = new ZipDeflate(name, { level: 6 });
    zip.add(this.file);
  }

  write(text: string): void {
    this.pending.push(text);
    this.pendingLength += text.length;
    if (this.pendingLength >= CHUNK) this.flush(false);
  }

  writeBytes(bytes: Buffer): void {
    this.flush(false);
    this.hash.update(bytes);
    this.file.push(new Uint8Array(bytes), false);
  }

  private flush(final: boolean): void {
    const bytes = Buffer.from(this.pending.join(""), "utf8");
    this.pending = [];
    this.pendingLength = 0;
    this.hash.update(bytes);
    if (bytes.length || final) this.file.push(new Uint8Array(bytes), final);
  }

  end(): string {
    this.flush(true);
    return this.hash.digest("hex");
  }
}

/**
 * Write a v1 bundle straight from a runs directory, one record at a time:
 * memory stays proportional to the index (a run id and hash per record), not
 * the records, and the event loop gets a turn every 20 ms or so.
 * The chain is verified while it is written, and the result stamped into
 * chain.json. Members are byte for byte what generateEvidenceBundleV1 writes
 * for the same records; manifest.json comes last in the archive, since it
 * signs the others' digests.
 */
export async function streamEvidenceBundleV1(options: StreamBundleOptions): Promise<{ path: string; manifest: Rec; verification: ChainVerification & { fully_intact: boolean; problems?: string[] } }> {
  const { runsDir, entries, signer, tenant } = options;
  const unreadable = [...options.unreadable];
  const pacer = new Pacer(options.yieldEvery);
  const now = new Date();
  const outDir = options.outputDir ?? ".";
  fs.mkdirSync(outDir, { recursive: true });
  const work = fs.mkdtempSync(path.join(outDir, ".air-export-"));
  const partial = path.join(work, "bundle.partial");
  const receiptsTmp = path.join(work, "receipts.part");
  // Each descriptor is closed exactly once: the export pauses, and a number
  // closed twice may by then belong to a file the agent has opened.
  const open = new Set<number>();
  const openFile = (file: string, flags: string): number => {
    const fd = fs.openSync(file, flags);
    open.add(fd);
    return fd;
  };
  const closeFile = (fd: number): void => {
    if (open.delete(fd)) fs.closeSync(fd);
  };
  const out = openFile(partial, "w");
  const receiptsOut = openFile(receiptsTmp, "w");
  try {
    let zipError: unknown;
    let zipDone = false;
    const zip = new Zip((err, chunk, final) => {
      if (err) zipError = err;
      else fs.writeSync(out, chunk);
      if (final) zipDone = true;
    });

    // records/actions.jsonl, verifying the chain as it goes.
    const actions = new StreamMember(zip, "records/actions.jsonl");
    const key = Buffer.from(options.signingKey, "utf8");
    let prev: Buffer = GENESIS_DIGEST;
    let verified = 0;
    let withHash = 0;
    let firstBreak: { at: number; runId: string } | undefined;
    const tally = new Counts();
    const written: Array<[string, string]> = [];
    let receipts = 0;
    // Receipts go to a side file in 64 KB writes, and into the archive after
    // chain.json, as the in-memory export orders the members.
    let receiptsPending: string[] = [];
    let receiptsPendingLength = 0;
    const flushReceipts = (): void => {
      fs.writeSync(receiptsOut, receiptsPending.join(""));
      receiptsPending = [];
      receiptsPendingLength = 0;
    };
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i]!;
      if (pacer.due()) await pacer.pause();
      if (!e.chainHash) continue;
      let rec: ChainRecord;
      try {
        rec = parsePreserving(fs.readFileSync(path.join(runsDir, e.file), "utf8")) as ChainRecord;
      } catch {
        unreadable.push(e.file); // changed or removed since it was indexed
        continue;
      }
      if (!rec || typeof rec !== "object" || Array.isArray(rec)) {
        unreadable.push(e.file);
        continue;
      }
      if (!rec.chain_hash) continue; // rewritten outside the chain since it was indexed
      if (!firstBreak) {
        const step = chainStep(key, prev, rec);
        withHash++;
        if (step.ok) {
          verified++;
          prev = step.digest;
        } else {
          firstBreak = { at: i, runId: String(rec.run_id ?? "") };
        }
      }
      actions.write(pythonJson(rec) + "\n");
      tally.add(rec as Rec);
      written.push([String(rec.run_id ?? ""), String(rec.chain_hash ?? "")]);
      if (rec["receipt"]) {
        const item = { run_id: String(rec.run_id ?? ""), ...(rec["receipt"] as Rec) };
        const text = (receipts++ ? ",\n" : "") + "    " + nestedJson(item, 2);
        receiptsPending.push(text);
        receiptsPendingLength += text.length;
        if (receiptsPendingLength >= CHUNK) flushReceipts();
      }
    }
    flushReceipts();
    const actionsDigest = actions.end();
    closeFile(receiptsOut);

    const problems = [...(options.problems ?? [])];
    if (unreadable.length) problems.unshift(`${unreadable.length} record file(s) could not be read: ${unreadable.slice(0, 3).join(", ")}`);
    // Key order as the in-memory export writes it: fully_intact first.
    const verification: ChainVerification & { fully_intact: boolean; problems?: string[] } = {
      fully_intact: !firstBreak && verified === entries.length && problems.length === 0,
      intact: !firstBreak,
      total_records: entries.length,
      verified_records: verified,
      records_with_hash: withHash,
      ...(firstBreak ? { first_break_at: firstBreak.at, first_break_run_id: firstBreak.runId } : {}),
    };
    if (problems.length) {
      // Stamped as a break, so verifiers fail the bundle and say why.
      verification.intact = false;
      verification.first_break_at ??= written.length;
      verification.problems = problems;
    }

    // verification/chain.json, as JSON.stringify(doc, null, 2) would write it.
    const chain = new StreamMember(zip, "verification/chain.json");
    chain.write(`{\n  "algorithm": ${JSON.stringify(CHAIN_ALGORITHM)},\n  "head_hash": ${JSON.stringify(written.length ? written[written.length - 1]![1] : "")},\n  "records": `);
    if (!written.length) chain.write("[]");
    else {
      chain.write("[\n");
      for (let i = 0; i < written.length; i++) {
        if (pacer.due()) await pacer.pause();
        const [runId, hash] = written[i]!;
        chain.write(`${i ? ",\n" : ""}    {\n      "run_id": ${JSON.stringify(runId)},\n      "chain_hash": ${JSON.stringify(hash)}\n    }`);
      }
      chain.write("\n  ]");
    }
    chain.write(`,\n  "verification_at_export": ${nestedJson(verification, 1)}\n}`);
    const chainDigest = chain.end();

    // verification/receipts.json, from the receipts gathered on the way.
    const receiptsMember = new StreamMember(zip, "verification/receipts.json");
    receiptsMember.write(`{\n  "signing_method": ${JSON.stringify(signer.method)},\n  "public_key_hex": ${JSON.stringify(signer.publicKeyHex ?? "")},\n  "note": ${JSON.stringify(RECEIPTS_NOTE)},\n  "receipts": `);
    if (!receipts) receiptsMember.write("[]");
    else {
      receiptsMember.write("[\n");
      const fd = openFile(receiptsTmp, "r");
      try {
        const buf = Buffer.alloc(CHUNK);
        for (let n; (n = fs.readSync(fd, buf, 0, CHUNK, null)) > 0; ) {
          receiptsMember.writeBytes(Buffer.from(buf.subarray(0, n)));
          if (pacer.due()) await pacer.pause();
        }
      } finally {
        closeFile(fd);
      }
      receiptsMember.write("\n  ]");
    }
    receiptsMember.write("\n}");
    const receiptsDigest = receiptsMember.end();

    const small = (name: string, text: string): string => {
      const m = new StreamMember(zip, name);
      m.write(text);
      return m.end();
    };
    const files: Record<string, string> = {
      "records/actions.jsonl": actionsDigest,
      "verification/chain.json": chainDigest,
      "verification/receipts.json": receiptsDigest,
      "verification/public_key.pem": small("verification/public_key.pem", pemFor(signer)),
      "mapping/sb26-189.json": small("mapping/sb26-189.json", loadMapping()),
    };
    const manifest = signedManifest({ now, tenant, system: options.system, counts: tally.counts, period: tally.period, anchor: options.anchor, files, signer });
    // Canonical scalars, so the verifier's re-serialisation matches the signed digest.
    small("manifest.json", pythonJsonPretty(manifest));
    zip.end();
    if (zipError) throw zipError;
    if (!zipDone) throw new Error("the archive did not finish writing");
    closeFile(out);

    const outPath = path.resolve(outDir, bundleFileName(now, tenant, String(manifest["bundle_id"])));
    fs.renameSync(partial, outPath);
    return { path: outPath, manifest, verification };
  } finally {
    for (const fd of [...open]) {
      try {
        closeFile(fd);
      } catch {
        /* already gone; the work directory is removed below */
      }
    }
    fs.rmSync(work, { recursive: true, force: true });
  }
}
