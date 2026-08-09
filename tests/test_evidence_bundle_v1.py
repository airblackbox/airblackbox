"""Evidence Bundle v1: generation, signing, and independent verification.

Covers the six verifier checks plus tamper detection: a bundle must verify
clean end-to-end, and any post-signing alteration (records, manifest, or a
receipt) must fail loudly with the offending record identified.
"""

import hashlib
import hmac as hmac_mod
import io
import json
import os
import zipfile

import pytest

from air_blackbox.evidence_verify import (
    VerificationFailure,
    main as verify_main,
    verify_bundle,
)
from air_blackbox.export.evidence_bundle import (
    canonical_manifest_bytes,
    categorize_record,
    generate_evidence_bundle_v1,
)
from air_blackbox.gate.receipt import ActionReceipt, ReceiptSigner, hash_payload

HMAC_KEY = "test-signing-key"


@pytest.fixture()
def signer():
    return ReceiptSigner(private_key=os.urandom(32), hmac_key=HMAC_KEY)


def _record(signer, action, detail="", status="success",
            decision="permit", screening=None):
    receipt = ActionReceipt(
        agent_id="test-tenant", action_name=action,
        action_category="screening" if screening is not None else "",
        payload_hash=hash_payload(detail) if detail else "",
        covenant_hash="cov-hash", decision=decision,
        authorized=(decision == "permit"))
    signer.sign_authorization(receipt)
    rec = {
        "run_id": f"run-{action}-{os.urandom(4).hex()}",
        "timestamp": "2026-07-18T12:00:00+00:00",
        "type": "agent_action",
        "action": action,
        "detail": detail,
        "model": "",
        "status": status,
        "covenant_decision": decision,
        "tokens": {"total": 0},
        "receipt": receipt.to_dict(),
    }
    if screening is not None:
        rec["screening"] = screening
    return rec


def _chain(records):
    """Apply the production HMAC chain over the records in order."""
    prev = b"genesis"
    for rec in records:
        body = {k: v for k, v in rec.items() if k != "chain_hash"}
        h = hmac_mod.new(HMAC_KEY.encode(),
                         prev + json.dumps(body, sort_keys=True).encode(),
                         hashlib.sha256)
        rec["chain_hash"] = h.hexdigest()
        prev = h.digest()
    return records


@pytest.fixture()
def records(signer):
    return _chain([
        _record(signer, "read_profile", "candidate profile read"),
        _record(signer, "reject_candidate",
                "candidate=Ada; decision=reject", decision="require_approval",
                screening={"decision_type": "reject",
                           "human_reviewer": "j.smith",
                           "review_action": "approved"}),
        _record(signer, "score_candidate", "candidate=Bo; decision=score",
                screening={"decision_type": "recommend"}),  # no reviewer: gap
        _record(signer, "human_approval",
                "reject_candidate for Ada, approved by user"),
        _record(signer, "infer_protected_attributes", "age guess attempt",
                status="blocked", decision="forbid"),
    ])


@pytest.fixture()
def bundle(tmp_path, records, signer):
    attach = tmp_path / "attachments"
    attach.mkdir()
    (attach / "impact-assessment.md").write_text("# Impact assessment\n")
    path, manifest = generate_evidence_bundle_v1(
        chain_entries=records,
        tenant="test-tenant",
        signer=signer,
        chain_verification={"fully_intact": True, "intact": True,
                            "verified_records": len(records)},
        system={"name": "Test screening agent", "deployer": "Test LLC",
                "high_risk_rationale": "employment decisions"},
        attachments_dir=str(attach),
        output_dir=str(tmp_path))
    return path, manifest


def test_categorize_record(records):
    cats = [categorize_record(r) for r in records]
    assert cats == ["agent_action", "screening_decision",
                    "screening_decision", "human_approval", "blocked_action"]


def test_manifest_shape_and_counts(bundle):
    _, manifest = bundle
    assert manifest["bundle_version"] == "1.0"
    # The fixture is the distinction in miniature: one reject reviewed by
    # j.smith, one engine score with nobody assigned. The coarse total says
    # "1 missing reviewer"; the split says the adverse decision was reviewed
    # and the unreviewed record is an engine output, which is not a gap.
    assert manifest["counts"] == {
        "actions": 5, "screening_decisions": 2, "blocked_actions": 1,
        "human_approvals": 1,
        "adverse_decisions": 1,
        "adverse_decisions_missing_reviewer": 0,
        "engine_outputs_without_reviewer": 1,
        "screening_decisions_missing_reviewer": 1}
    assert manifest["frameworks"] == ["CO-SB26-189"]
    assert manifest["outcome_monitoring"] == "deployer-supplied"
    assert manifest["system"]["deployer"] == "Test LLC"
    assert manifest["retention_until"] > manifest["created_at"][:10]
    assert "attachments/impact-assessment.md" in manifest["files"]
    sig = manifest["signature"]
    assert sig["alg"] == "ed25519"
    assert sig["upgrade_path"] == "ML-DSA-65"
    digest = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    assert digest == sig["signed_digest"]


def test_clean_bundle_verifies(bundle, capsys):
    path, _ = bundle
    summary = verify_bundle(path, hmac_key=HMAC_KEY, out=io.StringIO())
    assert summary["records"] == 5
    assert summary["alterations"] == 0
    assert summary["fingerprint"].startswith("ed25519:")
    # CLI end-to-end, no secret
    assert verify_main(["verify", path]) == 0
    out = capsys.readouterr().out
    # Unanchored fixture bundle: verified but reported honestly as not
    # rewrite-protected, never a bare over-confident "VERIFIED".
    assert "VERIFIED" in out and "5 records, 0 alterations" in out
    assert "ed25519:" in out
    assert "NOT anchored" in out
    assert summary["anchor"] == "absent"


def _rewrite_member(path, member, new_bytes):
    """Rewrite one member of the ZIP in place (rebuild, preserving others)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, \
            zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            zout.writestr(item, new_bytes if item == member
                          else zin.read(item))
    with open(path, "wb") as f:
        f.write(buf.getvalue())


def test_tampered_record_fails_file_digest(bundle):
    path, _ = bundle
    with zipfile.ZipFile(path) as zf:
        lines = zf.read("records/actions.jsonl").decode().splitlines()
    rec = json.loads(lines[2])
    rec["detail"] = "candidate=Bo; decision=advance"  # attacker edit
    lines[2] = json.dumps(rec, sort_keys=True)
    _rewrite_member(path, "records/actions.jsonl", "\n".join(lines) + "\n")
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 2
    assert "records/actions.jsonl" in e.value.message


def test_tampered_manifest_fails_signature(bundle):
    path, _ = bundle
    with zipfile.ZipFile(path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    manifest["counts"]["blocked_actions"] = 0  # hide the block
    _rewrite_member(path, "manifest.json", json.dumps(manifest, indent=2))
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 2
    assert "digest mismatch" in e.value.message


def test_resigned_manifest_count_lie_fails_check5(bundle, signer):
    """Even an attacker WITH the manifest-signing ability can't lie about
    counts: check 5 recomputes them from the records."""
    path, _ = bundle
    with zipfile.ZipFile(path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    manifest["counts"]["blocked_actions"] = 0
    digest = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    manifest["signature"]["signed_digest"] = digest
    manifest["signature"]["value"] = signer.sign(bytes.fromhex(digest))
    _rewrite_member(path, "manifest.json", json.dumps(manifest, indent=2))
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 5
    assert "blocked_actions" in e.value.message


def test_invalid_receipt_fails_check4(tmp_path, signer, records):
    records[1]["receipt"]["authorization_sig"] = "00" * 64  # forged
    path, _ = generate_evidence_bundle_v1(
        chain_entries=_chain(records), tenant="test-tenant", signer=signer,
        chain_verification={"fully_intact": True},
        output_dir=str(tmp_path))
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 4
    assert records[1]["run_id"] in e.value.message


def test_chain_recompute_catches_pre_export_alteration(tmp_path, signer,
                                                       records):
    """A record altered after chaining but before export: file digests and
    receipts still pass (the bundle faithfully packages what it was given),
    but the --key HMAC recompute exposes the break."""
    records[0]["detail"] = "altered after chaining"
    path, _ = generate_evidence_bundle_v1(
        chain_entries=records, tenant="test-tenant", signer=signer,
        chain_verification={"fully_intact": False},
        output_dir=str(tmp_path))
    # Without the key: structural checks pass, receipt of record 0 still
    # verifies (payload_hash is inside the receipt, not re-derived).
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, hmac_key=HMAC_KEY, out=io.StringIO())
    assert e.value.check == 3
    assert records[0]["run_id"] in e.value.message


def test_missing_required_file_fails_check1(bundle):
    path, _ = bundle
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, \
            zipfile.ZipFile(buf, "w") as zout:
        for item in zin.namelist():
            if item != "verification/receipts.json":
                zout.writestr(item, zin.read(item))
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 1
    assert "receipts.json" in e.value.message


def test_unlisted_member_added_after_signing_fails_check2(bundle):
    """A file the manifest does not list is covered by nothing.

    The per-file digest loop only proves the LISTED files are unaltered, so
    before this check an attacker could drop a forged document into a validly
    signed bundle and all six checks still passed clean - 0 alterations, valid
    signature, the lot. The forged file is the interesting one precisely
    because it is the kind an auditor would read: an impact assessment nobody
    approved.
    """
    path, manifest = bundle
    forged = "attachments/human-review-signoff.md"
    assert forged not in manifest["files"], "fixture already lists this name"
    with zipfile.ZipFile(path, "a") as zf:
        zf.writestr(forged, "# Human review sign-off\nApproved by nobody.\n")
    with pytest.raises(VerificationFailure) as e:
        verify_bundle(path, out=io.StringIO())
    assert e.value.check == 2
    assert forged in e.value.message
    assert "does not list" in e.value.message


def test_legitimate_attachment_is_listed_and_verifies(tmp_path, signer,
                                                      records):
    """The guard must not reject attachments the generator itself signs."""
    attach = tmp_path / "attachments"
    attach.mkdir()
    (attach / "dpia.md").write_text("# DPIA\n")
    path, manifest = generate_evidence_bundle_v1(
        chain_entries=records, tenant="t", signer=signer,
        chain_verification={"fully_intact": True, "intact": True,
                            "verified_records": len(records)},
        attachments_dir=str(attach), output_dir=str(tmp_path))
    assert "attachments/dpia.md" in manifest["files"]
    summary = verify_bundle(path, out=io.StringIO())
    assert summary["alterations"] == 0


# ---- adverse vs engine reviewer gaps --------------------------------------
# Production data made this concrete: 14 of 53 screening records had no
# human_reviewer, and the coarse count invited "fixing" it by naming the
# search-runner as the reviewer of engine scores nobody reviewed. That would
# have fabricated human oversight inside the format that exists to evidence it.

def _screening(action, reviewer="", decision_type=""):
    return {"run_id": f"r-{action}-{reviewer}-{decision_type}",
            "action": action, "status": "success",
            "timestamp": "2026-08-07T00:00:00Z",
            "screening": {"human_reviewer": reviewer,
                          "decision_type": decision_type}}


def test_adverse_and_engine_reviewer_gaps_are_counted_separately(signer,
                                                                 tmp_path):
    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    records = [
        _screening("reject_candidate", reviewer="u-abc"),   # reviewed: fine
        _screening("reject_candidate"),                     # THE gap
        _screening("reject_candidate"),                     # THE gap
        _screening("score_candidate"),                      # engine: not a gap
        _screening("score_candidate"),                      # engine: not a gap
        _screening("rank_candidates"),                      # engine: not a gap
    ]
    _, manifest = generate_evidence_bundle_v1(
        records, "t", signer, {"intact": True, "verified_records": len(records)},
        output_dir=str(tmp_path))
    c = manifest["counts"]
    assert c["adverse_decisions"] == 3
    assert c["adverse_decisions_missing_reviewer"] == 2
    assert c["engine_outputs_without_reviewer"] == 3
    # The coarse total keeps its old meaning for readers of older bundles.
    assert c["screening_decisions_missing_reviewer"] == 5


def test_decision_type_reject_counts_as_adverse_whatever_the_action_name(
        signer, tmp_path):
    """Callers name actions in their own vocabulary; a reject is a reject."""
    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    records = [_screening("filter_candidate", decision_type="reject")]
    _, manifest = generate_evidence_bundle_v1(
        records, "t", signer, {"intact": True, "verified_records": 1},
        output_dir=str(tmp_path))
    assert manifest["counts"]["adverse_decisions_missing_reviewer"] == 1


def test_engine_scores_alone_report_no_adverse_gap(signer, tmp_path):
    """A day of pure scoring must not read as a compliance problem."""
    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    _, manifest = generate_evidence_bundle_v1(
        [_screening("score_candidate") for _ in range(20)], "t", signer,
        {"intact": True, "verified_records": 20}, output_dir=str(tmp_path))
    assert manifest["counts"]["adverse_decisions_missing_reviewer"] == 0
    assert manifest["counts"]["engine_outputs_without_reviewer"] == 20
