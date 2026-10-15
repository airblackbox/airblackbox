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

import { parsePreserving, pythonJsonBytes, pythonJsonPretty, type Canonical } from "./canonical.js";

const GENESIS = Buffer.from("genesis", "utf8");
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
  private readonly key: Buffer;
  private prev: Buffer = GENESIS;
  private seq = 0;
  private count = 0;
  private pending: Promise<unknown> = Promise.resolve();

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
    this.key = Buffer.from(resolveSigningKey(runsDir, signingKey), "utf8");
    if (resume) this.resume();
  }

  private resume(): void {
    const records = loadRecords(this.runsDir).filter((r) => r.chain_hash);
    for (const rec of records) {
      const h = this.digest(rec);
      this.prev = h.digest;
      this.count++;
      this.seq = Math.max(this.seq, Number(rec.chain_seq ?? 0));
    }
  }

  private digest(record: ChainRecord): { hex: string; digest: Buffer } {
    const { chain_hash: _omit, ...clean } = record;
    const h = createHmac("sha256", this.key);
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
    if (!record.version) record.version = "1.0.0";
    if (!record.timestamp) record.timestamp = new Date().toISOString();
    delete record.chain_hash;
    record.chain_seq = this.seq + 1;
    const { hex, digest } = this.digest(record);
    record.chain_hash = hex;
    // The file is the canonical form indented: every number is written as it
    // was hashed, so any reader that re-serialises canonically recovers the
    // hashed bytes.
    const file = path.join(this.runsDir, `${record.run_id}.air.json`);
    fs.writeFileSync(file, pythonJsonPretty(record) + "\n");
    this.prev = digest;
    this.count++;
    this.seq++;
    return hex;
  }

  get recordCount(): number {
    return this.count;
  }

  get currentHash(): string {
    return this.prev.equals(GENESIS) ? "genesis" : this.prev.toString("hex");
  }

  get nextSeq(): number {
    return this.seq + 1;
  }
}

/** Load the chained records of a directory in verification order. */
export function loadRecords(runsDir: string): ChainRecord[] {
  let names: string[];
  try {
    names = fs.readdirSync(runsDir).filter((n) => n.endsWith(".air.json"));
  } catch {
    return [];
  }
  const records: ChainRecord[] = [];
  for (const name of names) {
    try {
      const parsed = parsePreserving(fs.readFileSync(path.join(runsDir, name), "utf8"));
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        records.push(parsed as ChainRecord);
      }
    } catch {
      /* unreadable file is outside the chain, as in the Python loader */
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
  return records;
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

/** Verify every chained record in a runs directory. */
export function verifyChain(runsDir: string, signingKey?: string): ChainVerification {
  return verifyRecords(loadRecords(runsDir), resolveSigningKey(runsDir, signingKey));
}
