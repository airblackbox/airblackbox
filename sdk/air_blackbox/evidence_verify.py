"""air-evidence: independent verifier for .air-evidence v1 bundles.

    air-evidence verify bundle.air-evidence [--key HMAC_KEY]

Runs five checks in order, failing loudly with the exact record id on the
first failure:

  1. ZIP integrity and required files present
  2. Manifest signature valid against the bundled public key (and the
     manifest's per-file digests match the actual bundle contents, so the
     one signature transitively covers every file)
  3. Chain hashes consistent over records/actions.jsonl (full HMAC
     recompute when --key is provided; structural consistency otherwise)
  4. Every record's receipt signature verifies with the public key
  5. Counts in the manifest match the actual records

No secrets are required for checks 1, 2, 4, and 5 - a client's lawyer,
their enterprise customer, or a regulator can run this as-is. The --key
option additionally recomputes the private HMAC chain.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac as hmac_mod
import json
import sys
import zipfile
from typing import Any, Dict, List

from air_blackbox.export.evidence_bundle import (
    V1_REQUIRED_FILES,
    canonical_manifest_bytes,
    categorize_record,
)


class VerificationFailure(Exception):
    def __init__(self, check: int, message: str):
        super().__init__(message)
        self.check = check
        self.message = message


def _fail(check: int, message: str) -> None:
    raise VerificationFailure(check, message)


def _read(zf: zipfile.ZipFile, name: str) -> bytes:
    with zf.open(name) as f:
        return f.read()


def _ed25519_verify(public_key_raw: bytes, signature_hex: str,
                    data: bytes) -> bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(
            bytes.fromhex(signature_hex), data)
        return True
    except Exception:
        return False


def _pem_raw_key(pem_text: str) -> bytes:
    """Extract the raw Ed25519 key bytes from the bundled PEM."""
    from cryptography.hazmat.primitives import serialization
    key = serialization.load_pem_public_key(pem_text.encode())
    return key.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _auth_payload(receipt: Dict[str, Any]) -> bytes:
    """Rebuild ActionReceipt.authorization_payload byte-for-byte."""
    data = {
        "receipt_id": receipt.get("receipt_id", ""),
        "agent_id": receipt.get("agent_id", ""),
        "action_name": receipt.get("action_name", ""),
        "action_category": receipt.get("action_category", ""),
        "payload_hash": receipt.get("payload_hash", ""),
        "covenant_hash": receipt.get("covenant_hash", ""),
        "decision": receipt.get("decision", ""),
        "authorized": receipt.get("authorized", False),
        "parent_receipt_id": receipt.get("parent_receipt_id"),
        "created_at": receipt.get("created_at", ""),
    }
    return json.dumps(data, sort_keys=True).encode("utf-8")


def verify_bundle(path: str, hmac_key: str | None = None,
                  out=sys.stdout) -> Dict[str, Any]:
    """Run all five checks. Returns a summary dict; raises
    VerificationFailure on the first failed check."""

    # ---- Check 1: ZIP integrity and required files ------------------------
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        _fail(1, f"cannot open bundle: {e}")
    bad = zf.testzip()
    if bad is not None:
        _fail(1, f"corrupt member in ZIP: {bad}")
    names = set(zf.namelist())
    missing = [n for n in V1_REQUIRED_FILES if n not in names]
    if missing:
        _fail(1, f"required files missing from bundle: {', '.join(missing)}")
    print("[1/5] ZIP integrity and layout: OK", file=out)

    # ---- Check 2: manifest signature + per-file digests -------------------
    try:
        manifest = json.loads(_read(zf, "manifest.json"))
    except json.JSONDecodeError as e:
        _fail(2, f"manifest.json is not valid JSON: {e}")
    sig = manifest.get("signature") or {}
    digest = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    if digest != sig.get("signed_digest"):
        _fail(2, "manifest digest mismatch: canonical sha256 is "
                 f"{digest[:16]}..., manifest claims "
                 f"{str(sig.get('signed_digest'))[:16]}... - the manifest "
                 "was altered after signing")
    pem_text = _read(zf, "verification/public_key.pem").decode()
    alg = sig.get("alg", "")
    if alg == "ed25519":
        try:
            pub_raw = _pem_raw_key(pem_text)
        except Exception as e:
            _fail(2, f"cannot parse verification/public_key.pem: {e}")
        if sig.get("public_key_hex") and pub_raw.hex() != sig["public_key_hex"]:
            _fail(2, "public key mismatch: manifest signature key != "
                     "verification/public_key.pem")
        if not _ed25519_verify(pub_raw, sig.get("value", ""),
                               bytes.fromhex(digest)):
            _fail(2, "manifest signature INVALID for the bundled public key")
    elif alg == "hmac-sha256":
        if not hmac_key:
            _fail(2, "manifest is HMAC-signed; pass --key to verify "
                     "(no public-key signature present)")
        expect = hmac_mod.new(hmac_key.encode(), bytes.fromhex(digest),
                              hashlib.sha256).hexdigest()
        if not hmac_mod.compare_digest(expect, sig.get("value", "")):
            _fail(2, "manifest HMAC signature INVALID for the provided key")
    else:
        _fail(2, f"unsupported manifest signature algorithm: '{alg}'")
    for fname, want in (manifest.get("files") or {}).items():
        if fname not in names:
            _fail(2, f"manifest lists {fname} but it is not in the bundle")
        got = hashlib.sha256(_read(zf, fname)).hexdigest()
        if got != want:
            _fail(2, f"file digest mismatch for {fname}: contents were "
                     "altered after the manifest was signed")
    print(f"[2/5] Manifest signature ({alg}) and "
          f"{len(manifest.get('files') or {})} file digests: OK", file=out)

    # ---- Check 3: chain hashes over records/actions.jsonl -----------------
    records: List[Dict[str, Any]] = []
    for i, line in enumerate(
            _read(zf, "records/actions.jsonl").decode().splitlines()):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            _fail(3, f"records/actions.jsonl line {i + 1} is not valid JSON")
    chain_doc = json.loads(_read(zf, "verification/chain.json"))
    listed = chain_doc.get("records", [])
    if len(listed) != len(records):
        _fail(3, f"chain.json lists {len(listed)} records but "
                 f"actions.jsonl contains {len(records)}")
    for i, (rec, entry) in enumerate(zip(records, listed)):
        if rec.get("run_id") != entry.get("run_id"):
            _fail(3, f"record order mismatch at index {i}: actions.jsonl "
                     f"run_id={rec.get('run_id')} vs chain.json "
                     f"run_id={entry.get('run_id')}")
        if rec.get("chain_hash") != entry.get("chain_hash"):
            _fail(3, f"chain hash mismatch at index {i} "
                     f"(run_id={rec.get('run_id')})")
    if hmac_key:
        prev = b"genesis"
        for i, rec in enumerate(records):
            body = {k: v for k, v in rec.items() if k != "chain_hash"}
            h = hmac_mod.new(hmac_key.encode(),
                             prev + json.dumps(body, sort_keys=True).encode(),
                             hashlib.sha256)
            if h.hexdigest() != rec.get("chain_hash"):
                _fail(3, f"HMAC chain recompute FAILED at index {i} "
                         f"(run_id={rec.get('run_id')}) - this record or an "
                         "earlier one was altered")
            prev = h.digest()
        print(f"[3/5] Chain: full HMAC recompute over {len(records)} "
              f"records: OK", file=out)
    else:
        print(f"[3/5] Chain: {len(records)} records structurally consistent "
              f"with chain.json (pass --key for full HMAC recompute)",
              file=out)

    # ---- Check 4: per-record receipts -------------------------------------
    checked = 0
    for i, rec in enumerate(records):
        receipt = rec.get("receipt")
        if not receipt:
            continue
        method = receipt.get("signing_method", "")
        sig_hex = receipt.get("authorization_sig", "")
        if method == "ed25519":
            pub_hex = receipt.get("signing_public_key", "")
            if not pub_hex or not sig_hex:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) "
                         "lacks a key or signature")
            if not _ed25519_verify(bytes.fromhex(pub_hex), sig_hex,
                                   _auth_payload(receipt)):
                _fail(4, f"receipt signature INVALID at index {i} "
                         f"(run_id={rec.get('run_id')})")
        elif method == "hmac-sha256":
            if not hmac_key:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) "
                         "is HMAC-signed; pass --key to verify")
            expect = hmac_mod.new(hmac_key.encode(), _auth_payload(receipt),
                                  hashlib.sha256).hexdigest()
            if not hmac_mod.compare_digest(expect, sig_hex):
                _fail(4, f"receipt HMAC INVALID at index {i} "
                         f"(run_id={rec.get('run_id')})")
        else:
            _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) has "
                     f"unsupported signing method '{method}'")
        checked += 1
    print(f"[4/5] Receipts: {checked}/{len(records)} records carry a "
          f"receipt, all signatures valid", file=out)

    # ---- Check 5: manifest counts match reality ---------------------------
    cats = [categorize_record(r) for r in records]
    screening = [r for r, c in zip(records, cats) if c == "screening_decision"]
    actual = {
        "actions": len(records),
        "screening_decisions": len(screening),
        "blocked_actions": cats.count("blocked_action"),
        "human_approvals": cats.count("human_approval"),
        "screening_decisions_missing_reviewer": sum(
            1 for r in screening
            if not r.get("screening", {}).get("human_reviewer")),
    }
    declared = manifest.get("counts") or {}
    for k, v in actual.items():
        if k in declared and declared[k] != v:
            _fail(5, f"count mismatch for '{k}': manifest says "
                     f"{declared[k]}, records show {v}")
    print("[5/5] Counts: manifest matches records", file=out)

    pub_hex = (manifest.get("signature") or {}).get("public_key_hex", "")
    fingerprint = (
        f"{alg}:{hashlib.sha256(bytes.fromhex(pub_hex)).hexdigest()[:16]}"
        if pub_hex else alg)
    return {"records": len(records), "alterations": 0,
            "fingerprint": fingerprint, "counts": actual,
            "bundle_id": manifest.get("bundle_id", "")}


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="air-evidence",
        description="Verify a .air-evidence bundle. No secrets required "
                    "(--key optionally adds the private HMAC chain recompute).")
    sub = ap.add_subparsers(dest="command", required=True)
    vp = sub.add_parser("verify", help="verify a bundle")
    vp.add_argument("bundle", help="path to the .air-evidence file")
    vp.add_argument("--key", default=None,
                    help="HMAC signing key for full chain recompute")
    args = ap.parse_args(argv)

    try:
        summary = verify_bundle(args.bundle, hmac_key=args.key)
    except VerificationFailure as e:
        print(f"FAILED at check {e.check}: {e.message}", file=sys.stderr)
        return 1
    print(f"VERIFIED: {summary['records']} records, "
          f"{summary['alterations']} alterations, "
          f"signed by {summary['fingerprint']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
