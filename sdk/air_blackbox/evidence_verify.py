"""air-evidence: independent verifier for .air-evidence v1 bundles.

    air-evidence verify bundle.air-evidence [--key HMAC_KEY] [--tsa-cacert CA]

Runs six checks in order, failing loudly with the exact record id on the
first failure:

  1. ZIP integrity and required files present
  2. Manifest signature valid against the bundled public key (and the
     manifest's per-file digests match the actual bundle contents, so the
     one signature transitively covers every file)
  3. Chain hashes consistent over records/actions.jsonl, and the chain was
     recorded intact at export (full HMAC recompute when --key is provided)
  4. Every record's receipt signature verifies with the public key
  5. Counts in the manifest match the actual records
  6. External anchor: the key-free chain head re-derived over the records
     matches the RFC 3161 timestamp countersigned by an external authority -
     the check that makes an operator rewrite detectable. An unanchored
     bundle is reported as such (no rewrite protection), never silently
     passed as fully verified.

No secrets are required - a client's lawyer, their enterprise customer, or a
regulator can run this as-is. The --key option additionally recomputes the
private HMAC chain; --tsa-cacert lets check 6 run fully offline.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac as hmac_mod
import json
import sys
import zipfile
from typing import Any, Dict, List

from air_blackbox.export.evidence_bundle import (
    V1_MAPPING_PREFIX,
    V1_REQUIRED_FILES,
    canonical_manifest_bytes,
    categorize_record,
)
from air_blackbox.anchor.head import head_over_entries


def _rederive_head(records: List[Dict[str, Any]], up_to_seq=None) -> str:
    """Re-derive the key-free chain head over the bundle's own records.

    Mirrors compute_head() but works on the in-memory record list from
    actions.jsonl. Uses the shared head_over_entries() so the derivation can
    never drift from the writer's. A single altered chain_hash changes this
    head, which is what lets a no-secret verifier detect tampering by checking
    the head against the external timestamp token.
    """
    entries = []
    for r in records:
        ch = r.get("chain_hash")
        if not ch:
            continue
        seq = r.get("chain_seq") or 0
        if up_to_seq is not None and seq > up_to_seq:
            continue
        entries.append((seq, ch))
    return head_over_entries(entries)


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


def _hex_block_key(pem_text: str) -> str:
    """Extract the lowercase hex key from an 'AIR PUBLIC KEY HEX' block - the
    bundle format for keys with no standard PEM encoding (ML-DSA-65).
    Returns "" if the text is not such a block."""
    lines = [ln.strip() for ln in pem_text.strip().splitlines()]
    if (len(lines) >= 3
            and lines[0] == "-----BEGIN AIR PUBLIC KEY HEX-----"
            and lines[-1] == "-----END AIR PUBLIC KEY HEX-----"):
        body = "".join(lines[1:-1]).lower()
        try:
            bytes.fromhex(body)
            return body
        except ValueError:
            return ""
    return ""


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
                  tsa_cacert: str | None = None,
                  out=sys.stdout) -> Dict[str, Any]:
    """Run all six checks. Returns a summary dict; raises
    VerificationFailure on the first failed check.

    Check 6 (external anchor) is what defeats an operator rewrite: it
    re-derives the key-free chain head over the records and checks it against
    the RFC 3161 timestamp token embedded in the bundle. A timestamp is a
    countersignature from a key the operator does NOT hold, so a rewritten -
    even perfectly re-signed - history no longer matches it.
    """

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
    # The mapping member is required but its name is not pinned: bundles from
    # before Colorado repealed SB 24-205 carry mapping/sb24-205.json, current
    # ones mapping/sb26-189.json. Evidence must keep verifying after the
    # statute it was mapped to is gone - the records are the invariant.
    if not any(n.startswith(V1_MAPPING_PREFIX) and n.endswith(".json")
               for n in names):
        _fail(1, "required files missing from bundle: mapping/*.json "
                 "(no regulator mapping present)")
    print("[1/6] ZIP integrity and layout: OK", file=out)

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
    manifest_pubkey_hex = None  # the bundle's signing key; anchors Check 4
    if alg == "ed25519":
        try:
            pub_raw = _pem_raw_key(pem_text)
        except Exception as e:
            _fail(2, f"cannot parse verification/public_key.pem: {e}")
        manifest_pubkey_hex = pub_raw.hex()
        if sig.get("public_key_hex") and pub_raw.hex() != sig["public_key_hex"]:
            _fail(2, "public key mismatch: manifest signature key != "
                     "verification/public_key.pem")
        if not _ed25519_verify(pub_raw, sig.get("value", ""),
                               bytes.fromhex(digest)):
            _fail(2, "manifest signature INVALID for the bundled public key")
    elif alg == "ML-DSA-65":
        from air_blackbox.gate.receipt import HAS_MLDSA65, mldsa_verify
        if not HAS_MLDSA65:
            _fail(2, "manifest is ML-DSA-65-signed but no verifier is "
                     "installed - pip install 'air-blackbox[pqc]'")
        # ML-DSA keys are shipped as a hex block (they have no standard
        # SubjectPublicKeyInfo PEM encoding in `cryptography` yet).
        pub_hex = _hex_block_key(pem_text)
        if not pub_hex:
            _fail(2, "cannot parse verification/public_key.pem as an ML-DSA "
                     "hex key block")
        manifest_pubkey_hex = pub_hex
        if sig.get("public_key_hex") and pub_hex != sig["public_key_hex"].lower():
            _fail(2, "public key mismatch: manifest signature key != "
                     "verification/public_key.pem")
        if not mldsa_verify(bytes.fromhex(pub_hex),
                            bytes.fromhex(digest),
                            bytes.fromhex(sig.get("value", ""))):
            _fail(2, "manifest ML-DSA-65 signature INVALID for the bundled "
                     "public key")
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
    print(f"[2/6] Manifest signature ({alg}) and "
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
    stamped = chain_doc.get("verification_at_export") or {}
    if stamped.get("intact") is False:
        _fail(3, "the bundle's own chain verification recorded the chain as "
                 "NOT intact at export time - a broken chain was exported "
                 f"(first break at record {stamped.get('first_break_at')})")
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
        print(f"[3/6] Chain: full HMAC recompute over {len(records)} "
              f"records: OK", file=out)
    else:
        print(f"[3/6] Chain: {len(records)} records structurally consistent "
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
            # Anchor authenticity to the bundle's signing key: a receipt must
            # be signed by the SAME key that signed the manifest, otherwise
            # "all signatures valid" would certify nothing about who signed.
            if manifest_pubkey_hex and pub_hex.lower() != manifest_pubkey_hex:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) is "
                         "signed by a key other than the bundle's signing key")
            if not _ed25519_verify(bytes.fromhex(pub_hex), sig_hex,
                                   _auth_payload(receipt)):
                _fail(4, f"receipt signature INVALID at index {i} "
                         f"(run_id={rec.get('run_id')})")
        elif method == "ML-DSA-65":
            from air_blackbox.gate.receipt import HAS_MLDSA65, mldsa_verify
            if not HAS_MLDSA65:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) "
                         "is ML-DSA-65-signed but no verifier is installed - "
                         "pip install 'air-blackbox[pqc]'")
            pub_hex = receipt.get("signing_public_key", "")
            if not pub_hex or not sig_hex:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) "
                         "lacks a key or signature")
            # Same authenticity anchor as ed25519: the receipt key must be
            # the bundle's signing key.
            if manifest_pubkey_hex and pub_hex.lower() != manifest_pubkey_hex:
                _fail(4, f"receipt at index {i} (run_id={rec.get('run_id')}) is "
                         "signed by a key other than the bundle's signing key")
            if not mldsa_verify(bytes.fromhex(pub_hex), _auth_payload(receipt),
                                bytes.fromhex(sig_hex)):
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
    print(f"[4/6] Receipts: {checked}/{len(records)} records carry a "
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
    print("[5/6] Counts: manifest matches records", file=out)

    # ---- Check 6: external anchor (operator-rewrite detection) -------------
    # The manifest carries the anchor (it is inside the signed manifest, so an
    # honest manifest cannot lie about whether it was anchored). We re-derive
    # the key-free head over the ACTUAL records and check it against the
    # timestamp token - so a rewritten history whose anchor was not correctly
    # re-issued no longer matches, and an unanchored bundle is reported as
    # such rather than silently blessed.
    anchor = manifest.get("anchor") or {}
    anchor_state = "absent"
    if anchor.get("anchored") and anchor.get("tsr_b64"):
        from air_blackbox.anchor.tsa import verify_anchor_bytes
        try:
            tsr = base64.b64decode(anchor["tsr_b64"])
        except Exception as e:
            _fail(6, f"anchor token is not valid base64: {e}")
        rederived = _rederive_head(records, up_to_seq=anchor.get("seq_max"))
        ok, detail = verify_anchor_bytes(rederived, tsr, ca_pem=tsa_cacert)
        if ok:
            anchor_state = "verified"
            print("[6/6] External anchor: VERIFIED - the timestamp authority's "
                  "countersignature commits to the records' head (a rewrite "
                  "would not match)", file=out)
        elif "imprint mismatch" in (detail or ""):
            _fail(6, "REWRITE DETECTED - the records' head does not match what "
                     "the external timestamp countersigned. The history was "
                     "rewritten after it was anchored.")
        else:
            # Could not complete cryptographic verification (no CA / offline).
            # Not proof of tampering; report honestly rather than pass or fail.
            anchor_state = "unverified"
            print(f"[6/6] External anchor: present but NOT cryptographically "
                  f"verified ({detail}). Supply --tsa-cacert (or run with "
                  "network access) to check the timestamp.", file=out)
    else:
        gap = anchor.get("error") or anchor.get("status") or "no anchor recorded"
        print("[6/6] External anchor: NONE - this bundle is not anchored "
              f"({gap}), so an operator rewrite of the records cannot be "
              "detected by this verifier. The signature and chain checks above "
              "still hold. Not a failure.", file=out)

    # ---- Check 6b: public transparency-log anchor (M2), if present --------
    # The Rekor anchor is the second, stronger rail: the RFC 3161 timestamp
    # can be re-obtained by an attacker for a rewritten head, but an entry in
    # a public APPEND-ONLY log can never be removed - so old anchors remain
    # discoverable forever (see audit_runs_against_log for the full sweep).
    rekor = anchor.get("rekor") or {}
    if rekor.get("uuid"):
        from air_blackbox.anchor.rekor import verify_bundle_anchor
        try:
            logged = json.loads(
                base64.b64decode(rekor["payload_b64"]).decode())
            bound = int(logged.get("chain_seq_max", -1))
        except Exception as e:
            _fail(6, f"rekor anchor payload unparseable: {e}")
        ok, detail = verify_bundle_anchor(
            {bound: _rederive_head(records, up_to_seq=bound)}, rekor)
        if not ok:
            if "REWRITE DETECTED" in detail:
                _fail(6, f"public-log anchor: {detail}")
            _fail(6, f"public-log anchor invalid: {detail}")
        anchor_state = ("verified+public-log" if anchor_state == "verified"
                        else "public-log")
        print(f"[6b ] Public-log anchor: {detail} "
              f"(rekor uuid {rekor['uuid'][:16]}..., log index "
              f"{rekor.get('log_index')}). The entry is permanent; "
              "audit every anchor under this key with air-evidence audit-log.",
              file=out)

    pub_hex = (manifest.get("signature") or {}).get("public_key_hex", "")
    fingerprint = (
        f"{alg}:{hashlib.sha256(bytes.fromhex(pub_hex)).hexdigest()[:16]}"
        if pub_hex else alg)
    return {"records": len(records), "alterations": 0,
            "fingerprint": fingerprint, "counts": actual,
            "anchor": anchor_state,
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
    vp.add_argument("--tsa-cacert", default=None,
                    help="PEM CA chain of the timestamp authority, for offline "
                         "anchor verification (else FreeTSA's CA is fetched)")
    args = ap.parse_args(argv)

    try:
        summary = verify_bundle(args.bundle, hmac_key=args.key,
                                tsa_cacert=args.tsa_cacert)
    except VerificationFailure as e:
        print(f"FAILED at check {e.check}: {e.message}", file=sys.stderr)
        return 1
    anchor = summary.get("anchor", "absent")
    qualifier = {
        "verified": "chain externally anchored & countersigned",
        "unverified": "signature valid; anchor present but UNVERIFIED "
                      "(pass --tsa-cacert or allow network)",
        "absent": "signature valid; NOT anchored - an operator rewrite would "
                  "not be detectable by this check",
    }.get(anchor, anchor)
    print(f"VERIFIED [{qualifier}]: {summary['records']} records, "
          f"{summary['alterations']} alterations, "
          f"signed by {summary['fingerprint']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
