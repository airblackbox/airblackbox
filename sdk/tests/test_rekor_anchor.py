"""M2 public transparency-log anchoring, tested against an in-process fake
Rekor that implements the three endpoints the client uses, with the wire
format mirrored from the working Go client (pkg/trust/anchor.go).

The property under test is the M2 guarantee itself: a rewritten history -
even one freshly RE-ANCHORED to the log - is detected, because the original
entries cannot be removed from an append-only log. This is exactly the gap
the RFC 3161 anchor documents as its limit.
"""

import base64
import hashlib
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("cryptography")

from air_blackbox.anchor.head import compute_head
from air_blackbox.anchor.rekor import (
    RekorClient,
    anchor_head_to_rekor,
    audit_runs_against_log,
    decode_logged_payload,
    verify_bundle_anchor,
)
from air_blackbox.trust.chain import AuditChain

SECRET = "operator-held-key"


# ---------------------------------------------------------------------------
# Fake Rekor: append-only by construction, same API shapes as the real one.
# ---------------------------------------------------------------------------

class _FakeRekor(BaseHTTPRequestHandler):
    # Class-level shared log state (per-test reset via fresh server).
    entries = {}          # uuid -> stored entry fields
    by_key = {}           # pem content b64 -> [uuid]
    next_index = 0

    def log_message(self, *a):  # silence test noise
        pass

    def _json(self, code, doc, headers=None):
        body = json.dumps(doc).encode()
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.loads(self.rfile.read(
            int(self.headers.get("Content-Length", 0))).decode())
        cls = type(self)
        if self.path == "/api/v1/log/entries":
            canonical = json.dumps(body, sort_keys=True).encode()
            uuid = hashlib.sha256(canonical).hexdigest()
            if uuid in cls.entries:   # identical entry: 409 like real Rekor
                self._json(409, {}, {"Location": f"/api/v1/log/entries/{uuid}"})
                return
            fields = {
                "body": base64.b64encode(canonical_entry_body(body)).decode(),
                "logIndex": cls.next_index,
                "integratedTime": 1780000000 + cls.next_index,
            }
            cls.next_index += 1
            cls.entries[uuid] = fields
            key_content = body["spec"]["signature"]["publicKey"]["content"]
            cls.by_key.setdefault(key_content, []).append(uuid)
            self._json(201, {uuid: fields})
        elif self.path == "/api/v1/index/retrieve":
            key_content = body["publicKey"]["content"]
            self._json(200, cls.by_key.get(key_content, []))
        else:
            self._json(404, {"error": "no such endpoint"})

    def do_GET(self):
        cls = type(self)
        if self.path.startswith("/api/v1/log/entries/"):
            uuid = self.path.rsplit("/", 1)[-1]
            if uuid in cls.entries:
                self._json(200, {uuid: cls.entries[uuid]})
            else:
                self._json(404, {"error": "not found"})
        else:
            self._json(404, {"error": "no such endpoint"})


def canonical_entry_body(posted: dict) -> bytes:
    """Real Rekor stores the entry body (kind/apiVersion/spec) it accepted."""
    return json.dumps(posted, sort_keys=True).encode()


@pytest.fixture()
def rekor():
    # Fresh log per test.
    _FakeRekor.entries = {}
    _FakeRekor.by_key = {}
    _FakeRekor.next_index = 0
    server = HTTPServer(("127.0.0.1", 0), _FakeRekor)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield RekorClient(f"http://127.0.0.1:{server.server_port}", timeout=10)
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# Helpers: a genuine chain, and a rewritten one.
# ---------------------------------------------------------------------------

def _write_chain(runs, records, resume=False):
    chain = AuditChain(runs_dir=runs, signing_key=SECRET, resume=resume)
    for r in records:
        chain.write(dict(r))


def _genuine(n=4, start=0):
    return [{"run_id": f"run-{i:03d}", "action": "screen_candidate",
             "candidate": f"cand-{i}"} for i in range(start, start + n)]


def _seq_max(runs):
    import glob
    seqs = []
    for p in glob.glob(os.path.join(runs, "*.air.json")):
        seqs.append(json.load(open(p)).get("chain_seq") or 0)
    return max(seqs)


# ---------------------------------------------------------------------------
# Publish + fetch round trip.
# ---------------------------------------------------------------------------

def test_anchor_publish_fetch_roundtrip(tmp_path, rekor):
    runs = str(tmp_path / "runs")
    _write_chain(runs, _genuine())
    head, seq = compute_head(runs), _seq_max(runs)
    seed = os.urandom(32)

    anchor = anchor_head_to_rekor(head, seq, seed, client=rekor)
    assert anchor.uuid and anchor.log_index >= 0

    payload = decode_logged_payload(rekor.fetch_entry(anchor.uuid))
    assert payload["chain_head"] == head
    assert payload["chain_seq_max"] == seq

    # Idempotent republish reports already_existed, like real Rekor's 409.
    again = anchor_head_to_rekor(head, seq, seed, client=rekor)
    # (a second anchor of the same head signs a fresh timestamp, so it is a
    # new entry; only a byte-identical entry 409s. Both are fine - the log
    # keeps everything.)
    assert again.uuid


def test_embedded_anchor_offline_verification(tmp_path, rekor):
    runs = str(tmp_path / "runs")
    _write_chain(runs, _genuine())
    head, seq = compute_head(runs), _seq_max(runs)
    anchor = anchor_head_to_rekor(head, seq, os.urandom(32), client=rekor)

    ok, detail = verify_bundle_anchor({seq: head}, anchor.to_dict())
    assert ok, detail

    # A rewritten runs dir recomputes a different head at the same bound.
    ok, detail = verify_bundle_anchor({seq: "0" * 64}, anchor.to_dict())
    assert not ok and "REWRITE DETECTED" in detail

    # A forged receipt (signature does not match payload) is rejected.
    d = anchor.to_dict()
    d["payload_b64"] = base64.b64encode(json.dumps({
        "format": "air-chain-anchor-v1", "chain_head": "0" * 64,
        "chain_seq_max": seq, "anchored_at": "2026-01-01T00:00:00Z",
    }, sort_keys=True, separators=(",", ":")).encode()).decode()
    ok, detail = verify_bundle_anchor({seq: "0" * 64}, d)
    assert not ok and "INVALID" in detail


# ---------------------------------------------------------------------------
# THE M2 test: a re-anchored rewrite is still detected.
# ---------------------------------------------------------------------------

def test_reanchored_rewrite_is_detected_by_log_audit(tmp_path, rekor):
    """The attack the RFC 3161 anchor cannot catch: rewrite history AND
    obtain a fresh anchor for the new head. The log audit still catches it,
    because the ORIGINAL anchor is still in the append-only log and the
    rewritten history cannot reproduce its bounded head."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    runs = str(tmp_path / "runs")
    _write_chain(runs, _genuine())
    seed = os.urandom(32)
    pub_raw = Ed25519PrivateKey.from_private_bytes(seed).public_key() \
        .public_bytes(serialization.Encoding.Raw,
                      serialization.PublicFormat.Raw)

    # Month 1: the genuine history is anchored.
    anchor_head_to_rekor(compute_head(runs), _seq_max(runs), seed,
                         client=rekor)

    # Month 6: the operator rewrites the ENTIRE history (cleanly re-signed
    # with the operator-held key) and - crucially - RE-ANCHORS the new head.
    rewritten = [{"run_id": f"run-{i:03d}", "action": "screen_candidate",
                  "candidate": "COVER-UP"} for i in range(4)]
    runs2 = str(tmp_path / "runs_rewritten")
    _write_chain(runs2, rewritten)
    anchor_head_to_rekor(compute_head(runs2), _seq_max(runs2), seed,
                         client=rekor)

    # The audit walks EVERY entry under the anchoring key.
    audit = audit_runs_against_log(runs2, pub_raw, rekor)
    assert audit.anchors_checked == 2
    assert audit.rewrite_detected          # the old entry gives it away
    assert len(audit.mismatches) == 1
    assert audit.mismatches[0]["logged_head"] != compute_head(runs2)

    # And the genuine history still audits clean against both its anchors.
    genuine_audit = audit_runs_against_log(runs, pub_raw, rekor)
    # (one anchor matches; the attacker's re-anchor of the fake head does
    # not match the genuine records either - an honest auditor sees exactly
    # one consistent lineage only when there is exactly one history)
    assert genuine_audit.anchors_checked == 2
    assert genuine_audit.consistent == 1


# ---------------------------------------------------------------------------
# MCP integration: export publishes the anchor; the tool audits the log.
# ---------------------------------------------------------------------------

def _fresh_srv(tmp_path, monkeypatch, rekor):
    srv = pytest.importorskip("air_blackbox.mcp_server")
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("AIR_REKOR_SERVER", rekor.server)
    # Point the TSA rail at a port that refuses instantly: the test then also
    # proves the rails fail independently (TSA gap does not block the log
    # anchor).
    monkeypatch.setenv("AIR_TSA_URLS", "http://127.0.0.1:9/tsr")
    srv._chains.clear()
    srv._signers.clear()
    return srv


def test_export_publishes_to_log_and_bundle_verifies(tmp_path, monkeypatch,
                                                     rekor):
    import glob as _glob
    import io

    from air_blackbox.evidence_verify import verify_bundle

    srv = _fresh_srv(tmp_path, monkeypatch, rekor)
    srv.record_action("read_profile", detail="candidate A")
    srv.record_action("draft_message", detail="hello")

    note, manifest = srv._anchor_current_head("_local")
    assert "Public log: entry" in note
    assert manifest["rekor"]["uuid"]

    out = srv.export_evidence()
    bundles = _glob.glob(str(tmp_path / "**" / "*.air-evidence"),
                         recursive=True)
    assert bundles, out
    buf = io.StringIO()
    summary = verify_bundle(bundles[0], out=buf)
    assert "Public-log anchor" in buf.getvalue()
    assert "public-log" in summary["anchor"]

    tool_out = srv.audit_public_log()
    assert "PUBLIC LOG CONSISTENT" in tool_out


def test_audit_tool_catches_rewrite_after_anchoring(tmp_path, monkeypatch,
                                                    rekor):
    import glob as _glob

    srv = _fresh_srv(tmp_path, monkeypatch, rekor)
    srv.record_action("reject_candidate", detail="no streaming experience")
    srv._anchor_current_head("_local")

    # The operator rewrites the record and re-signs the chain from scratch,
    # then even RE-ANCHORS the rewritten head. The old log entry remains.
    rec_path = _glob.glob(str(tmp_path / "**" / "*.air.json"),
                          recursive=True)[0]
    rec = json.load(open(rec_path))
    runs = os.path.dirname(rec_path)
    os.remove(rec_path)
    rec["detail"] = "APPROVED ON MERIT"
    _write_chain(runs, [{k: rec[k] for k in ("run_id", "action", "detail")}])
    srv._chains.clear()
    srv._anchor_current_head("_local")     # the fresh re-anchor

    out = srv.audit_public_log()
    assert "REWRITE DETECTED" in out


def test_audit_tool_reports_disabled_when_off(tmp_path, monkeypatch, rekor):
    srv = _fresh_srv(tmp_path, monkeypatch, rekor)
    monkeypatch.delenv("AIR_REKOR_SERVER")
    monkeypatch.delenv("AIR_REKOR", raising=False)
    assert "not enabled" in srv.audit_public_log()


def test_untampered_history_audits_clean(tmp_path, rekor):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    runs = str(tmp_path / "runs")
    seed = os.urandom(32)
    pub_raw = Ed25519PrivateKey.from_private_bytes(seed).public_key() \
        .public_bytes(serialization.Encoding.Raw,
                      serialization.PublicFormat.Raw)

    # Anchor at two points as the chain grows - like monthly exports.
    _write_chain(runs, _genuine(2))
    anchor_head_to_rekor(compute_head(runs), _seq_max(runs), seed,
                         client=rekor)
    _write_chain(runs, _genuine(2, start=2), resume=True)   # append two more
    anchor_head_to_rekor(compute_head(runs), _seq_max(runs), seed,
                         client=rekor)

    audit = audit_runs_against_log(runs, pub_raw, rekor)
    assert audit.anchors_checked == 2
    assert audit.consistent == 2
    assert not audit.rewrite_detected
