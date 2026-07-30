"""Tests for external anchoring (binding history, M1).

The headline is test_rewrite_is_detected_by_anchor - the one test the whole
milestone exists for: a rewritten, re-signed history passes chain verification
but FAILS anchor verification, because the old timestamp countersigned the old
head. Everything else supports it.

A local RFC 3161 TSA is stood up with openssl so these run offline / in CI.
"""

import os
import shutil
import subprocess

import pytest

from air_blackbox.anchor import compute_head, verify_anchor_bytes
from air_blackbox.anchor.tsa import AnchorResult, make_query
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.trust.chain import AuditChain

if shutil.which("openssl") is None:  # pragma: no cover
    pytest.skip("openssl not available", allow_module_level=True)


class LocalTSA:
    """A throwaway RFC 3161 TSA (CA + timestamping cert) for offline tests."""

    def __init__(self, d: str):
        self.dir = d
        os.makedirs(d, exist_ok=True)
        self.ca_pem = os.path.join(d, "ca.pem")
        self._setup()

    def _ossl(self, *args, **kw):
        return subprocess.run(["openssl", *args], capture_output=True,
                              cwd=self.dir, timeout=30, **kw)

    def _setup(self):
        self._ossl("req", "-x509", "-newkey", "ec",
                   "-pkeyopt", "ec_paramgen_curve:P-256",
                   "-keyout", "ca.key", "-out", "ca.pem", "-nodes",
                   "-subj", "/CN=Test Root CA", "-days", "2")
        self._ossl("req", "-newkey", "ec",
                   "-pkeyopt", "ec_paramgen_curve:P-256",
                   "-keyout", "tsa.key", "-out", "tsa.csr", "-nodes",
                   "-subj", "/CN=Test TSA")
        with open(os.path.join(self.dir, "tsa.ext"), "w") as f:
            f.write("extendedKeyUsage=critical,timeStamping\n")
        self._ossl("x509", "-req", "-in", "tsa.csr", "-CA", "ca.pem",
                   "-CAkey", "ca.key", "-CAcreateserial", "-out", "tsa.pem",
                   "-days", "2", "-extfile", "tsa.ext")
        with open(os.path.join(self.dir, "tsa.conf"), "w") as f:
            f.write(
                "[tsa]\ndefault_tsa = c\n[c]\nserial = ./serial\n"
                "crypto_device = builtin\nsigner_cert = ./tsa.pem\n"
                "certs = ./ca.pem\nsigner_key = ./tsa.key\nsigner_digest = sha256\n"
                "default_policy = 1.2.3.4.1\ndigests = sha256, sha384, sha512\n"
                "accuracy = secs:1\nordering = yes\ntsa_name = yes\n"
                "ess_cert_id_chain = no\n")
        with open(os.path.join(self.dir, "serial"), "w") as f:
            f.write("01\n")

    def reply(self, head_hex: str) -> bytes:
        """Countersign a head, returning the DER RFC 3161 token."""
        with open(os.path.join(self.dir, "req.tsq"), "wb") as f:
            f.write(make_query(head_hex))
        self._ossl("ts", "-reply", "-config", "tsa.conf",
                   "-queryfile", "req.tsq", "-out", "resp.tsr")
        with open(os.path.join(self.dir, "resp.tsr"), "rb") as f:
            return f.read()


def _write_chain(runs_dir, key, actions):
    chain = AuditChain(runs_dir=runs_dir, signing_key=key)
    for i, action in enumerate(actions):
        chain.write({
            "run_id": f"00000000-0000-0000-0000-{i:012d}",
            "action": action, "status": "success",
            "timestamp": f"2026-07-17T00:00:{i:02d}Z",
        })


def test_head_is_deterministic_and_chain_bound(tmp_path):
    d = str(tmp_path / "runs"); os.makedirs(d)
    _write_chain(d, "k", ["read_profile", "draft_message", "send_message"])
    h1 = compute_head(d)
    assert h1 and len(h1) == 64
    assert compute_head(d) == h1                 # deterministic

    # The head binds to the chain (chain_hash per record), so re-signing a
    # different history - the exact thing an operator rewrite does - changes
    # the head. (A content edit that leaves a stale chain_hash is caught by
    # verify_chain instead; the head's job is to bind add/remove/re-sign.)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    _write_chain(d, "k", ["read_profile", "draft_message", "block_send"])
    assert compute_head(d) != h1


def test_anchor_verifies_against_its_head(tmp_path):
    d = str(tmp_path / "runs"); os.makedirs(d)
    _write_chain(d, "k", ["read_profile", "send_message"])
    head = compute_head(d)

    tsa = LocalTSA(str(tmp_path / "tsa"))
    tsr = tsa.reply(head)

    ok, detail = verify_anchor_bytes(head, tsr, ca_pem=tsa.ca_pem)
    assert ok, detail


def test_rewrite_is_detected_by_anchor(tmp_path):
    """THE test. Anchor a history, then rewrite and re-sign it. The chain still
    verifies (operator holds the key), but the anchor does not: the old
    timestamp countersigned the old head."""
    d = str(tmp_path / "runs"); os.makedirs(d)
    key = "operator-key"
    _write_chain(d, key, ["read_profile", "advance_candidate", "send_offer"])

    head = compute_head(d)
    tsa = LocalTSA(str(tmp_path / "tsa"))
    tsr = tsa.reply(head)                          # anchored at time T
    assert verify_anchor_bytes(head, tsr, ca_pem=tsa.ca_pem)[0]

    # The operator rewrites history: same key, but "send_offer" becomes
    # "reject_candidate" and a step is dropped. Rebuild the whole chain.
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    _write_chain(d, key, ["read_profile", "reject_candidate"])

    # The rewritten chain verifies cleanly - this is the operator's forgery.
    engine = ReplayEngine(runs_dir=d)
    engine.load()
    assert engine.verify_chain(signing_key=key).intact, \
        "rewritten chain should pass chain verification (operator re-signed it)"

    # But the anchor does not: the current head no longer matches the token.
    new_head = compute_head(d)
    assert new_head != head
    ok, detail = verify_anchor_bytes(new_head, tsr, ca_pem=tsa.ca_pem)
    assert not ok
    assert "imprint mismatch" in detail or "rewritten" in detail


def test_missing_token_is_a_gap_not_a_pass(tmp_path):
    ok, detail = verify_anchor_bytes("deadbeef" * 8, b"", ca_pem=None)
    assert not ok and "no timestamp token" in detail


# --- MCP integration: export_evidence anchors, verify_anchor detects rewrite ---
# These need the MCP SDK; skip cleanly if it is not installed (the core anchor
# tests above do not need it).

def _mcp_server(monkeypatch, tmp_path):
    pytest.importorskip("mcp")
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear(); srv._signers.clear()
    return srv


def _patch_local_tsa(monkeypatch, tsa: "LocalTSA"):
    """Make the MCP server's anchor path use a local offline TSA."""
    def fake_timestamp_head(head_hex, tsa_urls=None):
        return AnchorResult(ok=True, head=head_hex, tsr=tsa.reply(head_hex),
                            tsa_url="local-test-tsa", timestamp="T0")
    # export_evidence imports timestamp_head from air_blackbox.anchor at call
    # time, so patch the attribute on that module by its string path.
    monkeypatch.setattr("air_blackbox.anchor.timestamp_head", fake_timestamp_head)
    monkeypatch.setenv("AIR_TSA_CACERT", tsa.ca_pem)


def test_mcp_export_anchors_and_verify_anchor_passes(tmp_path, monkeypatch):
    srv = _mcp_server(monkeypatch, tmp_path)
    tsa = LocalTSA(str(tmp_path / "tsa"))
    _patch_local_tsa(monkeypatch, tsa)

    srv.record_action("read_profile")
    srv.record_action("advance_candidate")
    out = srv.export_evidence()
    assert "Anchor: head bound to" in out

    assert "ANCHOR VALID" in srv.verify_anchor()


def test_mcp_rewrite_breaks_anchor_but_not_chain(tmp_path, monkeypatch):
    """Full-stack version of THE test through the MCP tools: after a rewrite,
    verify_chain and verify_receipts still pass, but verify_anchor breaks."""
    import glob
    srv = _mcp_server(monkeypatch, tmp_path)
    tsa = LocalTSA(str(tmp_path / "tsa"))
    _patch_local_tsa(monkeypatch, tsa)

    srv.record_action("read_profile")
    srv.record_action("advance_candidate")
    srv.export_evidence()                       # anchors head at seq 2
    assert "ANCHOR VALID" in srv.verify_anchor()

    # Operator rewrites history: rebuild the two records with a changed action,
    # re-signing the chain and re-signing the receipts with the tenant's keys.
    runs = str(tmp_path)
    for f in glob.glob(os.path.join(runs, "*.air.json")):
        os.remove(f)
    srv._chains.clear()                         # fresh chain over the same store
    srv.record_action("read_profile")
    srv.record_action("reject_candidate")       # the forged outcome

    # The rewritten chain and receipts verify cleanly - the operator holds the keys.
    assert "CHAIN INTACT" in srv.verify_chain()
    assert "ALL RECEIPTS VALID" in srv.verify_receipts()

    # But the anchor does not: the countersigned head no longer matches.
    out = srv.verify_anchor()
    assert "ANCHOR BROKEN" in out


def test_mcp_anchor_gap_is_reported_not_hidden(tmp_path, monkeypatch):
    srv = _mcp_server(monkeypatch, tmp_path)

    # No reachable TSA -> anchor gap.
    monkeypatch.setattr("air_blackbox.anchor.timestamp_head",
                        lambda h, u=None: AnchorResult(
                            ok=False, head=h, error="no TSA reachable"))
    srv.record_action("read_profile")
    out = srv.export_evidence()
    assert "Anchor: GAP" in out
    assert "NO ANCHOR" in srv.verify_anchor()


# --- Evidence-bundle anchor wiring (issue #57): air-evidence verify must
# consult the external anchor, so a rewrite is detected by the same command a
# regulator runs, not only by the separate MCP verify_anchor tool. ----------

def _bundle_records_with_seq(signer, n=3):
    """n chained records (chain_seq + chain_hash + signed receipt), the shape
    the MCP export writes into a bundle."""
    import hashlib as _h, hmac as _hm, json as _j
    from air_blackbox.gate.receipt import ActionReceipt, hash_payload
    recs = []
    prev = b"genesis"
    for i in range(n):
        r = ActionReceipt(agent_id="t", action_name=f"act_{i}",
                          payload_hash=hash_payload(f"d{i}"),
                          covenant_hash="cov", decision="permit", authorized=True)
        signer.sign_authorization(r)
        rec = {"run_id": f"run-{i}", "chain_seq": i,
               "timestamp": f"2026-07-18T00:00:0{i}Z", "action": f"act_{i}",
               "status": "success", "receipt": r.to_dict()}
        body = {k: v for k, v in rec.items() if k != "chain_hash"}
        h = _hm.new(b"k", prev + _j.dumps(body, sort_keys=True).encode(), _h.sha256)
        rec["chain_hash"] = h.hexdigest()
        prev = h.digest()
        recs.append(rec)
    return recs


def _make_bundle(tmp_path, signer, records, anchor_manifest):
    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    path, _ = generate_evidence_bundle_v1(
        chain_entries=records, tenant="t", signer=signer,
        chain_verification={"intact": True, "verified_records": len(records)},
        anchor_manifest=anchor_manifest, output_dir=str(tmp_path))
    return path


def test_evidence_verify_confirms_a_valid_anchor(tmp_path):
    import base64, io
    from air_blackbox.anchor.head import head_over_entries
    from air_blackbox.gate.receipt import ReceiptSigner
    from air_blackbox.evidence_verify import verify_bundle
    tsa = LocalTSA(str(tmp_path / "tsa"))
    signer = ReceiptSigner(private_key=os.urandom(32), hmac_key="k")
    recs = _bundle_records_with_seq(signer)
    head = head_over_entries([(r["chain_seq"], r["chain_hash"]) for r in recs])
    anchor = {"anchored": True, "head": head, "seq_max": len(recs) - 1,
              "tsr_b64": base64.b64encode(tsa.reply(head)).decode()}
    path = _make_bundle(tmp_path, signer, recs, anchor)
    summary = verify_bundle(path, tsa_cacert=tsa.ca_pem, out=io.StringIO())
    assert summary["anchor"] == "verified"


def test_evidence_verify_DETECTS_rewrite_via_anchor(tmp_path):
    # THE test for #57: the bundle's records produce a different head than the
    # one the timestamp countersigned (history was rewritten after anchoring).
    # Checks 1-5 pass (manifest honestly re-signed over the new records); only
    # the external anchor - a key the operator does not hold - catches it.
    import base64, io
    from air_blackbox.anchor.head import head_over_entries
    from air_blackbox.gate.receipt import ReceiptSigner
    from air_blackbox.evidence_verify import verify_bundle, VerificationFailure
    tsa = LocalTSA(str(tmp_path / "tsa"))
    signer = ReceiptSigner(private_key=os.urandom(32), hmac_key="k")

    original = _bundle_records_with_seq(signer)
    original_head = head_over_entries(
        [(r["chain_seq"], r["chain_hash"]) for r in original])
    # Anchor commits to the ORIGINAL head...
    anchor = {"anchored": True, "head": original_head, "seq_max": len(original) - 1,
              "tsr_b64": base64.b64encode(tsa.reply(original_head)).decode()}
    # ...but the bundle ships a REWRITTEN history (re-chained, re-signed).
    rewritten = _bundle_records_with_seq(signer)
    rewritten[1]["action"] = "COVER_UP"
    import hashlib as _h, hmac as _hm, json as _j
    prev = b"genesis"
    for rec in rewritten:
        body = {k: v for k, v in rec.items() if k != "chain_hash"}
        rec["chain_hash"] = _hm.new(
            b"k", prev + _j.dumps(body, sort_keys=True).encode(), _h.sha256).hexdigest()
        prev = _hm.new(b"k", prev + _j.dumps(body, sort_keys=True).encode(), _h.sha256).digest()
    path = _make_bundle(tmp_path, signer, rewritten, anchor)

    with pytest.raises(VerificationFailure) as exc:
        verify_bundle(path, tsa_cacert=tsa.ca_pem, out=io.StringIO())
    assert exc.value.check == 6
    assert "REWRITE DETECTED" in exc.value.message


def test_evidence_verify_reports_unanchored_bundle_honestly(tmp_path):
    # An unanchored bundle must NOT be reported as fully verified.
    import io
    from air_blackbox.gate.receipt import ReceiptSigner
    from air_blackbox.evidence_verify import verify_bundle
    signer = ReceiptSigner(private_key=os.urandom(32), hmac_key="k")
    recs = _bundle_records_with_seq(signer)
    path = _make_bundle(tmp_path, signer, recs, anchor_manifest=None)
    summary = verify_bundle(path, out=io.StringIO())
    assert summary["anchor"] == "absent"
