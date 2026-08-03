"""Monitoring layer: the health probe must tell the truth (ok only when
evidence can actually be recorded), auth rejections must be diagnosable from
logs without ever logging the token, and error tracking must be a strict
no-op unless explicitly configured.
"""

import asyncio
import logging
import os

import pytest


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("AIR_RUNS_DIR", str(tmp_path / "runs"))
    from air_blackbox import mcp_server as m
    monkeypatch.setattr(m, "RUNS_DIR", str(tmp_path / "runs"))
    return m


def test_health_ok_when_volume_writable(server):
    resp = asyncio.run(server._health(None))
    assert resp.status_code == 200
    assert b'"ok"' in resp.body


def test_health_degraded_when_volume_not_writable(server, tmp_path, monkeypatch):
    # A file where the runs DIRECTORY should be: makedirs fails with an
    # OSError subclass, exactly like a full/unmounted/read-only volume.
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    monkeypatch.setattr(server, "RUNS_DIR", str(blocker / "runs"))
    resp = asyncio.run(server._health(None))
    assert resp.status_code == 503
    assert b"degraded" in resp.body
    # Never leak filesystem paths to an unauthenticated endpoint.
    assert str(blocker).encode() not in resp.body


def test_jwt_rejection_reason_is_logged_but_token_is_not(caplog):
    pytest.importorskip("jwt")
    from air_blackbox.mcp_auth import JwtTokenVerifier
    v = JwtTokenVerifier("http://127.0.0.1:9/jwks.json",
                        issuer="https://idp.example", audience="https://api")
    secret_token = "eyJhbGciOiJub25lIn0.SECRET-PAYLOAD.sig"
    with caplog.at_level(logging.INFO, logger="air_blackbox.mcp_auth"):
        assert asyncio.run(v.verify_token(secret_token)) is None
    assert any("token rejected" in r.message for r in caplog.records)
    assert all("SECRET-PAYLOAD" not in r.getMessage() for r in caplog.records)


def test_error_tracking_noop_without_dsn(server, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert server._init_error_tracking() is None   # no crash, no import


def test_error_tracking_missing_sdk_warns_but_does_not_crash(
        server, monkeypatch, caplog):
    monkeypatch.setenv("SENTRY_DSN", "https://x@example.ingest.sentry.io/1")
    import builtins
    real_import = builtins.__import__

    def _no_sentry(name, *a, **kw):
        if name == "sentry_sdk":
            raise ImportError("sentry_sdk unavailable")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _no_sentry)
    with caplog.at_level(logging.WARNING, logger="air_blackbox.mcp"):
        server._init_error_tracking()
    assert any("sentry-sdk is not installed" in r.message
               for r in caplog.records)
