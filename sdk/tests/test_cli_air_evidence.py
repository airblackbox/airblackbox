"""`air-blackbox export --format air-evidence`: the CLI can produce the format
a third party can actually check.

Before this, generate_evidence_bundle_v1 had exactly one caller - the MCP
server. Everything the CLI produced needed the operator's signing key to
verify, so the only bundle you could hand to someone who does not trust you
was reachable only by running a chat connector. The pitch is "hand this to
your auditor"; the CLI could not produce the thing being handed over.

Anchoring defaults ON here for the same reason it does in the module: the
external timestamp is the only property in the format an operator cannot
forge for themselves, so leaving it opt-in made the load-bearing part
optional.
"""

import io
import json
import os
import zipfile

import pytest

pytest.importorskip("cryptography")

from air_blackbox.anchor.tsa import AnchorResult
from air_blackbox.evidence_verify import VerificationFailure, verify_bundle
from air_blackbox.export.air_evidence import (
    export_air_evidence,
    signer_fingerprint,
    signer_for,
)
from air_blackbox.trust.chain import AuditChain

HMAC_KEY = "cli-test-signing-key"


@pytest.fixture()
def runs(tmp_path, monkeypatch):
    """A runs directory as the gateway or a trust layer would leave it.

    monkeypatch, not os.environ: setting TRUST_SIGNING_KEY directly leaked
    into every test that ran afterwards and broke the sandbox suite.
    """
    monkeypatch.setenv("TRUST_SIGNING_KEY", HMAC_KEY)
    d = tmp_path / "runs"
    chain = AuditChain(runs_dir=str(d), signing_key=HMAC_KEY)
    for i, (action, detail) in enumerate([
            ("read_profile", "candidate profile read"),
            ("score_candidate", "candidate=Bo; decision=score"),
            ("reject_candidate", "candidate=Ada; decision=reject")]):
        chain.write({"run_id": f"r{i}", "timestamp": "2026-08-09T20:00:00Z",
                     "type": "agent_action", "action": action,
                     "detail": detail, "model": "", "status": "success",
                     "tokens": {"total": 0}})
    return str(d)


def _local_tsa(monkeypatch, tsa):
    def fake(head_hex, tsa_urls=None, **kw):
        return AnchorResult(ok=True, head=head_hex, tsr=tsa.reply(head_hex),
                            tsa_url="local-test-tsa", timestamp="T0")
    monkeypatch.setattr("air_blackbox.anchor.timestamp_head", fake)


def test_cli_export_produces_a_bundle_the_verifier_accepts(runs, tmp_path):
    """The whole point: no secret changes hands, and it verifies."""
    result = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    assert result.path.endswith(".air-evidence")
    assert result.records == 3

    summary = verify_bundle(result.path, out=io.StringIO())
    assert summary["records"] == 3
    assert summary["alterations"] == 0


def test_the_fingerprint_printed_at_export_is_the_one_the_verifier_pins(runs,
                                                                       tmp_path):
    """--expect-key is useless if the issuer cannot learn their own value.

    The export prints a fingerprint for the operator to publish; if it did not
    match what the verifier computes, every pinned verification would fail.
    """
    result = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    summary = verify_bundle(result.path, expect_key=result.fingerprint,
                            out=io.StringIO())
    assert summary["signer_pinned"] is True
    assert summary["fingerprint"] == result.fingerprint


def test_export_anchors_by_default(runs, tmp_path, monkeypatch):
    import subprocess
    if subprocess.run(["which", "openssl"], capture_output=True).returncode:
        pytest.skip("openssl not available")
    from test_anchor import LocalTSA

    tsa = LocalTSA(str(tmp_path / "tsa"))
    _local_tsa(monkeypatch, tsa)

    result = export_air_evidence(runs, output_dir=str(tmp_path))
    assert result.anchored, result.anchor_note
    assert "head bound to" in result.anchor_note

    summary = verify_bundle(result.path, tsa_cacert=tsa.ca_pem,
                            out=io.StringIO())
    assert summary["anchor"] == "verified"


def test_no_anchor_is_opt_out_and_says_what_was_given_up(runs, tmp_path):
    result = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    assert not result.anchored
    assert "SKIPPED by request" in result.anchor_note
    summary = verify_bundle(result.path, out=io.StringIO())
    assert summary["anchor"] == "absent"


def test_an_unreachable_authority_is_a_recorded_gap_not_a_failed_export(
        runs, tmp_path, monkeypatch):
    """Refusing to export offline would just teach people to pass --no-anchor.

    The gap goes into the signed manifest and into anchors/gaps.log, so an
    auditor sees that no witness was obtained that day.
    """
    def unreachable(head_hex, tsa_urls=None, **kw):
        return AnchorResult(ok=False, head=head_hex, tsr=b"",
                            error="connection refused")
    monkeypatch.setattr("air_blackbox.anchor.timestamp_head", unreachable)

    result = export_air_evidence(runs, output_dir=str(tmp_path))
    assert not result.anchored
    assert "GAP" in result.anchor_note
    with zipfile.ZipFile(result.path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    assert manifest["anchor"]["anchored"] is False
    assert "connection refused" in manifest["anchor"]["error"]
    with open(os.path.join(runs, "anchors", "gaps.log")) as f:
        assert "connection refused" in f.read()


def test_empty_runs_dir_refuses_rather_than_evidencing_nothing(tmp_path):
    with pytest.raises(ValueError, match="nothing to evidence"):
        export_air_evidence(str(tmp_path / "empty"), output_dir=str(tmp_path))


def test_signing_identity_is_stable_across_exports(runs, tmp_path):
    """The fingerprint an auditor pins must not change between exports."""
    first = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    second = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    assert first.fingerprint == second.fingerprint
    assert signer_fingerprint(signer_for(runs)) == first.fingerprint


def test_a_broken_chain_is_reported_not_hidden(runs, tmp_path):
    """A bundle must never quietly attest a chain that does not verify."""
    import glob
    victim = sorted(glob.glob(os.path.join(runs, "*.air.json")))[1]
    with open(victim) as f:
        rec = json.load(f)
    rec["detail"] = "candidate=Bo; decision=advance"     # pre-export tamper
    with open(victim, "w") as f:
        json.dump(rec, f)

    result = export_air_evidence(runs, output_dir=str(tmp_path), anchor=False)
    with zipfile.ZipFile(result.path) as zf:
        chain_doc = json.loads(zf.read("verification/chain.json"))
    assert chain_doc["verification_at_export"]["fully_intact"] is False
    assert any("NOT fully intact" in n for n in result.notes)

    # And the verifier refuses it rather than passing a bundle that admits,
    # in its own signed payload, that the chain did not verify at export.
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(result.path, out=io.StringIO())
    assert "NOT intact at export time" in e.value.message
