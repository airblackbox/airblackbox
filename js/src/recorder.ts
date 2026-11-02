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
import * as os from "node:os";
import * as path from "node:path";
import { createHash, randomUUID } from "node:crypto";

import { headOfIndex, timestampHead, type AnchorResult } from "./anchor.js";
import { anchorManifestFrom, streamEvidenceBundleV1, type AnchorManifest } from "./bundle.js";
import { AuditChain, indexRecordsPaced, resolveSigningKey, verifyChain, type ChainRecord, type ChainVerification } from "./chain.js";
import { Covenant, type Context, type RuleAction } from "./covenant.js";
import { ActionReceipt, ReceiptSigner, hashPayload } from "./receipt.js";

const KEY_FILE = ".air-receipt-key";
const LOCK_FILE = ".air-writer.lock";

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
  /**
   * Called when a framework hook could not record something. Hooks never let
   * a recording failure break the agent's own work (the tool has already
   * run); without this callback the first failure is logged with
   * console.warn and later ones are only counted in `recordErrors`.
   */
  onRecordError?: (error: unknown) => void;
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
  for (let attempt = 0; attempt < 3; attempt++) {
    let text: string;
    try {
      text = fs.readFileSync(file, "utf8");
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== "ENOENT") {
        throw new Error(`cannot read ${file} (${(e as Error).message}). It holds this directory's signing identity: fix its permissions rather than replacing it.`);
      }
      const created = createKeyFile(file);
      if (created) return created;
      continue; // another process created it first: use theirs
    }
    try {
      const doc = JSON.parse(text) as { algorithm?: string; seed?: string };
      if (doc.algorithm === "ed25519" && doc.seed) return new ReceiptSigner({ privateKey: Buffer.from(doc.seed, "hex") });
    } catch {
      /* fall through to the refusal below */
    }
    // Never overwrite an existing key: replacing it would rotate the identity
    // every earlier receipt in this directory was signed under.
    throw new Error(`${file} exists but is not an Ed25519 key this recorder can use. Point runsDir at a fresh directory rather than replacing it.`);
  }
  throw new Error(`could not create or read ${file}`);
}

/**
 * Create the key file atomically: written whole under a temporary name, then
 * hard-linked into place, so a process starting at the same moment never
 * reads half a key and two creators cannot both win. Returns undefined when
 * another process got there first.
 */
function createKeyFile(file: string): ReceiptSigner | undefined {
  const signer = new ReceiptSigner();
  const body = JSON.stringify({ algorithm: "ed25519", seed: signer.seed!.toString("hex") });
  const tmp = `${file}.${process.pid}.${randomUUID()}.tmp`;
  fs.writeFileSync(tmp, body, { mode: 0o600, flag: "wx" });
  try {
    fs.linkSync(tmp, file);
    return signer;
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "EEXIST") return undefined;
    // A filesystem without hard links: an exclusive create is still safe
    // against overwriting, if not against a reader racing the write.
    try {
      fs.writeFileSync(file, body, { mode: 0o600, flag: "wx" });
      return signer;
    } catch (e2) {
      if ((e2 as NodeJS.ErrnoException).code === "EEXIST") return undefined;
      throw e2;
    }
  } finally {
    fs.rmSync(tmp, { force: true });
  }
}

// One chain per runs directory per process: Recorders opened on the same
// directory (a recorder per request, say) append to one history instead of
// forking it.
const chains = new Map<string, { chain: AuditChain; key: string; users: number }>();
const heldLocks = new Set<string>();
let exitHookInstalled = false;

function sharedChain(runsDir: string, hmacKey: string | undefined): { chain: AuditChain; dir: string } {
  const dir = fs.realpathSync(runsDir);
  const key = resolveSigningKey(runsDir, hmacKey);
  const existing = chains.get(dir);
  if (existing) {
    if (existing.key !== key) throw new Error(`${runsDir} is already being recorded in this process with a different HMAC key`);
    existing.chain.syncWithDisk();
    existing.users++;
    return { chain: existing.chain, dir };
  }
  acquireWriterLock(dir);
  const chain = new AuditChain(runsDir, hmacKey, true);
  chains.set(dir, { chain, key, users: 1 });
  return { chain, dir };
}

/** One Recorder on `dir` is done; the last one out releases the directory. */
function releaseChain(dir: string): void {
  const entry = chains.get(dir);
  if (!entry || --entry.users > 0) return;
  chains.delete(dir);
  if (heldLocks.delete(dir)) {
    try {
      fs.rmSync(path.join(dir, LOCK_FILE), { force: true });
    } catch {
      /* the directory is gone */
    }
  }
}

/**
 * The chain has one writer at a time. Two processes appending to one
 * directory fork it, and the fork only shows when the evidence fails to
 * verify, so a second process on this machine is refused up front. A lock
 * left by a process that has exited is taken over. This narrows the ways to
 * fork a chain; it is not a distributed mutex (two processes taking over the
 * same stale lock at the same instant can both proceed).
 */
function acquireWriterLock(dir: string): void {
  if (heldLocks.has(dir)) return;
  const file = path.join(dir, LOCK_FILE);
  const mine = JSON.stringify({ pid: process.pid, host: os.hostname(), started: new Date().toISOString() });
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      fs.writeFileSync(file, mine, { flag: "wx" });
      heldLocks.add(dir);
      installExitHook();
      return;
    } catch (e) {
      const code = (e as NodeJS.ErrnoException).code;
      if (code !== "EEXIST") return; // cannot lock (read-only, say): writing will report its own errors
    }
    let holder: { pid?: number; host?: string } = {};
    try {
      holder = JSON.parse(fs.readFileSync(file, "utf8")) as typeof holder;
    } catch {
      /* unreadable lock: treat as stale */
    }
    if (holder.pid && holder.host && holder.host !== os.hostname()) {
      // Liveness cannot be checked across machines (a shared volume).
      console.warn(`AIR Blackbox: taking over ${file}, held by process ${holder.pid} on ${holder.host}. ` +
        "If that machine is still recording into this directory, the chain will fork.");
    } else if (holder.pid && holder.pid !== process.pid && processAlive(holder.pid)) {
      throw new Error(
        `${dir} is being recorded by process ${holder.pid}. A chain has one writer at a time: give each process its own ` +
          `runsDir, send records through the ingest server, or have that process call close() on its recorder when it ` +
          `is done. If no such process is running, delete ${file}.`,
      );
    }
    fs.rmSync(file, { force: true }); // stale, or left by this process
  }
}

function processAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return (e as NodeJS.ErrnoException).code === "EPERM";
  }
}

function installExitHook(): void {
  if (exitHookInstalled) return;
  exitHookInstalled = true;
  process.once("exit", () => {
    for (const dir of heldLocks) {
      try {
        fs.rmSync(path.join(dir, LOCK_FILE), { force: true });
      } catch {
        // The directory is gone or replaced: nothing left to unlock, and an
        // exit hook must never turn a clean exit into a crash.
      }
    }
  });
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
  /** Recording failures the hooks absorbed so the agent could carry on. */
  recordErrors = 0;
  private readonly chain: AuditChain;
  private readonly chainDir: string;
  private closed = false;
  private readonly signer: ReceiptSigner;
  // A true private field, so console.log(recorder) cannot print the key.
  readonly #hmacKey?: string;
  private readonly onRecordError?: (error: unknown) => void;
  private written = 0;

  constructor(name = "agent", options: RecorderOptions = {}) {
    this.name = name;
    this.runsDir = options.runsDir ?? path.join("air-runs", name);
    fs.mkdirSync(this.runsDir, { recursive: true });
    this.covenant = typeof options.covenant === "string" ? Covenant.fromYaml(options.covenant) : options.covenant;
    this.anchor = options.anchor ?? true;
    this.anchorTimeout = options.anchorTimeout ?? 10000;
    this.tsaUrls = options.tsaUrls;
    this.#hmacKey = options.hmacKey;
    this.onRecordError = options.onRecordError;
    this.signer = loadOrCreateSigner(this.runsDir);
    const shared = sharedChain(this.runsDir, options.hmacKey);
    this.chain = shared.chain;
    this.chainDir = shared.dir;
  }

  /**
   * Done recording: hand the directory back so another process can continue
   * the chain while this one keeps running. Recording after close() throws.
   * (A process that exits releases its directories anyway.)
   */
  close(): void {
    if (this.closed) return;
    this.closed = true;
    releaseChain(this.chainDir);
  }

  private assertOpen(): void {
    if (this.closed) throw new Error(`recorder ${this.name} is closed`);
  }

  /**
   * How a hook reports a record it could not write. Hooks call this instead
   * of letting the failure reach the agent.
   */
  reportRecordError(error: unknown): void {
    this.recordErrors++;
    if (this.onRecordError) {
      try {
        this.onRecordError(error);
      } catch {
        /* a failing callback must not break the agent either */
      }
      return;
    }
    if (this.recordErrors === 1) {
      console.warn(`AIR Blackbox (${this.name}): could not record an action: ${error instanceof Error ? error.message : String(error)}. ` +
        "The agent was not interrupted; later failures are counted in recordErrors. Pass onRecordError to handle them.");
    }
  }

  /** The signer's public key (hex). */
  get publicKeyHex(): string {
    return this.signer.publicKeyHex ?? "";
  }

  /**
   * The short identity an auditor pins, e.g. `ed25519:10ba682c8ad13513`:
   * what `air-evidence verify --expect-key` and the browser verifier show.
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
    this.assertOpen();
    if (typeof detail !== "string") detail = String(detail ?? "");
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
      if (options.humanReviewer) screening["human_reviewer"] = String(options.humanReviewer).slice(0, 100);
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
    this.assertOpen();
    // The writer's fields last: a field named run_id would otherwise choose
    // the record's file name (and could overwrite another record).
    const record: ChainRecord = { ...fields, run_id: randomUUID(), timestamp: new Date().toISOString(), type };
    const chainHash = this.chain.write(record);
    this.written++;
    return chainHash;
  }

  /** Verify the chain this recorder writes to, as the Python verifier would. */
  verify(): ChainVerification {
    return verifyChain(this.runsDir, resolveSigningKey(this.runsDir, this.#hmacKey));
  }

  /**
   * Write a signed `.air-evidence` bundle and return its path. The chain is
   * verified as the bundle is written and the result is stamped into the
   * signed manifest, so a bundle never quietly attests a broken history.
   *
   * The export streams from the runs directory a record at a time, so a long
   * history costs an index entry per record in memory rather than the
   * records, and the agent keeps running while it is written. It covers the
   * records on disk when it starts; anything recorded meanwhile goes in the
   * next export.
   */
  async export(outputDir?: string): Promise<string> {
    const { entries, unreadable } = await indexRecordsPaced(this.runsDir);
    const chained = entries.filter((e) => e.chainHash);
    // This process knows the head it wrote. If the newest record on disk is
    // not it, records were removed after they were written; and a record
    // file that cannot be read is a hole. Either way the export says the
    // history is not intact rather than attesting what is left.
    const problems: string[] = [];
    const head = chained.length ? chained[chained.length - 1]!.chainHash : "genesis";
    if (this.chain.writesSinceLoad > 0 && head !== this.chain.currentHash) problems.push("the newest record this process wrote is missing from the directory");
    const seqMax = chained.reduce((m, e) => Math.max(m, e.seq), 0);

    let anchor: AnchorManifest;
    let anchorNote = "";
    if (!this.anchor) {
      anchor = { anchored: false, reason: "anchoring disabled" };
    } else {
      const anchorHead = headOfIndex(entries);
      if (!anchorHead) {
        anchor = { anchored: false, reason: "no records" };
      } else {
        const result: AnchorResult = await timestampHead(anchorHead, this.tsaUrls, this.anchorTimeout);
        anchorNote = result.ok ? `timestamped by ${result.tsa_url}` : `no external timestamp: ${result.error}`;
        anchor = anchorManifestFrom(result, seqMax);
      }
    }

    const { path: bundlePath, verification } = await streamEvidenceBundleV1({
      runsDir: this.runsDir,
      entries,
      unreadable,
      signingKey: resolveSigningKey(this.runsDir, this.#hmacKey),
      tenant: this.name,
      signer: this.signer,
      system: { name: this.name, high_risk_rationale: "", deployer: "" },
      anchor,
      outputDir: outputDir ?? this.runsDir,
      problems,
    });
    const found = verification.problems ?? [];
    const notIntact = found.length ? `chain not intact: ${found.join("; ")}` : "";
    if (notIntact) console.warn(`AIR Blackbox (${this.name}): ${notIntact}`);
    this.lastExportNote = [notIntact, anchorNote].filter(Boolean).join("; ");
    this.bundlePath = bundlePath;
    return bundlePath;
  }

  /** Export if anything was recorded, then close. For `await using rec = record(...)`. */
  async [Symbol.asyncDispose](): Promise<void> {
    try {
      if (this.written && !this.closed) await this.export();
    } finally {
      this.close();
    }
  }
}

/** Start recording an agent. */
export function record(name = "agent", options: RecorderOptions = {}): Recorder {
  return new Recorder(name, options);
}
