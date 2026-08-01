"""The 'Audit Day' demo is a design-partner-facing artifact (the DM says "run
the exact thing"), so CI guards that it still runs and still catches the
operator rewrite. Skips when openssl is absent, since the anchor act needs it.
"""

import os
import shutil
import subprocess
import sys

import pytest

_DEMO = os.path.join(
    os.path.dirname(__file__), "..", "..", "demo", "hiring_audit_day.py")

pytestmark = pytest.mark.skipif(
    shutil.which("openssl") is None,
    reason="the anchor act needs openssl for the local TSA")


def test_demo_catches_the_cover_up():
    proc = subprocess.run(
        [sys.executable, _DEMO], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "REWRITE DETECTED" in proc.stdout
    # The tension only works if the company's own check passes first.
    assert "internal hash-chain self-check: PASSES" in proc.stdout
    assert "BLOCKED" in proc.stdout
