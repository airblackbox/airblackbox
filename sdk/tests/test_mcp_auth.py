"""Tests for MCP OAuth token verification and tenant isolation."""

import os

import pytest

pytest.importorskip("mcp")

from air_blackbox.mcp_auth import (  # noqa: E402
    IntrospectionTokenVerifier,
    StaticTokenVerifier,
    build_auth,
)


async def _verify(verifier, token):
    return await verifier.verify_token(token)


def test_static_verifier_valid_token():
    import asyncio
    v = StaticTokenVerifier("secret123:recruiter-a:read|write")
    tok = asyncio.run(_verify(v, "secret123"))
    assert tok is not None
    assert tok.subject == "recruiter-a"
    assert tok.scopes == ["read", "write"]


def test_static_verifier_rejects_unknown():
    import asyncio
    v = StaticTokenVerifier("secret123:recruiter-a")
    assert asyncio.run(_verify(v, "wrong")) is None


def test_static_verifier_multiple_tenants():
    import asyncio
    v = StaticTokenVerifier("t1:alice,t2:bob")
    assert asyncio.run(_verify(v, "t1")).subject == "alice"
    assert asyncio.run(_verify(v, "t2")).subject == "bob"


def test_build_auth_disabled_without_env(monkeypatch):
    monkeypatch.delenv("AIR_MCP_INTROSPECTION_URL", raising=False)
    monkeypatch.delenv("AIR_MCP_TOKENS", raising=False)
    verifier, settings = build_auth()
    assert verifier is None and settings is None


def test_build_auth_static_mode(monkeypatch):
    monkeypatch.delenv("AIR_MCP_INTROSPECTION_URL", raising=False)
    monkeypatch.setenv("AIR_MCP_TOKENS", "k:tenant1")
    verifier, settings = build_auth()
    assert isinstance(verifier, StaticTokenVerifier)
    assert settings is not None


def test_build_auth_introspection_mode(monkeypatch):
    monkeypatch.setenv("AIR_MCP_INTROSPECTION_URL", "https://idp.example.com/introspect")
    verifier, settings = build_auth()
    assert isinstance(verifier, IntrospectionTokenVerifier)
    assert settings is not None


def test_tenant_id_is_filesystem_safe():
    import air_blackbox.mcp_server as srv
    assert srv._safe_tenant("../etc/passwd") == "___etc_passwd"
    assert "/" not in srv._safe_tenant("a/b/c")
    assert srv._safe_tenant("normal-id_1") == "normal-id_1"


def test_tenant_chains_are_isolated(tmp_path, monkeypatch):
    # Two tenants writing through the server land in separate runs dirs and
    # separate chains.
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    a = srv._tenant_chain("alice")
    b = srv._tenant_chain("bob")
    a.write({"run_id": "a1", "action": "read_profile",
             "timestamp": "2026-07-16T00:00:00Z"})
    b.write({"run_id": "b1", "action": "read_profile",
             "timestamp": "2026-07-16T00:00:00Z"})

    assert os.path.isfile(os.path.join(tmp_path, "alice", "a1.air.json"))
    assert os.path.isfile(os.path.join(tmp_path, "bob", "b1.air.json"))
    assert not os.path.isfile(os.path.join(tmp_path, "alice", "b1.air.json"))


# --- field-test regressions: covenant vocabulary + honest verification ---

def _load_recruiting_covenant(srv):
    from air_blackbox.gate.covenant import Covenant
    path = os.path.join(os.path.dirname(__file__), "..", "air_blackbox",
                        "gate", "examples", "recruiting-screener.covenant.yaml")
    return Covenant.from_yaml(path)


def test_check_covenant_distinguishes_no_rule_from_explicit(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", _load_recruiting_covenant(srv))

    # Free-text action name: vocabulary miss, not a policy judgment.
    out = srv.check_covenant("say good morning to the user")
    assert "no rule" in out
    assert "vocabulary" in out
    assert "read_profile" in out          # teaches the vocabulary

    # Explicit rule: reported as such.
    out = srv.check_covenant("infer_protected_attributes")
    assert "explicit rule" in out and "forbid" in out


def test_record_action_no_rule_message(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", _load_recruiting_covenant(srv))
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    out = srv.record_action("reviewed 3 candidate LinkedIn profiles")
    assert "NO RULE MATCHED" in out and "vocabulary miss" in out

    out = srv.record_action("infer_protected_attributes")
    assert "BLOCKED by covenant rule" in out


def test_verify_chain_partial_is_not_intact(tmp_path, monkeypatch):
    import json
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    srv.record_action("read_profile")
    # A stray unchained record lands in the same store.
    with open(os.path.join(tmp_path, "stray.air.json"), "w") as f:
        json.dump({"run_id": "stray", "timestamp": "2026-01-01T00:00:00Z"}, f)

    out = srv.verify_chain()
    assert "PARTIAL" in out and "CANNOT be verified" in out
    assert "INTACT" not in out


def test_chain_resumes_across_server_restarts(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))

    srv._chains.clear()
    srv.record_action("read_profile")
    srv.record_action("draft_message")

    # Simulate a Desktop restart: fresh chain objects over the same store.
    srv._chains.clear()
    srv.record_action("read_profile")

    out = srv.verify_chain()
    assert "CHAIN INTACT: all 3 records verified" in out


def test_export_warns_on_broken_chain(tmp_path, monkeypatch):
    import json, glob, zipfile
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    srv.record_action("read_profile")
    srv.record_action("draft_message")
    # Tamper with the first record.
    path = sorted(glob.glob(os.path.join(tmp_path, "*.air.json")))[0]
    with open(path) as f:
        rec = json.load(f)
    rec["action"] = "TAMPERED"
    with open(path, "w") as f:
        json.dump(rec, f)

    out = srv.export_evidence()
    assert "WARNING - BROKEN CHAIN EXPORTED" in out
    assert "NOT clean compliance evidence" in out

    # The signed payload itself carries the failure (v1 bundle: the
    # verify_chain result is stamped into verification/chain.json).
    zpath = glob.glob(os.path.join(tmp_path, "bundle-*.air-evidence"))[0]
    with zipfile.ZipFile(zpath) as z:
        chain_doc = json.loads(z.read("verification/chain.json"))
    verification = chain_doc["verification_at_export"]
    assert verification["fully_intact"] is False
    assert verification["intact"] is False


def test_export_clean_chain_reports_verified(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    srv.record_action("read_profile")
    out = srv.export_evidence()
    assert "chain fully verified at export time" in out
    assert "WARNING" not in out


def test_human_approval_flow_is_recordable(tmp_path, monkeypatch):
    # Field-test regression: a decision requires approval, and recording the
    # human's approval must be permitted (not a default-deny vocabulary miss).
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", _load_recruiting_covenant(srv))
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()

    gated = srv.log_screening_decision("Dana Okafor", "reject", "provenance only")
    assert "REQUIRES HUMAN APPROVAL" in gated

    approved = srv.record_action(
        "human_approval", detail="reject Dana approved by user", category="screening")
    assert approved.startswith("Recorded")           # not blocked
    assert "NO RULE" not in approved and "BLOCKED" not in approved

    assert "CHAIN INTACT: all 2 records verified" in srv.verify_chain()


def test_actions_carry_verifiable_ed25519_receipts(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear()
    srv._signers.clear()

    srv.record_action("read_profile", detail="candidate A")
    srv.record_action("draft_message", detail="hello")

    out = srv.verify_receipts()
    assert "ALL RECEIPTS VALID: 2/2" in out
    assert "ed25519" in out
    assert "Public key:" in out


def test_receipt_public_key_is_stable_across_restart(tmp_path, monkeypatch):
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear(); srv._signers.clear()

    srv.record_action("read_profile")
    pub1 = srv._tenant_signer("_local").public_key_hex

    # Simulate a restart: drop the in-memory signer, reload from the keyfile.
    srv._signers.clear()
    pub2 = srv._tenant_signer("_local").public_key_hex
    assert pub1 == pub2 and pub1


def test_tampered_receipt_is_caught(tmp_path, monkeypatch):
    import glob, json
    import air_blackbox.mcp_server as srv
    monkeypatch.setattr(srv, "_covenant", None)
    monkeypatch.setattr(srv, "RUNS_DIR", str(tmp_path))
    srv._chains.clear(); srv._signers.clear()

    srv.record_action("read_profile", detail="candidate A")
    # Forge the decision inside a stored receipt without re-signing.
    path = glob.glob(os.path.join(tmp_path, "*.air.json"))[0]
    with open(path) as f:
        rec = json.load(f)
    rec["receipt"]["decision"] = "permit"
    rec["receipt"]["action_name"] = "bulk_export"
    with open(path, "w") as f:
        json.dump(rec, f)

    out = srv.verify_receipts()
    assert "RECEIPT FAILURE" in out
