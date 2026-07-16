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
    from air_blackbox.mcp_server import _safe_tenant
    assert _safe_tenant("../etc/passwd") == "___etc_passwd"
    assert "/" not in _safe_tenant("a/b/c")
    assert _safe_tenant("normal-id_1") == "normal-id_1"


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
