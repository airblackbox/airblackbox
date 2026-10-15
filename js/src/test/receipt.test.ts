import assert from "node:assert/strict";
import { test } from "node:test";

import { ActionReceipt, ReceiptSigner, hashPayload, publicKeyPem, verifyReceipt } from "../receipt.js";
import { hasAirSdk, python } from "./helpers.js";

test("sign, verify, and reject tampering", () => {
  const signer = new ReceiptSigner();
  assert.equal(signer.method, "ed25519");
  assert.equal(signer.publicKeyHex!.length, 64);
  const r = new ActionReceipt({ agent_id: "a", action_name: "send_email", payload_hash: hashPayload({ to: "x" }), decision: "permit", authorized: true });
  signer.signAuthorization(r);
  assert.equal(r.signing_method, "ed25519");
  assert.equal(signer.verifyAuthorization(r), true);
  assert.equal(verifyReceipt(r.toDict()).verified, true);
  assert.equal(verifyReceipt(r.toDict(), signer.publicKeyHex).verified, true);
  assert.equal(verifyReceipt(r.toDict(), "00".repeat(32)).verified, false);

  const tampered = { ...r.toDict(), authorized: false };
  assert.equal(verifyReceipt(tampered).verified, false);

  r.result_hash = hashPayload({ ok: true });
  r.result_status = "success";
  r.sealed_at = "2026-10-15T00:00:00.000000Z";
  signer.signSeal(r);
  assert.equal(signer.verifySeal(r), true);
  r.result_status = "failure";
  assert.equal(signer.verifySeal(r), false);
});

test("a persisted seed resumes the same identity", () => {
  const a = new ReceiptSigner();
  const b = new ReceiptSigner({ privateKey: a.seed! });
  assert.equal(a.publicKeyHex, b.publicKeyHex);
  const r = new ActionReceipt({ agent_id: "a", action_name: "x" });
  a.signAuthorization(r);
  assert.equal(b.verifyAuthorization(r), true);
});

test("an hmacKey alone does not downgrade receipts from Ed25519", () => {
  assert.equal(new ReceiptSigner({ hmacKey: "shared" }).method, "ed25519");
});

test("forced hmac signs but is not third-party verifiable", () => {
  const s = new ReceiptSigner({ hmacKey: "shared", method: "hmac-sha256" });
  assert.equal(s.method, "hmac-sha256");
  const r = new ActionReceipt({ agent_id: "a", action_name: "x" });
  s.signAuthorization(r);
  assert.equal(s.verifyAuthorization(r), true);
  assert.equal(verifyReceipt(r.toDict()).verified, false);
});

test("PEM export is a SubjectPublicKeyInfo block", () => {
  const pem = publicKeyPem(new ReceiptSigner().publicKeyHex!);
  assert.match(pem, /^-----BEGIN PUBLIC KEY-----\n[A-Za-z0-9+/=\n]+-----END PUBLIC KEY-----\n$/);
});

test("differential: the Python SDK verifies our receipts and we verify its", { skip: !hasAirSdk() && "air_blackbox SDK not importable" }, () => {
  const signer = new ReceiptSigner();
  const r = new ActionReceipt({
    agent_id: "support-agent", action_name: "issue_refund", action_category: "screening",
    payload_hash: hashPayload("order 991, $40"), covenant_hash: "ab".repeat(32), decision: "permit", authorized: true,
  });
  signer.signAuthorization(r);
  const out = python(`
import json, sys
from air_blackbox.gate.receipt import verify_receipt, hash_payload
d = json.loads(sys.stdin.read())
ok, detail = verify_receipt(d)
ok2, _ = verify_receipt(d, expected_public_key=d["signing_public_key"])
d2 = dict(d); d2["decision"] = "forbid"
bad, _ = verify_receipt(d2)
print(json.dumps({"ok": ok, "ok2": ok2, "bad": bad, "detail": detail, "payload_hash": hash_payload("order 991, $40")}))`, JSON.stringify(r.toDict()));
  const res = JSON.parse(out) as { ok: boolean; ok2: boolean; bad: boolean; detail: string; payload_hash: string };
  assert.equal(res.ok, true, res.detail);
  assert.equal(res.ok2, true);
  assert.equal(res.bad, false);
  assert.equal(res.payload_hash, hashPayload("order 991, $40"));

  // Theirs -> ours (Ed25519 explicitly: the SDK prefers ML-DSA-65 when the pqc extra is present).
  const theirs = python(`
import json, os
from air_blackbox.gate.receipt import ActionReceipt, ReceiptSigner, hash_payload
s = ReceiptSigner(private_key=os.urandom(32))
r = ActionReceipt(agent_id="py-agent", action_name="approve_loan", payload_hash=hash_payload({"amount": 75000}), decision="require_approval", authorized=False)
s.sign_authorization(r)
print(json.dumps(r.to_dict()))`);
  const theirReceipt = JSON.parse(theirs) as Record<string, unknown>;
  assert.equal(verifyReceipt(theirReceipt).verified, true);
  assert.equal(verifyReceipt({ ...theirReceipt, authorized: true } as never).verified, false);
  assert.equal((theirReceipt as { payload_hash: string }).payload_hash, hashPayload({ amount: 75000 }));
});
