"""The proof harness is a public credibility artifact, so CI guards it:
AIR must deliver every guarantee, AND the comparison must stay real (the bare
hash chain must still MISS the operator rewrite, or the harness proves nothing).
"""

import importlib.util
import os
import shutil

import pytest

_PROVE = os.path.join(os.path.dirname(__file__), "..", "..", "bench", "proof", "prove.py")
_spec = importlib.util.spec_from_file_location("air_prove", _PROVE)
prove = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prove)

pytestmark = pytest.mark.skipif(
    shutil.which("openssl") is None,
    reason="anchor rows need openssl for the local TSA")


@pytest.fixture(scope="module")
def rows():
    return dict(prove.collect())


def test_air_delivers_every_guarantee(rows):
    for name, expected in prove.AIR_EXPECTED.items():
        assert rows[name]["AIR Blackbox"] == expected, name


def test_plain_log_catches_nothing(rows):
    assert rows["edit a past record"]["plain log"] == prove.MISSED
    assert rows["delete a record from history"]["plain log"] == prove.MISSED
    assert rows["rewrite + re-sign entire history"]["plain log"] == prove.MISSED


def test_hash_chain_catches_edits_but_misses_operator_rewrite(rows):
    # This asymmetry is the whole point: a good hash chain catches edits and
    # deletions but not an operator who rewrites and re-signs. The external
    # anchor is what closes that gap, and AIR must be the only column that does.
    assert rows["edit a past record"]["hash chain"] == prove.DETECTED
    assert rows["delete a record from history"]["hash chain"] == prove.DETECTED
    assert rows["rewrite + re-sign entire history"]["hash chain"] == prove.MISSED
    assert rows["rewrite + re-sign entire history"]["AIR Blackbox"] == prove.DETECTED


def test_no_secret_verification_only_air(rows):
    assert rows["verify with no secret"]["hash chain"] == prove.NO
    assert rows["verify with no secret"]["AIR Blackbox"] == prove.YES
