"""Tests for the session passport (accountable browser-agent activity)."""

import os

from air_blackbox.passport import BrowserSession

COVENANT = os.path.join(
    os.path.dirname(__file__), "..", "air_blackbox", "gate", "examples",
    "linkedin-sourcing.covenant.yaml")


def _session(tmp_path, key="passport-key"):
    return BrowserSession(runs_dir=str(tmp_path), covenant=COVENANT,
                          signing_key=key)


def test_permitted_actions_allowed(tmp_path):
    with _session(tmp_path) as s:
        d = s.action("read_profile", target="https://linkedin.com/in/alice")
        assert d.allowed and not d.needs_approval
        assert d.decision == "permit"


def test_sensitive_action_needs_approval(tmp_path):
    with _session(tmp_path) as s:
        d = s.action("send_message", target="https://linkedin.com/in/alice")
        assert d.needs_approval and not d.allowed
        s.approve(d)
        assert d.allowed


def test_forbidden_action_blocked(tmp_path):
    with _session(tmp_path) as s:
        d = s.action("scrape_search_page")
        assert d.blocked and not d.allowed


def test_clean_session_passport(tmp_path):
    with _session(tmp_path) as s:
        for i in range(5):
            assert s.action("read_profile", target=f"/in/c{i}").allowed
        d = s.action("send_message", target="/in/c0")
        s.approve(d)
    p = s.passport()
    assert p.verdict == "CLEAN"
    assert p.chain_intact
    assert p.action_counts["read_profile"] == 5
    assert p.approvals == 1
    assert p.total_actions == 6
    assert not p.violations


def test_unapproved_sensitive_action_is_a_violation(tmp_path):
    with _session(tmp_path) as s:
        s.action("read_profile", target="/in/a")
        s.action("send_message", target="/in/a")   # never approved
    p = s.passport()
    assert p.verdict == "VIOLATIONS"
    assert any("unapproved" in v for v in p.violations)


def test_blocked_action_is_a_violation(tmp_path):
    with _session(tmp_path) as s:
        s.action("harvest_emails")
    p = s.passport()
    assert p.verdict == "VIOLATIONS"
    assert p.blocked == 1
    assert any("blocked" in v for v in p.violations)


def test_passport_export_produces_bundle(tmp_path):
    with _session(tmp_path) as s:
        d = s.action("send_message", target="/in/a")
        s.approve(d)
    path = s.export_passport()
    assert path and os.path.exists(path)


def test_chain_survives_and_verifies(tmp_path):
    with _session(tmp_path) as s:
        for i in range(3):
            s.action("navigate", target=f"/page/{i}")
    p = s.passport()
    # Every action recorded is chained and verifies with the session key.
    assert p.chain_intact
    assert p.chain_verified == 3
