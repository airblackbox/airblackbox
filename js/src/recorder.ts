/**
 * Record what an agent does into a signed evidence file anyone can verify.
 *
 *     import { record } from "air-blackbox";
 *
 *     const rec = record("support-agent");
 *     rec.action("read_ticket", "ticket #4821");
 *     rec.action("issue_refund", "order 991, $40", { humanReviewer: "dana@acme.example" });
 *     const bundle = await rec.export();   // drop it on https://airblackbox.ai/verify
 *
 * Each action is chained (HMAC-SHA256), individually signed (Ed25519), and on
 * export the chain head is timestamped by an external RFC 3161 authority when
 * one is reachable; an unreachable authority is recorded as a gap, never hidden.
 *
 * The chain has exactly one writer by design. Reusing a runs directory
 * continues its chain and keeps its signing identity, so the Python SDK's
 * `air.record("support-agent")` and this recorder can take turns on the same
 * directory and the result still verifies as one history.
 */
import * as fs from "node:fs";
import * as path from "node:path";
import { createHash, randomUUID } from "node:crypto";

import { computeHead, timestampHead, type AnchorResult } from "./anchor.js";
import { anchorManifestFrom, generateEvidenceBundleV1, type AnchorManifest } from "./bundle.js";
import { AuditChain, loadRecords, resolveSigningKey, verifyRecords, type ChainRecord } from "./chain.js";
import { Covenant, type Context, type RuleAction } from "./covenant.js";
import { ActionReceipt, ReceiptSigner, hashPayload } from "./receipt.js";

const KEY_FILE = ".air-receipt-key";

export interface Recorded {
  action: string;
  decision: RuleAction;
  chain_hash: string;
  /** True only when the covenant permits outright; an action needing approval is recorded but not allowed. */
  allowed: boolean;
}

export interface RecorderOptions {
  /** Where records and the signing key live. Default `./air-runs/<name>`. */
  runsDir?: string;
  /** A Covenant, or a path to a covenant YAML. Without one every action is recorded as permitted. */
  covenant?: Covenant | string;
  /** HMAC key for the chain. Defaults to $TRUST_SIGNING_KEY, the colocated keyfile, then the development default. */
  hmacKey?: string;
  /** Timestamp the chain head with an external authority on export. Default true. */
  anchor?: boolean;
  /** Milliseconds to wait per timestamp authority. Default 10000. */
  anchorTimeout?: number;
  /** Timestamp authorities to try, in order. */
  tsaUrls?: string[];
}

export interface ActionOptions {
  /** Who reviewed the decision, if anyone. Bundles flag consequential decisions that lack one. */
  humanReviewer?: string;
  /** Marks a screening decision (advance | reject | rank | recommend) so the bundle counts it. */
  decisionType?: string;
  /** Extra context: passed to the covenant's guards and stored on the record. */
  context?: Context;
  /**
   * Values the covenant's guards may read but which are NOT stored on the
   * record, such as a tool's input fields. Keeps inputs (which may carry
   * personal data) out of the evidence while still letting a rule like
   * `require_approval: issue_refund when: "amount > 100"` see them.
   */
  guard?: Context;
  /**
   * The execution outcome, when the caller knows it: "success", "error", or
   * "blocked" (the action was stopped before it ran). Default: "blocked"
   * when the covenant forbids, otherwise "success".
   */
  status?: "success" | "error" | "blocked";
  /** The framework or hook that observed the action, stored on the record. */
  framework?: string;
}

/** Fields an observation record (model call, tool call seen by a hook) carries. */
export interface ObservationFields {
  [key: string]: unknown;
}

function loadOrCreateSigner(runsDir: string): ReceiptSigner {
  const file = path.join(runsDir, KEY_FILE);
  if (fs.existsSync(file)) {
    try {
      const doc = JSON.parse(fs.readFileSync(file, "utf8")) as { algorithm?: string; seed?: string };
      if (doc.algorithm === "ed25519" && doc.seed) return new ReceiptSigner({ privateKey: Buffer.from(doc.seed, "hex") });
    } catch {
      /* fall through to the refusal below */
    }
    // Never overwrite an existing key: replacing it would rotate the identity
    // every earlier receipt in this directory was signed under.
    throw new Error(`${file} exists but is not an Ed25519 key this recorder can use. Point runsDir at a fresh directory rather than replacing it.`);
  }
  const signer = new ReceiptSigner();
  fs.writeFileSync(file, JSON.stringify({ algorithm: "ed25519", seed: signer.seed!.toString("hex") }), { mode: 0o600, flag: "wx" });
  return signer;
}

export class Recorder {
  readonly name: string;
  readonly runsDir: string;
  readonly covenant?: Covenant;
  readonly anchor: boolean;
  readonly anchorTimeout: number;
  readonly tsaUrls?: string[];
  bundlePath?: string;
  lastExportNote = "";
  private readonly chain: AuditChain;
  private readonly signer: ReceiptSigner;
  private readonly hmacKey?: string;
  private written = 0;

  constructor(name = "agent", options: RecorderOptions = {}) {
    this.name = name;
    this.runsDir = options.runsDir ?? path.join("air-runs", name);
    fs.mkdirSync(this.runsDir, { recursive: true });
    this.covenant = typeof options.covenant === "string" ? Covenant.fromYaml(options.covenant) : options.covenant;
    this.anchor = options.anchor ?? true;
    this.anchorTimeout = options.anchorTimeout ?? 10000;
    this.tsaUrls = options.tsaUrls;
    this.hmacKey = options.hmacKey;
    this.chain = new AuditChain(this.runsDir, options.hmacKey, true);
    this.signer = loadOrCreateSigner(this.runsDir);
  }

  /** The signer's public key (hex). */
  get publicKeyHex(): string {
    return this.signer.publicKeyHex ?? "";
  }

  /**
   * The short identity an auditor pins, e.g. `ed25519:10ba682c8ad13513`:
   * what `air-blackbox verify --expect-key` and the browser verifier show.
   */
  get fingerprint(): string {
    const pub = this.publicKeyHex;
    if (!pub) return this.signer.method;
    return `${this.signer.method}:${createHash("sha256").update(Buffer.from(pub, "hex")).digest("hex").slice(0, 16)}`;
  }

  get recordCount(): number {
    return this.written;
  }

  /**
   * Record one action. With a covenant loaded the name must match a rule, or
   * it is recorded as forbidden under default-deny. This records; it does not
   * intercept. Read `allowed` and honour it.
   */
  action(name: string, detail = "", options: ActionOptions = {}): Recorded {
    const context = options.context ?? {};
    const decision: RuleAction = this.covenant
      ? this.covenant.evaluate(name, { detail, ...(options.guard ?? {}), ...context })
      : "permit";
    const record: ChainRecord = {
      run_id: randomUUID(),
      timestamp: new Date().toISOString(),
      type: "agent_action",
      action: name,
      detail: detail.slice(0, 2000),
      status: options.status ?? (decision === "forbid" ? "blocked" : "success"),
      covenant_decision: decision,
    };
    if (options.framework) record["framework"] = options.framework;
    if (Object.keys(context).length) record["context"] = context;
    let category = "";
    if (options.decisionType || options.humanReviewer) {
      category = "screening";
      const screening: Record<string, string> = { decision_type: options.decisionType ?? name };
      if (options.humanReviewer) screening["human_reviewer"] = options.humanReviewer.slice(0, 100);
      record["screening"] = screening;
    }
    if (this.covenant) record["covenant_hash"] = this.covenant.hash;
    const receipt = new ActionReceipt({
      agent_id: this.name,
      action_name: name,
      action_category: category,
      payload_hash: detail ? hashPayload(detail) : "",
      covenant_hash: this.covenant?.hash ?? "",
      decision,
      authorized: decision === "permit",
    });
    this.signer.signAuthorization(receipt);
    record["receipt"] = receipt.toDict();
    const chainHash = this.chain.write(record);
    this.written++;
    return { action: name, decision, chain_hash: chainHash, allowed: decision === "permit" };
  }

  /**
   * Record something observed rather than decided: a model call a hook saw,
   * a tool call a callback reported. No covenant evaluation, no receipt;
   * these are the records the Python trust layers write.
   */
  observe(type: string, fields: ObservationFields = {}): string {
    const record: ChainRecord = { run_id: randomUUID(), timestamp: new Date().toISOString(), type, ...fields };
    const chainHash = this.chain.write(record);
    this.written++;
    return chainHash;
  }

  /** Verify the chain this recorder writes to, as the Python verifier would. */
  verify(): ReturnType<typeof verifyRecords> {
    return verifyRecords(loadRecords(this.runsDir), resolveSigningKey(this.runsDir, this.hmacKey));
  }

  /**
   * Write a signed `.air-evidence` bundle and return its path. The chain is
   * verified first and the result is stamped into the signed manifest, so a
   * bundle never quietly attests a broken history.
   */
  async export(outputDir?: string): Promise<string> {
    const records = loadRecords(this.runsDir);
    const verification = this.verify();
    const fullyIntact = verification.intact && verification.verified_records === records.length;
    const chained = records.filter((r) => r.chain_hash);
    const seqMax = chained.reduce((m, r) => Math.max(m, Number(r.chain_seq ?? 0)), 0);

    let anchor: AnchorManifest;
    if (!this.anchor) {
      anchor = { anchored: false, reason: "anchoring disabled" };
    } else {
      const head = computeHead(this.runsDir);
      if (!head) {
        anchor = { anchored: false, reason: "no records" };
      } else {
        const result: AnchorResult = await timestampHead(head, this.tsaUrls, this.anchorTimeout);
        this.lastExportNote = result.ok ? `timestamped by ${result.tsa_url}` : `no external timestamp: ${result.error}`;
        anchor = anchorManifestFrom(result, seqMax);
      }
    }

    const { path: bundlePath } = generateEvidenceBundleV1({
      chainEntries: chained,
      tenant: this.name,
      signer: this.signer,
      chainVerification: { fully_intact: fullyIntact, ...verification },
      system: { name: this.name, high_risk_rationale: "", deployer: "" },
      anchor,
      outputDir: outputDir ?? this.runsDir,
    });
    this.bundlePath = bundlePath;
    return bundlePath;
  }

  /** Export if anything was recorded. For `await using rec = record(...)`. */
  async [Symbol.asyncDispose](): Promise<void> {
    if (this.written) await this.export();
  }
}

/** Start recording an agent. */
export function record(name = "agent", options: RecorderOptions = {}): Recorder {
  return new Recorder(name, options);
}
