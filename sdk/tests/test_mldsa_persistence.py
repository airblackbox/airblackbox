"""Regression tests for #63: the ML-DSA-65 signer must persist and resume its
keypair, so a tenant's public key survives restarts and old receipts keep
verifying. Also covers the provider layer (pqcrypto / liboqs) and the
end-to-end evidence bundle under a post-quantum tenant.

These tests run under the CI `python-test-pqc` job (pqcrypto installed) and
skip cleanly in the classical job.
"""

import glob
import json
import os

import pytest

from air_blackbox.gate.receipt import (
    HAS_MLDSA65,
    ActionReceipt,
    ReceiptSigner,
    hash_payload,
    verify_receipt,
)

pqc = pytest.mark.skipif(
    not HAS_MLDSA65, reason="no ML-DSA-65 provider installed (pqc extra)")


def _signed_receipt(signer, action="read_profile"):
    r = ActionReceipt(agent_id="screener", action_name=action,
                      payload_hash=hash_payload({"candidate": "fictional"}),
                      decision="permit", authorized=True)
    signer.sign_authorization(r)
    return r


# ---------------------------------------------------------------------------
# The core #63 defect: keypair persistence and resumption.
# ---------------------------------------------------------------------------

@pqc
def test_mldsa_keypair_resumes_and_old_receipts_still_verify():
    s1 = ReceiptSigner()
    assert s1.method == "ML-DSA-65"
    receipt = _signed_receipt(s1)

    # "Restart": rebuild a signer from the persisted keypair bytes.
    s2 = ReceiptSigner(mldsa_keypair=s1.mldsa_keypair)
    assert s2.method == "ML-DSA-65"
    assert s2.public_key_hex == s1.public_key_hex          # stable identity
    assert s2.verify_authorization(receipt)                # old receipt verifies
    # And the resumed signer signs receipts the original key verifies.
    assert s1.verify_authorization(_signed_receipt(s2))


@pqc
def test_provided_ed25519_key_is_honored_even_with_mldsa_available():
    """The literal #63 bug: a provided key was ignored and a fresh ML-DSA
    keypair generated instead, silently rotating the caller's identity."""
    pytest.importorskip("cryptography")
    seed = os.urandom(32)
    s1 = ReceiptSigner(private_key=seed)
    s2 = ReceiptSigner(private_key=seed)
    assert s1.method == s2.method == "ed25519"
    assert s1.public_key_hex == s2.public_key_hex


@pqc
def test_fresh_signer_prefers_mldsa_and_is_third_party_verifiable():
    s = ReceiptSigner()
    receipt = _signed_receipt(s)
    ok, detail = verify_receipt(receipt.to_dict())
    assert ok, detail
    assert "ML-DSA-65" in detail
    # Authenticity: a different expected key must be rejected.
    other = ReceiptSigner()
    ok, detail = verify_receipt(receipt.to_dict(),
                                expected_public_key=other.public_key_hex)
    assert not ok


@pqc
def test_tampered_mldsa_receipt_fails():
    s = ReceiptSigner()
    receipt = _signed_receipt(s)
    d = receipt.to_dict()
    d["action_name"] = "bulk_export"          # forge the action
    ok, _ = verify_receipt(d)
    assert not ok


# ---------------------------------------------------------------------------
# MCP tenant key file: v2 format, restart stability, legacy migration.
# ---------------------------------------------------------------------------

def _fresh_srv(tmp_path, monkeypatch):
    srv = pytest.importorskip("air_blackbox.mcp_server")
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()
    srv._signers.clear()
    return srv


@pqc
def test_new_tenant_gets_persisted_mldsa_key(tmp_path, monkeypatch):
    srv = _fresh_srv(tmp_path, monkeypatch)
    signer = srv._tenant_signer("_local")
    assert signer.method == "ML-DSA-65"

    key_files = glob.glob(str(tmp_path / "**" / ".air-receipt-key"),
                          recursive=True)
    assert len(key_files) == 1
    doc = json.loads(open(key_files[0]).read())
    assert doc["algorithm"] == "ML-DSA-65"
    assert doc["public_key"] == signer.public_key_hex

    # Restart: same public key, and receipts recorded before the restart
    # still verify.
    srv.record_action("read_profile", detail="candidate A")
    pub1 = signer.public_key_hex
    srv._signers.clear()
    assert srv._tenant_signer("_local").public_key_hex == pub1
    assert "ALL RECEIPTS VALID: 1/1" in srv.verify_receipts()


@pqc
def test_legacy_ed25519_tenant_is_not_rotated_to_mldsa(tmp_path, monkeypatch):
    """A pre-#63 tenant persisted a bare-hex Ed25519 seed. Its identity must
    stay Ed25519 forever - migrating would change its public key."""
    srv = _fresh_srv(tmp_path, monkeypatch)
    runs = srv._tenant_runs_dir("_local")
    os.makedirs(runs, exist_ok=True)
    seed = os.urandom(32)
    with open(os.path.join(runs, ".air-receipt-key"), "w") as f:
        f.write(seed.hex())

    signer = srv._tenant_signer("_local")
    assert signer.method == "ed25519"
    srv._signers.clear()
    assert srv._tenant_signer("_local").public_key_hex == signer.public_key_hex


# ---------------------------------------------------------------------------
# End to end: evidence bundle exported and verified under an ML-DSA tenant.
# ---------------------------------------------------------------------------

@pqc
def test_evidence_bundle_verifies_under_mldsa(tmp_path, monkeypatch):
    from air_blackbox.evidence_verify import verify_bundle

    srv = _fresh_srv(tmp_path, monkeypatch)
    srv.record_action("read_profile", detail="candidate A")
    srv.record_action("draft_message", detail="hello")

    out = srv.export_evidence()
    bundles = glob.glob(str(tmp_path / "**" / "*.air-evidence"),
                        recursive=True)
    assert bundles, out
    summary = verify_bundle(bundles[0],
                            hmac_key=os.environ.get("TRUST_SIGNING_KEY"))
    assert summary["records"] == 2
    assert summary["alterations"] == 0
    assert summary["fingerprint"].startswith("ML-DSA-65:")


@pqc
def test_mldsa_bundle_receipt_forgery_is_caught(tmp_path, monkeypatch):
    """Check 4 must reject a receipt signed by a key other than the bundle's
    ML-DSA signing key - the authenticity anchor, not just consistency."""
    import io
    import zipfile

    from air_blackbox.evidence_verify import VerificationFailure, verify_bundle

    srv = _fresh_srv(tmp_path, monkeypatch)
    srv.record_action("read_profile", detail="candidate A")

    # Forge: replace the stored receipt with one signed by an attacker's key.
    attacker = ReceiptSigner()
    rec_path = glob.glob(str(tmp_path / "**" / "*.air.json"), recursive=True)[0]
    rec = json.load(open(rec_path))
    forged = _signed_receipt(attacker, action=rec["receipt"]["action_name"])
    rec["receipt"] = forged.to_dict()
    json.dump(rec, open(rec_path, "w"))

    out = srv.export_evidence()
    bundles = glob.glob(str(tmp_path / "**" / "*.air-evidence"),
                        recursive=True)
    assert bundles, out
    with pytest.raises(VerificationFailure):
        verify_bundle(bundles[0],
                      hmac_key=os.environ.get("TRUST_SIGNING_KEY"),
                      out=io.StringIO())
