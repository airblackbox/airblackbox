/**
 * HMAC-SHA256 audit chain: the AIR Blackbox Audit Chain Specification v1.0,
 * writing `<run_id>.air.json` records that the Python SDK, the Go gateway and
 * the browser verifier all read.
 *
 *     chain_hash = HMAC-SHA256(key, prev_digest || canonical(record without chain_hash))
 *
 * `prev_digest` starts as the bytes "genesis" and advances to each record's
 * raw 32-byte digest. `chain_seq` is the writer's append counter and is part
 * of the hashed record, so verifiers replay the exact order.
 */
import { createHmac, randomUUID } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";

import { parsePreserving, pythonJson, pythonJsonBytes, pythonJsonPretty, type Canonical } from "./canonical.js";

const GENESIS = Buffer.from("genesis", "utf8");
// A run_id names its record's file, so it must not reach outside runsDir.
const SAFE_RUN_ID = /^(?!\.\.?$)[A-Za-z0-9._-]{1,200}$/;
export const DEFAULT_SIGNING_KEY = "air-blackbox-default";

export interface ChainRecord {
  run_id?: string;
  timestamp?: string;
  version?: string;
  chain_seq?: number;
  chain_hash?: string;
  [key: string]: unknown;
}

export interface ChainVerification {
  intact: boolean;
  total_records: number;
  verified_records: number;
  records_with_hash: number;
  first_break_at?: number;
  first_break_run_id?: string;
  /** Why an export judged the history incomplete (missing or unreadable records). */
  problems?: string[];
}

/** The HMAC key the Python SDK and gateway would use for this directory. */
export function resolveSigningKey(runsDir: string, explicit?: string): string {
  if (explicit) return explicit;
  const env = process.env["TRUST_SIGNING_KEY"];
  if (env) return env;
  try {
    const k = fs.readFileSync(path.join(runsDir, ".air-signing-key"), "utf8").trim();
    if (k) return k;
  } catch {
    /* no colocated key */
  }
  return DEFAULT_SIGNING_KEY;
}

export class AuditChain {
  readonly runsDir: string;
  // A true private field, so console.log(chain) cannot print the HMAC key.
  readonly #key: Buffer;
  private prev: Buffer = GENESIS;
  private seq = 0;
  private count = 0;
  private writes = 0;
  private knownFiles = 0;

  /**
   * @param runsDir where records are written; created if missing.
   * @param signingKey HMAC key; defaults to $TRUST_SIGNING_KEY, then the
   *   `.air-signing-key` file beside the records, then the development default.
   * @param resume continue the chain already in runsDir instead of starting a
   *   second genesis-rooted one that could never verify together with it.
   */
  constructor(runsDir = "./runs", signingKey?: string, resume = false) {
    this.runsDir = runsDir;
    fs.mkdirSync(runsDir, { recursive: true });
    this.#key = Buffer.from(resolveSigningKey(runsDir, signingKey), "utf8");
    if (resume) this.resume();
  }

  /**
   * Continue from the newest record's stored chain_hash, found by indexing
   * the directory (one read per file, no full parse for pretty-printed
   * records, no re-hashing). For an intact chain that is exactly the digest
   * re-hashing would reach; a broken chain fails verification at its break
   * either way.
   */
  private resume(): void {
    this.writes = 0;
    const { entries, unreadable } = indexRecords(this.runsDir);
    this.knownFiles = entries.length + unreadable.length;
    const chained = entries.filter((e) => e.chainHash);
    const head = chained[chained.length - 1];
    this.prev = head ? Buffer.from(head.chainHash, "hex") : GENESIS;
    this.count = chained.length;
    this.seq = chained.reduce((m, e) => Math.max(m, e.seq), 0);
  }

  /**
   * Pick up records another writer appended since this chain last looked
   * (the Python SDK taking its turn, say). One directory listing when
   * nothing changed.
   */
  syncWithDisk(): void {
    let files: number;
    try {
      files = fs.readdirSync(this.runsDir).filter((n) => n.endsWith(".air.json")).length;
    } catch {
      return;
    }
    if (files !== this.knownFiles) this.resume();
  }

  private digest(record: ChainRecord): { hex: string; digest: Buffer } {
    const { chain_hash: _omit, ...clean } = record;
    const h = createHmac("sha256", this.#key);
    h.update(this.prev);
    h.update(pythonJsonBytes(clean));
    const digest = h.digest();
    return { hex: digest.toString("hex"), digest };
  }

  /**
   * Stamp chain fields onto the record, write `<run_id>.air.json` and
   * advance the chain. Writes are serialised: a chain has one writer and one
   * order. Returns the chain_hash. The record object is mutated in place.
   */
  write(record: ChainRecord): string {
    if (!record.run_id) record.run_id = randomUUID();
    if (!SAFE_RUN_ID.test(String(record.run_id))) {
      throw new Error(`run_id ${JSON.stringify(record.run_id)} is not a safe file name; it names the record's file`);
    }
    if (!record.version) record.version = "1.0.0";
    if (!record.timestamp) record.timestamp = new Date().toISOString();
    delete record.chain_hash;
    record.chain_seq = this.seq + 1;
    // Serialise once and hash and write that snapshot: a value that reads
    // differently each time (a getter, a Proxy) can then never make the file
    // disagree with its hash.
    const snapshot = parsePreserving(pythonJson(record)) as ChainRecord;
    const { hex, digest } = this.digest(snapshot);
    snapshot.chain_hash = hex;
    record.chain_hash = hex;
    // The file is the canonical form indented: every number is written as it
    // was hashed, so any reader that re-serialises canonically recovers the
    // hashed bytes. Written to a temporary name and renamed, so a crash never
    // leaves a torn record behind.
    const file = path.join(this.runsDir, `${record.run_id}.air.json`);
    const tmp = `${file}.${process.pid}.tmp`;
    const existed = fs.existsSync(file);
    fs.writeFileSync(tmp, pythonJsonPretty(snapshot) + "\n");
    fs.renameSync(tmp, file);
    this.prev = digest;
    this.count++;
    this.seq++;
    this.writes++;
    if (!existed) this.knownFiles++;
    return hex;
  }

  get recordCount(): number {
    return this.count;
  }

  /** Records written through this chain since it last read the directory. */
  get writesSinceLoad(): number {
    return this.writes;
  }

  get currentHash(): string {
    return this.prev.equals(GENESIS) ? "genesis" : this.prev.toString("hex");
  }

  get nextSeq(): number {
    return this.seq + 1;
  }
}

/** Where a record file sits in verification order, without the record. */
export interface RecordIndexEntry {
  file: string;
  seq: number;
  timestamp: string;
  runId: string;
  /** "" for a record outside the chain. */
  chainHash: string;
}

// A top-level field of a pretty-printed record: every writer (this package,
// the Python SDK, the Go gateway) puts top-level keys on their own line at
// two spaces, and a newline inside a JSON string is always escaped, so this
// cannot match a nested key or text inside a value.
const topLevel = (key: string): RegExp => new RegExp(`\\n  "${key}": ("(?:[^"\\\\]|\\\\.)*"|-?\\d+)(?=,?\\n)`, "g");
const TOP_CHAIN_HASH = topLevel("chain_hash");
const TOP_CHAIN_SEQ = topLevel("chain_seq");
const TOP_RUN_ID = topLevel("run_id");
const TOP_TIMESTAMP = topLevel("timestamp");

const UNREAD = Symbol("unread");

/**
 * The value of a top-level key, undefined when it is absent, or UNREAD when
 * the fast path cannot be sure of it (a value it does not match, or the key
 * twice, where a JSON parser would keep the last).
 */
function topValue(re: RegExp, text: string, key: string): unknown {
  re.lastIndex = 0;
  const m = re.exec(text);
  if (!m) return text.includes(`\n  "${key}": `) ? UNREAD : undefined;
  if (re.exec(text)) return UNREAD;
  return JSON.parse(m[1]!);
}

/** Index one record file; undefined if it cannot be read as a record. */
export function indexRecordFile(runsDir: string, file: string): RecordIndexEntry | undefined {
  let text: string;
  try {
    text = fs.readFileSync(path.join(runsDir, file), "utf8");
  } catch {
    return undefined;
  }
  // The fast path reads a complete pretty-printed record. It orders entries
  // exactly as loadRecords would, or gives way to a full parse.
  const hash = topValue(TOP_CHAIN_HASH, text, "chain_hash");
  if (typeof hash === "string" && hash && text.trimEnd().endsWith("}")) {
    const seq = topValue(TOP_CHAIN_SEQ, text, "chain_seq");
    const timestamp = topValue(TOP_TIMESTAMP, text, "timestamp");
    const runId = topValue(TOP_RUN_ID, text, "run_id");
    if (seq !== UNREAD && timestamp !== UNREAD && runId !== UNREAD) {
      return {
        file,
        seq: Number(seq ?? 0),
        timestamp: String(timestamp ?? ""),
        runId: String(runId ?? ""),
        chainHash: hash,
      };
    }
  }
  // Not pretty-printed, outside the chain, or unusual: read it properly.
  let rec: Canonical;
  try {
    rec = parsePreserving(text);
  } catch {
    return undefined;
  }
  if (!rec || typeof rec !== "object" || Array.isArray(rec)) return undefined;
  const r = rec as ChainRecord;
  return {
    file,
    seq: Number(r.chain_seq ?? 0),
    timestamp: String(r.timestamp ?? ""),
    runId: String(r.run_id ?? ""),
    chainHash: r.chain_hash ? String(r.chain_hash) : "",
  };
}

/** Verification order: chain_seq, then timestamp, as loadRecords sorts. */
export function compareIndexEntries(a: RecordIndexEntry, b: RecordIndexEntry): number {
  if (a.seq !== b.seq) return a.seq - b.seq;
  return a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0;
}

export function recordFileNames(runsDir: string): string[] {
  try {
    return fs.readdirSync(runsDir).filter((n) => n.endsWith(".air.json"));
  } catch {
    return [];
  }
}

/** Index a runs directory in verification order, holding no records in memory. */
export function indexRecords(runsDir: string): { entries: RecordIndexEntry[]; unreadable: string[] } {
  const entries: RecordIndexEntry[] = [];
  const unreadable: string[] = [];
  for (const file of recordFileNames(runsDir)) {
    const e = indexRecordFile(runsDir, file);
    if (e) entries.push(e);
    else unreadable.push(file);
  }
  entries.sort(compareIndexEntries);
  return { entries, unreadable };
}

/** indexRecords, giving the event loop a turn as it goes (pacer). */
export async function indexRecordsPaced(runsDir: string, pacer = new Pacer()): Promise<{ entries: RecordIndexEntry[]; unreadable: string[] }> {
  const entries: RecordIndexEntry[] = [];
  const unreadable: string[] = [];
  for (const file of recordFileNames(runsDir)) {
    if (pacer.due()) await pacer.pause();
    const e = indexRecordFile(runsDir, file);
    if (e) entries.push(e);
    else unreadable.push(file);
  }
  entries.sort(compareIndexEntries);
  return { entries, unreadable };
}

/**
 * Long synchronous work, cut into slices so the process it runs in stays
 * responsive: due() says when about `budgetMs` of work (or `every` steps)
 * has gone by since the last pause.
 */
export class Pacer {
  private last = performance.now();
  private steps = 0;

  constructor(private readonly every = Infinity, private readonly budgetMs = 20) {}

  due(): boolean {
    if (++this.steps >= this.every || performance.now() - this.last >= this.budgetMs) {
      this.steps = 0;
      return true;
    }
    return false;
  }

  async pause(): Promise<void> {
    await new Promise<void>((resolve) => setImmediate(resolve));
    this.last = performance.now();
  }
}

/**
 * Verify a runs directory one record at a time, as verifyRecords would over
 * loadRecords, in memory proportional to the number of records' index
 * entries rather than their contents.
 */
export function verifyDirectory(runsDir: string, signingKey: string): ChainVerification & { unreadable: string[] } {
  const { entries, unreadable } = indexRecords(runsDir);
  const key = Buffer.from(signingKey, "utf8");
  let prev: Buffer = GENESIS;
  let verified = 0;
  let withHash = 0;
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i]!;
    if (!e.chainHash) continue;
    let rec: ChainRecord;
    try {
      rec = parsePreserving(fs.readFileSync(path.join(runsDir, e.file), "utf8")) as ChainRecord;
    } catch {
      unreadable.push(e.file);
      continue;
    }
    const step = chainStep(key, prev, rec);
    withHash++;
    if (!step.ok) {
      return { intact: false, total_records: entries.length, verified_records: verified, records_with_hash: withHash,
        first_break_at: i, first_break_run_id: String(rec.run_id ?? ""), unreadable };
    }
    verified++;
    prev = step.digest;
  }
  return { intact: true, total_records: entries.length, verified_records: verified, records_with_hash: withHash, unreadable };
}

/** One link of the chain: does this record's stored hash follow from prev? */
export function chainStep(key: Buffer, prev: Buffer, record: ChainRecord): { ok: boolean; digest: Buffer } {
  const { chain_hash: stored, ...clean } = record;
  const h = createHmac("sha256", key);
  h.update(prev);
  h.update(pythonJsonBytes(clean as Canonical));
  const digest = h.digest();
  return { ok: digest.toString("hex") === stored, digest };
}

export const GENESIS_DIGEST = GENESIS;

/** Load the chained records of a directory in verification order. */
export function loadRecords(runsDir: string): ChainRecord[] {
  return loadRecordsReport(runsDir).records;
}

/**
 * loadRecords, also naming the record files that could not be read. Those
 * are outside the chain, as in the Python loader, but an export should say
 * so rather than attest a history with a hole in it.
 */
export function loadRecordsReport(runsDir: string): { records: ChainRecord[]; unreadable: string[] } {
  let names: string[];
  try {
    names = fs.readdirSync(runsDir).filter((n) => n.endsWith(".air.json"));
  } catch {
    return { records: [], unreadable: [] };
  }
  const records: ChainRecord[] = [];
  const unreadable: string[] = [];
  for (const name of names) {
    try {
      const parsed = parsePreserving(fs.readFileSync(path.join(runsDir, name), "utf8"));
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        records.push(parsed as ChainRecord);
      } else {
        unreadable.push(name);
      }
    } catch {
      unreadable.push(name);
    }
  }
  records.sort((a, b) => {
    const sa = Number(a.chain_seq ?? 0);
    const sb = Number(b.chain_seq ?? 0);
    if (sa !== sb) return sa - sb;
    const ta = String(a.timestamp ?? "");
    const tb = String(b.timestamp ?? "");
    return ta < tb ? -1 : ta > tb ? 1 : 0;
  });
  return { records, unreadable };
}

/**
 * Verify an ordered list of records (as from loadRecords, or any records
 * whose numbers were parsed with parsePreserving). Records without a
 * chain_hash are outside the chain and never advance the digest, exactly as
 * the Python `verify_records` does.
 */
export function verifyRecords(records: ChainRecord[], signingKey: string): ChainVerification {
  const key = Buffer.from(signingKey, "utf8");
  let prev = GENESIS;
  let verified = 0;
  let withHash = 0;
  for (let i = 0; i < records.length; i++) {
    const raw = records[i]!;
    const stored = raw.chain_hash;
    if (!stored) continue;
    const { chain_hash: _omit, ...clean } = raw;
    const h = createHmac("sha256", key);
    h.update(prev);
    h.update(pythonJsonBytes(clean as Canonical));
    const digest = h.digest();
    withHash++;
    if (digest.toString("hex") !== stored) {
      return {
        intact: false,
        total_records: records.length,
        verified_records: verified,
        records_with_hash: withHash,
        first_break_at: i,
        first_break_run_id: String(raw.run_id ?? ""),
      };
    }
    verified++;
    prev = digest;
  }
  return { intact: true, total_records: records.length, verified_records: verified, records_with_hash: withHash };
}

/** Verify every chained record in a runs directory, one record at a time. */
export function verifyChain(runsDir: string, signingKey?: string): ChainVerification {
  const { unreadable: _unreadable, ...result } = verifyDirectory(runsDir, resolveSigningKey(runsDir, signingKey));
  return result;
}
