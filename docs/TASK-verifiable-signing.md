# TASK: Make receipt signing auto-select AND third-party verifiable

Status: NOT STARTED. Queued from the May 30 2026 session. Do this fresh. This is
the signing path the entire product claim rests on. A subtle bug here is the most
expensive kind, so build it carefully and run the acceptance test before shipping.

## Background: what already works
ReceiptSigner in sdk/air_blackbox/gate/receipt.py ALREADY auto-selects the
signing method: ML-DSA-65 if oqs is importable, else Ed25519 if cryptography is
importable, else HMAC-SHA256. That logic is correct and should not be rebuilt.

## The real problem
A default `pip install air-blackbox` signs with HMAC-SHA256, because neither
cryptography nor oqs is a declared dependency. HMAC is symmetric: it needs a
shared secret, so it is NOT third-party verifiable. Worse, even with Ed25519,
receipts are not independently verifiable today because of two gaps:

GAP 1: the ActionReceipt does not record WHICH method signed it, nor the public
key. method and public_key_hex live on the signer object, not in the receipt
JSON. An auditor handed the receipt JSON cannot tell what algorithm or key to use.

GAP 2: Gate.verify() only works via the same in-memory ReceiptSigner that signed
it (it holds the key). A third party with only the receipt JSON has no way to
verify. So "third-party verifiable" is not actually true yet.

## Proven concept (verified in the May 30 session)
A receipt carrying signing_method + signing_public_key + signature CAN be verified
from the JSON alone, with no signer object and no shared secret, for Ed25519 and
ML-DSA-65 (both asymmetric). Tampering any signed field breaks verification.
HMAC cannot do this and must remain the emergency fallback only, never default.

## The fix, three parts in order
1. SELF-DESCRIBING RECEIPTS: at signing time, stamp each ActionReceipt with
   signing_method (e.g. "ed25519", "ML-DSA-65") and signing_public_key (hex).
   Add both fields to ActionReceipt and to to_dict()/to_json(). For HMAC, record
   method "hmac-sha256" and NO public key (it is not third-party verifiable, and
   the receipt should be honest about that).
2. KEY-ONLY VERIFICATION PATH: add a standalone verifier that takes only a
   receipt dict/JSON and verifies using the embedded method + public key, with no
   ReceiptSigner instance. For Ed25519/ML-DSA-65 use the public key. For HMAC,
   return "not independently verifiable" rather than a false PASS.
3. DEPENDENCIES (pyproject.toml): move cryptography from the optional [gate]
   extra to hard `dependencies` so Ed25519 is the guaranteed floor. Keep oqs as an
   optional extra: add `pqc = ["oqs>=0.10"]` (verify exact package/version name).
   Then default install signs Ed25519 (verifiable); `pip install air-blackbox[pqc]`
   signs ML-DSA-65. Bump version to 1.12.3 (PyPI forbids re-uploading 1.12.2).

## Acceptance test (GATES completion)
1. Fresh venv, `pip install` the built wheel (no extras). Sign a receipt.
   - g.signing_method MUST be "ed25519" (NOT hmac-sha256).
2. Serialize the receipt to JSON. Confirm it contains signing_method AND
   signing_public_key.
3. In a SEPARATE process with NO signer object, load only the JSON and verify
   using the embedded method+pubkey. MUST verify True.
4. Flip one byte in any signed field. Re-verify. MUST be False.
5. Fresh venv with `[pqc]` extra. Sign a receipt. method MUST be "ML-DSA-65",
   and the key-only verify MUST still pass and tamper MUST still fail.
6. Run scripts/release_check.sh -> ALL CHECKS PASSED before twine upload.

If step 4 ever passes, the verifier is broken. Stop and fix.

## Only AFTER acceptance passes
Then the public claim "signed, third-party-verifiable receipts, post-quantum
available" is true by default and safe to put in the README and any post.
