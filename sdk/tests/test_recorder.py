"""The zero-infrastructure path: record -> export -> verify, with no server.

Anchoring is stubbed throughout so the suite never touches the network.
"""

import json
import os

import pytest

import air_blackbox as air
from air_blackbox.evidence_verify import verify_bundle
from air_blackbox.gate.covenant import Covenant, Rule, RuleAction


@pytest.fixture(autouse=True)
def _no_network_anchor(monkeypatch):
    import air_blackbox.anchor as anchor

    class _Gap:
        ok = False
        error = "stubbed: no network in tests"

    monkeypatch.setattr(anchor, "timestamp_head", lambda *a, **k: _Gap())


def test_record_is_the_function_not_the_module():
    # Importing a submodule sets it as an attribute on the package, so a
    # module named like the function would replace air.record after first use.
    import air_blackbox.recorder  # noqa: F401  (force the submodule import)
    assert callable(air.record)


def test_round_trip_verifies(tmp_path):
    with air.record("support-agent", runs_dir=str(tmp_path)) as rec:
        rec.action("read_ticket", "ticket #4821")
        rec.action("issue_refund", "order 991, $40",
                   human_reviewer="dana@acme.example", decision_type="refund")

    assert rec.bundle_path and os.path.exists(rec.bundle_path)
    result = verify_bundle(rec.bundle_path)
    assert result["records"] == 2
    assert result["alterations"] == 0
    assert result["receipts_checked"] == 2
    assert result["fingerprint"].startswith("ed25519:")


def test_second_run_keeps_identity_and_continues_the_chain(tmp_path):
    with air.record("a", runs_dir=str(tmp_path)) as first:
        first.action("step_one", "")
    with air.record("a", runs_dir=str(tmp_path)) as second:
        second.action("step_two", "")

    r1 = verify_bundle(first.bundle_path)
    r2 = verify_bundle(second.bundle_path)
    assert r1["fingerprint"] == r2["fingerprint"]
    assert r2["records"] == 2 and r2["alterations"] == 0


def test_unreadable_key_is_refused_not_overwritten(tmp_path):
    key = tmp_path / ".air-receipt-key"
    key.write_text("not a key")
    with pytest.raises(RuntimeError):
        air.Recorder("a", runs_dir=str(tmp_path))
    assert key.read_text() == "not a key"


def test_key_file_is_private(tmp_path):
    air.Recorder("a", runs_dir=str(tmp_path))
    mode = os.stat(tmp_path / ".air-receipt-key").st_mode & 0o777
    assert mode == 0o600


def test_covenant_decisions_are_recorded_and_returned(tmp_path):
    cov = Covenant(agent="support", rules=[
        Rule(action=RuleAction.PERMIT, target="read_ticket"),
        Rule(action=RuleAction.REQUIRE_APPROVAL, target="issue_refund"),
    ])
    with air.record("support", runs_dir=str(tmp_path), covenant=cov) as rec:
        read = rec.action("read_ticket", "t1")
        refund = rec.action("issue_refund", "t1")
        unknown = rec.action("delete_database", "t1")

    assert read.allowed and read.decision == "permit"
    assert not refund.allowed and refund.decision == "require_approval"
    assert not unknown.allowed and unknown.decision == "forbid"   # default-deny

    result = verify_bundle(rec.bundle_path)
    assert result["counts"]["blocked_actions"] == 1
    assert result["alterations"] == 0


def test_failed_anchor_is_a_recorded_gap_not_a_crash(tmp_path):
    with air.record("a", runs_dir=str(tmp_path)) as rec:
        rec.action("step", "")
    assert "stubbed" in rec.last_export_note
    manifest = _manifest(rec.bundle_path)
    assert manifest["anchor"]["anchored"] is False
    assert "stubbed" in manifest["anchor"]["error"]
    assert verify_bundle(rec.bundle_path)["alterations"] == 0


def test_exception_still_writes_evidence_and_still_raises(tmp_path):
    with pytest.raises(RuntimeError, match="agent crashed"):
        with air.record("a", runs_dir=str(tmp_path)) as rec:
            rec.action("start_job", "nightly sync")
            raise RuntimeError("agent crashed")
    assert rec.bundle_path and os.path.exists(rec.bundle_path)


def test_nothing_recorded_writes_nothing(tmp_path):
    with air.record("a", runs_dir=str(tmp_path)) as rec:
        pass
    assert rec.bundle_path is None


def _manifest(bundle_path):
    import zipfile
    with zipfile.ZipFile(bundle_path) as z:
        return json.loads(z.read("manifest.json"))
