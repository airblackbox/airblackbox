/**
 * Bilateral action receipts, signed with Ed25519 and verifiable by anyone
 * from the receipt JSON alone.
 *
 * Phase 1 (authorization) signs the canonical authorization payload; phase 2
 * (seal) signs a payload that includes the authorization signature, so a seal
 * cannot exist without the authorization it covers. Payload bytes are the
 * Python SDK's byte-for-byte, so its `verify_receipt` and the browser
 * verifier accept receipts signed here, and vice versa.
 *
 * Keys are generated in this process and never leave it. Ed25519 only: it is
 * what WebCrypto verifies in a browser, and there is no ML-DSA-65 provider
 * for Node without a native build. A receipt signed by the Python SDK's
 * ML-DSA-65 signer is reported as unverifiable here, never as invalid.
 */
import {
  createHash,
  createHmac,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  randomUUID,
  sign as cryptoSign,
  timingSafeEqual,
  verify as cryptoVerify,
  type KeyObject,
} from "node:crypto";

import { RawNumber, pythonJson, pythonJsonBytes } from "./canonical.js";

export type ReceiptStatus = "authorized" | "denied" | "pending" | "sealed" | "failed";
export type SigningMethod = "ed25519" | "hmac-sha256";

export interface ReceiptInit {
  receipt_id?: string;
  agent_id?: string;
  action_name?: string;
  action_category?: string;
  payload_hash?: string;
  covenant_hash?: string;
  decision?: string;
  authorized?: boolean;
  parent_receipt_id?: string | null;
  status?: ReceiptStatus;
  created_at?: string;
  metadata?: Record<string, unknown>;
}

/** The JSON form of a receipt, field for field what the Python SDK writes. */
export interface ReceiptDict {
  receipt_id: string;
  agent_id: string;
  action_name: string;
  action_category: string;
  payload_hash: string;
  covenant_hash: string;
  decision: string;
  authorized: boolean;
  parent_receipt_id: string | null;
  authorization_sig: string;
  result_hash: string;
  result_status: string;
  seal_sig: string;
  chain_hash: string;
  status: string;
  created_at: string;
  sealed_at: string;
  signing_method: string;
  signing_public_key: string;
  metadata: Record<string, unknown>;
}

/** Python's datetime.utcnow().isoformat() + "Z" (microseconds, no offset). */
export function pythonUtcNow(): string {
  const d = new Date();
  const iso = d.toISOString(); // 2026-10-15T20:33:00.123Z
  return iso.slice(0, -1) + "000Z";
}

export class ActionReceipt {
  receipt_id: string;
  agent_id: string;
  action_name: string;
  action_category: string;
  payload_hash: string;
  covenant_hash: string;
  decision: string;
  authorized: boolean;
  parent_receipt_id: string | null;
  authorization_sig = "";
  result_hash = "";
  result_status = "";
  seal_sig = "";
  chain_hash = "";
  status: ReceiptStatus;
  created_at: string;
  sealed_at = "";
  signing_method = "";
  signing_public_key = "";
  metadata: Record<string, unknown>;

  constructor(init: ReceiptInit = {}) {
    this.receipt_id = init.receipt_id ?? randomUUID();
    this.agent_id = init.agent_id ?? "";
    this.action_name = init.action_name ?? "";
    this.action_category = init.action_category ?? "";
    this.payload_hash = init.payload_hash ?? "";
    this.covenant_hash = init.covenant_hash ?? "";
    this.decision = init.decision ?? "";
    this.authorized = init.authorized ?? false;
    this.parent_receipt_id = init.parent_receipt_id ?? null;
    this.status = init.status ?? "authorized";
    this.created_at = init.created_at ?? pythonUtcNow();
    this.metadata = init.metadata ?? {};
  }

  /** Canonical bytes the authorization signature covers. */
  get authorizationPayload(): Buffer {
    return authorizationPayloadFromDict(this);
  }

  /** Canonical bytes the seal signature covers. */
  get sealPayload(): Buffer {
    return pythonJsonBytes({
      receipt_id: this.receipt_id,
      authorization_sig: this.authorization_sig,
      result_hash: this.result_hash,
      result_status: this.result_status,
      sealed_at: this.sealed_at,
    });
  }

  toDict(): ReceiptDict {
    return {
      receipt_id: this.receipt_id,
      agent_id: this.agent_id,
      action_name: this.action_name,
      action_category: this.action_category,
      payload_hash: this.payload_hash,
      covenant_hash: this.covenant_hash,
      decision: this.decision,
      authorized: this.authorized,
      parent_receipt_id: this.parent_receipt_id,
      authorization_sig: this.authorization_sig,
      result_hash: this.result_hash,
      result_status: this.result_status,
      seal_sig: this.seal_sig,
      chain_hash: this.chain_hash,
      status: this.status,
      created_at: this.created_at,
      sealed_at: this.sealed_at,
      signing_method: this.signing_method,
      signing_public_key: this.signing_public_key,
      metadata: this.metadata,
    };
  }

  static fromDict(d: Partial<ReceiptDict>): ActionReceipt {
    const r = new ActionReceipt({
      receipt_id: d.receipt_id,
      agent_id: d.agent_id,
      action_name: d.action_name,
      action_category: d.action_category,
      payload_hash: d.payload_hash,
      covenant_hash: d.covenant_hash,
      decision: d.decision,
      authorized: d.authorized,
      parent_receipt_id: d.parent_receipt_id ?? null,
      status: (d.status as ReceiptStatus | undefined) ?? "authorized",
      created_at: d.created_at,
      metadata: d.metadata,
    });
    r.authorization_sig = d.authorization_sig ?? "";
    r.result_hash = d.result_hash ?? "";
    r.result_status = d.result_status ?? "";
    r.seal_sig = d.seal_sig ?? "";
    r.chain_hash = d.chain_hash ?? "";
    r.sealed_at = d.sealed_at ?? "";
    r.signing_method = d.signing_method ?? "";
    r.signing_public_key = d.signing_public_key ?? "";
    return r;
  }
}

/** Rebuild the authorization payload from a receipt dict, byte for byte. */
export function authorizationPayloadFromDict(d: Partial<ReceiptDict>): Buffer {
  return pythonJsonBytes({
    receipt_id: d.receipt_id ?? "",
    agent_id: d.agent_id ?? "",
    action_name: d.action_name ?? "",
    action_category: d.action_category ?? "",
    payload_hash: d.payload_hash ?? "",
    covenant_hash: d.covenant_hash ?? "",
    decision: d.decision ?? "",
    authorized: d.authorized ?? false,
    parent_receipt_id: d.parent_receipt_id ?? null,
    created_at: d.created_at ?? "",
  });
}

/**
 * SHA-256 of a payload's canonical JSON. Never stores the payload. Matches
 * the Python `hash_payload` (json.dumps(..., sort_keys=True, default=str))
 * for JSON-representable values; a Date is hashed as its ISO string, and
 * anything else as `hashable` describes. It does not throw on a payload's
 * contents: hashing a tool's output must never be what breaks the tool call.
 */
export function hashPayload(payload: unknown): string {
  let text: string;
  try {
    text = pythonJson(hashable(payload));
  } catch {
    text = pythonJson("[unhashable]"); // e.g. a Proxy whose traps throw
  }
  return createHash("sha256").update(text, "utf8").digest("hex");
}

const MAX_HASH_DEPTH = 500;

/**
 * A payload as canonical JSON can represent it. Plain JSON values are
 * unchanged, so hashes match the Python SDK's. Values JSON has no form for
 * get a stable one rather than an exception: non-finite numbers as Python
 * writes them (NaN, Infinity), a Map as an object, a Set as an array, bytes
 * as base64, an Error or URL as its text, a function or symbol by name, an
 * object with toJSON by its result, a property whose getter throws as
 * "[unreadable]", a reference back to an ancestor as "[circular]", and
 * nesting beyond 500 levels as "[too deep]".
 */
export function hashable(value: unknown, depth = 0, ancestors: Set<object> = new Set()): unknown {
  switch (typeof value) {
    case "number":
      return Number.isFinite(value) ? value : new RawNumber(Number.isNaN(value) ? "NaN" : value > 0 ? "Infinity" : "-Infinity");
    case "function":
      return `[function ${(value as { name?: string }).name || "anonymous"}]`;
    case "symbol":
      return value.toString();
    case "object":
      break;
    default:
      return value; // string, boolean, bigint, undefined
  }
  if (value === null || value instanceof RawNumber || value instanceof Date) return value;
  if (depth >= MAX_HASH_DEPTH) return "[too deep]";
  const obj = value as object;
  if (ancestors.has(obj)) return "[circular]";
  ancestors.add(obj);
  try {
    if (Array.isArray(obj)) return obj.map((v) => hashable(v, depth + 1, ancestors));
    if (ArrayBuffer.isView(obj)) return Buffer.from(obj.buffer, obj.byteOffset, obj.byteLength).toString("base64");
    if (obj instanceof ArrayBuffer) return Buffer.from(obj).toString("base64");
    if (obj instanceof Map) {
      const out: Record<string, unknown> = {};
      for (const [k, v] of obj) define(out, String(k), hashable(v, depth + 1, ancestors));
      return out;
    }
    if (obj instanceof Set) return [...obj].map((v) => hashable(v, depth + 1, ancestors));
    if (obj instanceof Error) return `${obj.name}: ${obj.message}`;
    if (obj instanceof URL) return obj.href;
    const toJSON = (obj as { toJSON?: unknown }).toJSON;
    if (typeof toJSON === "function") {
      try {
        return hashable(toJSON.call(obj), depth + 1, ancestors);
      } catch {
        return "[unreadable]";
      }
    }
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(obj)) {
      let v: unknown;
      try {
        v = (obj as Record<string, unknown>)[k];
      } catch {
        v = "[unreadable]";
      }
      define(out, k, hashable(v, depth + 1, ancestors));
    }
    return out;
  } finally {
    ancestors.delete(obj);
  }
}

function define(obj: Record<string, unknown>, key: string, value: unknown): void {
  Object.defineProperty(obj, key, { value, enumerable: true, writable: true, configurable: true });
}

export const hashResult = hashPayload;

// --- Ed25519 key handling -----------------------------------------------

const PKCS8_PREFIX = Buffer.from("302e020100300506032b657004220420", "hex");
const SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

function privateKeyFromSeed(seed: Buffer): KeyObject {
  if (seed.length !== 32) throw new RangeError("Ed25519 seed must be 32 bytes");
  return createPrivateKey({ key: Buffer.concat([PKCS8_PREFIX, seed]), format: "der", type: "pkcs8" });
}

function publicKeyFromRaw(raw: Buffer): KeyObject {
  if (raw.length !== 32) throw new RangeError("Ed25519 public key must be 32 bytes");
  return createPublicKey({ key: Buffer.concat([SPKI_PREFIX, raw]), format: "der", type: "spki" });
}

function rawPublicKey(pub: KeyObject): Buffer {
  const der = pub.export({ format: "der", type: "spki" }) as Buffer;
  return der.subarray(der.length - 32);
}

function rawSeed(priv: KeyObject): Buffer {
  const der = priv.export({ format: "der", type: "pkcs8" }) as Buffer;
  return der.subarray(der.length - 32);
}

/** SubjectPublicKeyInfo PEM for a raw Ed25519 public key. */
export function publicKeyPem(publicKeyHex: string): string {
  const pub = publicKeyFromRaw(Buffer.from(publicKeyHex, "hex"));
  return pub.export({ format: "pem", type: "spki" }) as string;
}

export class ReceiptSigner {
  readonly method: SigningMethod;
  private readonly priv?: KeyObject;
  private readonly pub?: KeyObject;
  private readonly hmacKey: Buffer;

  /**
   * @param options.privateKey 32-byte Ed25519 seed to resume a persisted
   *   identity. Omit to generate a fresh key.
   * @param options.hmacKey shared secret for the HMAC method. As in the
   *   Python SDK it does NOT select HMAC by itself: Ed25519 is always
   *   available in Node, so receipts stay third-party verifiable.
   * @param options.method "hmac-sha256" forces the shared-secret method
   *   (not third-party verifiable). Only for interop with HMAC deployments.
   */
  constructor(options: { privateKey?: Buffer | Uint8Array; hmacKey?: string; method?: SigningMethod } = {}) {
    this.hmacKey = Buffer.from(options.hmacKey ?? "air-blackbox-default", "utf8");
    if (options.method === "hmac-sha256") {
      if (options.privateKey) throw new TypeError("method hmac-sha256 takes an hmacKey, not a privateKey");
      this.method = "hmac-sha256";
      return;
    }
    if (options.privateKey) {
      this.priv = privateKeyFromSeed(Buffer.from(options.privateKey));
    } else {
      this.priv = generateKeyPairSync("ed25519").privateKey;
    }
    this.pub = createPublicKey(this.priv);
    this.method = "ed25519";
  }

  /** The 32-byte seed, for persisting the identity (same as Python's). */
  get seed(): Buffer | undefined {
    return this.priv ? rawSeed(this.priv) : undefined;
  }

  get publicKeyHex(): string | undefined {
    return this.pub ? rawPublicKey(this.pub).toString("hex") : undefined;
  }

  sign(data: Buffer): string {
    if (this.priv) return cryptoSign(null, data, this.priv).toString("hex");
    return createHmac("sha256", this.hmacKey).update(data).digest("hex");
  }

  verify(data: Buffer, signatureHex: string): boolean {
    try {
      const sig = Buffer.from(signatureHex, "hex");
      if (this.pub) return cryptoVerify(null, data, this.pub, sig);
      const expected = createHmac("sha256", this.hmacKey).update(data).digest();
      return expected.length === sig.length && timingSafeEqual(expected, sig);
    } catch {
      return false;
    }
  }

  signAuthorization(receipt: ActionReceipt): string {
    receipt.signing_method = this.method;
    receipt.signing_public_key = this.publicKeyHex ?? "";
    receipt.authorization_sig = this.sign(receipt.authorizationPayload);
    return receipt.authorization_sig;
  }

  signSeal(receipt: ActionReceipt): string {
    receipt.seal_sig = this.sign(receipt.sealPayload);
    return receipt.seal_sig;
  }

  verifyAuthorization(receipt: ActionReceipt): boolean {
    return this.verify(receipt.authorizationPayload, receipt.authorization_sig);
  }

  verifySeal(receipt: ActionReceipt): boolean {
    return this.verify(receipt.sealPayload, receipt.seal_sig);
  }
}

/**
 * Verify a receipt's authorization signature from its JSON alone. With no
 * expectedPublicKey this proves internal consistency (the signature matches
 * the embedded key); pass the hex key you trust to also prove authenticity.
 */
export function verifyReceipt(
  receipt: Partial<ReceiptDict>,
  expectedPublicKey?: string,
): { verified: boolean; detail: string } {
  const method = receipt.signing_method ?? "";
  const pubHex = (receipt.signing_public_key ?? "").trim().toLowerCase();
  const sigHex = receipt.authorization_sig ?? "";
  if (!sigHex) return { verified: false, detail: "no authorization signature present" };
  if (expectedPublicKey && (method === "ed25519" || method === "ML-DSA-65")) {
    if (!pubHex || pubHex !== expectedPublicKey.trim().toLowerCase()) {
      return { verified: false, detail: "receipt is signed by a key that does not match the expected/trusted public key (authenticity check failed)" };
    }
  }
  const payload = authorizationPayloadFromDict(receipt);
  if (method === "ed25519") {
    if (!pubHex) return { verified: false, detail: "ed25519 receipt missing public key" };
    try {
      const ok = cryptoVerify(null, payload, publicKeyFromRaw(Buffer.from(pubHex, "hex")), Buffer.from(sigHex, "hex"));
      return ok
        ? { verified: true, detail: "verified (ed25519, third-party verifiable)" }
        : { verified: false, detail: "ed25519 signature INVALID (tampered or wrong key)" };
    } catch {
      return { verified: false, detail: "ed25519 signature INVALID (tampered or wrong key)" };
    }
  }
  if (method === "ML-DSA-65") {
    return { verified: false, detail: "ML-DSA-65 receipt: no post-quantum verifier in this package; verify with the Python SDK (pip install 'air-blackbox[pqc]')" };
  }
  if (method === "hmac-sha256") {
    return { verified: false, detail: "hmac-sha256 is not third-party verifiable; it needs the shared secret" };
  }
  return { verified: false, detail: `unknown or missing signing_method: ${JSON.stringify(method)}` };
}
