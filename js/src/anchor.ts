/**
 * External timestamp anchoring (RFC 3161).
 *
 * The chain head is a key-free SHA-256 over the ordered (chain_seq,
 * chain_hash) pairs, so anyone with the records can recompute it. A public
 * timestamp authority countersigns that head with ITS key. An operator who
 * later rewrites history, even re-signing every record, can no longer match
 * the token they obtained earlier. The Python SDK and the browser verifier
 * check the token; this module only obtains it.
 *
 * The timestamp query is built here as DER (no openssl dependency), with the
 * same content `openssl ts -query -sha256 -cert` produces: version 1, a
 * SHA-256 message imprint, a random nonce and certReq TRUE.
 */
import { createHash, randomBytes } from "node:crypto";

import { pythonJsonCompact } from "./canonical.js";
import { loadRecords } from "./chain.js";

export const DEFAULT_TSA_URLS = [
  "https://freetsa.org/tsr",
  "https://timestamp.sigstore.dev/api/v1/timestamp",
  "http://timestamp.digicert.com",
];

export interface AnchorResult {
  ok: boolean;
  head: string;
  tsr?: Buffer;
  tsa_url?: string;
  timestamp?: string;
  error?: string;
}

/** SHA-256 over the ordered (chain_seq, chain_hash) pairs; "" for none. */
export function headOverEntries(entries: Array<[number, string]>): string {
  if (entries.length === 0) return "";
  const ordered = [...entries].sort((a, b) => a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0));
  return createHash("sha256").update(pythonJsonCompact(ordered), "utf8").digest("hex");
}

/** The key-free head of a runs directory, optionally bounded by chain_seq. */
export function computeHead(runsDir: string, upToSeq?: number): string {
  const entries: Array<[number, string]> = [];
  for (const rec of loadRecords(runsDir)) {
    const ch = rec.chain_hash;
    if (!ch) continue;
    const seq = Number(rec.chain_seq ?? 0);
    if (upToSeq !== undefined && seq > upToSeq) continue;
    entries.push([seq, String(ch)]);
  }
  return headOverEntries(entries);
}

// --- minimal DER ----------------------------------------------------------

function derLen(n: number): Buffer {
  if (n < 0x80) return Buffer.from([n]);
  const bytes: number[] = [];
  for (let v = n; v > 0; v >>= 8) bytes.unshift(v & 0xff);
  return Buffer.from([0x80 | bytes.length, ...bytes]);
}

function der(tag: number, content: Buffer): Buffer {
  return Buffer.concat([Buffer.from([tag]), derLen(content.length), content]);
}

const SHA256_ALG_ID = Buffer.from("300d06096086480165030402010500", "hex");

/** An RFC 3161 TimeStampReq over a 32-byte SHA-256 head, as DER. */
export function makeQuery(headHex: string): Buffer {
  const digest = Buffer.from(headHex, "hex");
  if (digest.length !== 32) throw new RangeError("head must be a 32-byte hex digest");
  let nonce = randomBytes(8);
  if (nonce[0]! & 0x80) nonce = Buffer.concat([Buffer.from([0]), nonce]);
  return der(0x30, Buffer.concat([
    der(0x02, Buffer.from([1])), // version v1
    der(0x30, Buffer.concat([SHA256_ALG_ID, der(0x04, digest)])), // MessageImprint
    der(0x02, nonce),
    der(0x01, Buffer.from([0xff])), // certReq TRUE
  ]));
}

/**
 * Obtain a timestamp token over the head from the first reachable authority.
 * The timeout is per URL. Failure is returned, never thrown: the caller
 * records the gap.
 */
export async function timestampHead(
  headHex: string,
  tsaUrls: string[] = DEFAULT_TSA_URLS,
  timeoutMs = 20000,
): Promise<AnchorResult> {
  if (!headHex) return { ok: false, head: headHex, error: "no chain head to anchor" };
  let tsq: Buffer;
  try {
    tsq = makeQuery(headHex);
  } catch (e) {
    return { ok: false, head: headHex, error: String(e) };
  }
  let lastErr = "no TSA reachable";
  for (const url of tsaUrls) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        body: new Uint8Array(tsq),
        headers: { "Content-Type": "application/timestamp-query" },
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (resp.status !== 200) {
        lastErr = `${url}: HTTP ${resp.status}`;
        continue;
      }
      const tsr = Buffer.from(await resp.arrayBuffer());
      if (tsr.length === 0) {
        lastErr = `${url}: empty response`;
        continue;
      }
      return { ok: true, head: headHex, tsr, tsa_url: url, timestamp: extractGenTime(tsr) };
    } catch (e) {
      lastErr = `${url}: ${e instanceof Error ? e.message : String(e)}`;
    }
  }
  return { ok: false, head: headHex, error: lastErr };
}

/**
 * Best-effort genTime from a TimeStampResp: the first GeneralizedTime inside
 * the TSTInfo. Informational only; verification does not depend on it.
 */
export function extractGenTime(tsr: Buffer): string | undefined {
  // id-ct-TSTInfo, OID 1.2.840.113549.1.9.16.1.4, as DER (tag, length, value).
  const oid = Buffer.from("060b2a864886f70d0109100104", "hex");
  const at = tsr.indexOf(oid);
  if (at < 0) return undefined;
  // The TSTInfo follows as [0] { OCTET STRING { SEQUENCE { version, policy,
  // messageImprint, serialNumber, genTime ... } } }; the first GeneralizedTime
  // (tag 0x18) after the OID is genTime.
  for (let i = at + oid.length; i < tsr.length - 2; i++) {
    if (tsr[i] !== 0x18) continue;
    const len = tsr[i + 1]!;
    if (len < 0x80 && i + 2 + len <= tsr.length) {
      const s = tsr.subarray(i + 2, i + 2 + len).toString("latin1");
      const m = /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?:\.(\d+))?Z$/.exec(s);
      if (m) {
        const frac = m[7] ? "." + m[7] : "";
        return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}${frac}Z`;
      }
    }
  }
  return undefined;
}
