"""Bundles that are malformed rather than tampered: each must fail cleanly.

A tamper test of bundles written by the TypeScript package found a few the
verifier accepted or crashed on. Every case here is built from a genuine
bundle, and each test failed before the check it covers existed.
"""

import io
import json
import sys
import zipfile

import pytest

pytest.importorskip("cryptography")

from air_blackbox.evidence_verify import VerificationFailure, _loads, verify_bundle
from air_blackbox.export.air_evidence import export_air_evidence
from air_blackbox.trust.chain import AuditChain

HMAC_KEY = "malformed-test-key"


def _runs(tmp_path, monkeypatch, records=None):
    monkeypatch.setenv("TRUST_SIGNING_KEY", HMAC_KEY)
    d = tmp_path / "runs"
    chain = AuditChain(runs_dir=str(d), signing_key=HMAC_KEY)
    for i, rec in enumerate(records or [{"action": "read_ticket"}, {"action": "close_ticket"}]):
        chain.write({"run_id": f"r{i}", "timestamp": "2026-10-16T00:00:0%dZ" % i,
                     "type": "agent_action", "status": "success", **rec})
    return str(d)


@pytest.fixture()
def bundle(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    return export_air_evidence(_runs(tmp_path, monkeypatch), output_dir=str(out),
                               anchor=False).path


def _rewrite(src, dst, replace=None):
    """Copy a bundle member by member, replacing some members' bytes."""
    replace = replace or {}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info, replace.get(info.filename, zin.read(info.filename)))
    return dst


def _verify(path):
    return verify_bundle(str(path), out=io.StringIO())


def test_the_genuine_bundle_verifies(bundle, tmp_path):
    assert _verify(bundle)["records"] == 2
    # Re-zipping member by member is not tampering.
    assert _verify(_rewrite(bundle, tmp_path / "rezipped.air-evidence"))["records"] == 2


def test_a_manifest_that_repeats_a_key_is_refused(bundle, tmp_path):
    """Python keeps the LAST value of a repeated key; other readers keep the
    first. Put a forged value first and the genuine one last, and the
    signature (over the manifest as Python parses it) still verified while a
    first-value reader saw the forgery."""
    with zipfile.ZipFile(bundle) as z:
        raw = z.read("manifest.json")
    assert raw.startswith(b"{")
    forged = b'{"bundle_id": "FORGED-BY-ATTACKER", "counts": {"actions": 999},' + raw[1:]
    path = _rewrite(bundle, tmp_path / "dup.air-evidence", {"manifest.json": forged})
    with pytest.raises(VerificationFailure) as e:
        _verify(path)
    assert e.value.check == 2
    assert "repeats the key 'bundle_id'" in e.value.message


def test_repeated_keys_are_found_at_any_depth():
    with pytest.raises(VerificationFailure, match="repeats the key 'b'"):
        _loads('{"a": [{"b": 1, "b": 2}]}', "x.json", 3)
    assert _loads('{"a": {"b": 1}, "c": {"b": 2}}', "x.json", 3) == {"a": {"b": 1}, "c": {"b": 2}}


@pytest.mark.parametrize("prefix", [b"%PDF-1.4 a document a reader opens instead\n", None])
def test_bytes_before_the_archive_are_refused(bundle, tmp_path, prefix):
    if prefix is None:
        # A whole ZIP prepended: the file still starts with a valid header.
        decoy = tmp_path / "decoy.zip"
        with zipfile.ZipFile(decoy, "w") as z:
            z.writestr("readme.txt", "nothing to see")
        prefix = decoy.read_bytes()
    path = tmp_path / "prepended.air-evidence"
    path.write_bytes(prefix + open(bundle, "rb").read())
    with pytest.raises(VerificationFailure) as e:
        _verify(path)
    assert e.value.check == 1
    assert "bytes were added before it" in e.value.message


def test_bytes_after_the_archive_are_refused(bundle, tmp_path):
    path = tmp_path / "appended.air-evidence"
    path.write_bytes(open(bundle, "rb").read() + b"<script>payload()</script>")
    with pytest.raises(VerificationFailure) as e:
        _verify(path)
    assert e.value.check == 1
    assert "26 bytes follow the end of the archive" in e.value.message


def test_a_bundle_exported_with_anchoring_off_says_so(tmp_path, monkeypatch):
    import air_blackbox

    monkeypatch.setenv("TRUST_SIGNING_KEY", HMAC_KEY)
    with air_blackbox.record("malformed", runs_dir=str(tmp_path / "runs"), anchor=False) as rec:
        rec.action("read_ticket", "ticket #1")
    out = io.StringIO()
    verify_bundle(rec.bundle_path, out=out)
    assert "not anchored (anchoring disabled)" in out.getvalue()


def test_json_nested_beyond_any_interpreter_fails_cleanly():
    """Nesting deeper than the interpreter's JSON parser allows is a check
    failure, never a RecursionError traceback. A million levels is past the
    limit of every supported Python."""
    with pytest.raises(VerificationFailure) as e:
        _loads("[" * 1_000_000 + "]" * 1_000_000, "a record", 3)
    assert e.value.check == 3
    assert e.value.message == "a record is nested too deeply to verify"


def _round_trips(value):
    try:
        json.loads(json.dumps(value, sort_keys=True))
        return True
    except RecursionError:
        return False


def test_a_deeply_nested_record_verifies_or_fails_cleanly(tmp_path, monkeypatch):
    """The TypeScript writer allows deeper nesting than Python 3.11's default
    recursion limit, and the verifier crashed with a RecursionError traceback
    instead of reporting a failure. From 3.12 the json module has its own,
    higher limit, so the same genuine record verifies there."""
    deep = {}
    node = deep
    for _ in range(3000):
        node["x"] = {}
        node = node["x"]
    readable_here = _round_trips(deep)
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(20000)
    try:
        runs = _runs(tmp_path, monkeypatch, [{"action": "deep", "context": deep}])
        (tmp_path / "out").mkdir()
        path = export_air_evidence(runs, output_dir=str(tmp_path / "out"), anchor=False).path
    finally:
        sys.setrecursionlimit(limit)
    if readable_here:
        assert _verify(path)["records"] == 1
        return
    with pytest.raises(VerificationFailure) as e:
        _verify(path)
    assert e.value.check == 3
    assert "nested too deeply" in e.value.message
