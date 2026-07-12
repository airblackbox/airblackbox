"""Tests for the compliance sandbox (external-gateway mode).

Managed-gateway mode needs the Go binary and is exercised end-to-end in CI's
Go jobs and manually; these tests drive the orchestration and verdict logic
with an "agent" that writes chained records the way a gateway would.
"""

import json
import os
import sys
import tempfile

from air_blackbox.sandbox import SandboxSession

# An agent that records N chained calls into the sandbox runs dir, like a
# gateway would, then exits with the requested code.
AGENT = """
import sys
sys.path.insert(0, {sdk_path!r})
from air_blackbox.trust.chain import AuditChain
chain = AuditChain(runs_dir={runs_dir!r}, signing_key="sandbox-test-key")
for i in range(int(sys.argv[1])):
    chain.write({{
        "run_id": f"00000000-0000-0000-0000-00000000000{{i}}",
        "model": "gpt-4", "status": sys.argv[3] if len(sys.argv) > 3 else "success",
        "tokens": {{"total": 10}},
        "timestamp": f"2026-07-03T00:00:0{{i}}Z",
    }})
sys.exit(int(sys.argv[2]))
"""

SDK_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(n_calls, exit_code, status="success"):
    with tempfile.TemporaryDirectory() as d:
        runs = os.path.join(d, "runs")
        os.makedirs(runs)
        with open(os.path.join(runs, ".air-signing-key"), "w") as f:
            f.write("sandbox-test-key\n")
        session = SandboxSession(
            sandbox_dir=d, gateway_url="http://unused:1", runs_dir=runs)
        agent = AGENT.format(sdk_path=os.path.abspath(SDK_PATH), runs_dir=runs)
        verdict = session.run(
            [sys.executable, "-c", agent, str(n_calls), str(exit_code), status],
            timeout=60)
        with open(os.path.join(d, "report.json")) as f:
            report = json.load(f)
        # The temp dir vanishes when this function returns, so capture
        # artifact existence while it still exists.
        artifacts = {
            "evidence": bool(verdict.evidence_path)
                        and os.path.exists(verdict.evidence_path),
            "lake": bool(verdict.lake_dir) and os.path.isdir(verdict.lake_dir),
        }
        return verdict, report, artifacts


def test_clean_run_graduates():
    verdict, report, artifacts = _run(n_calls=3, exit_code=0)
    assert verdict.passed
    assert verdict.total_calls == 3
    assert verdict.chain_intact and verdict.chain_verified == 3
    assert report["passed"] is True
    assert artifacts["evidence"]


def test_nonzero_agent_exit_fails():
    verdict, _, _ = _run(n_calls=3, exit_code=2)
    assert not verdict.passed
    assert any("exited nonzero" in r for r in verdict.reasons)


def test_no_recorded_calls_fails():
    verdict, _, _ = _run(n_calls=0, exit_code=0)
    assert not verdict.passed
    assert any("no LLM calls" in r for r in verdict.reasons)


def test_errored_calls_fail():
    verdict, _, _ = _run(n_calls=2, exit_code=0, status="error")
    assert not verdict.passed
    assert any("errored" in r for r in verdict.reasons)


def test_requires_gateway_config():
    import pytest
    with pytest.raises(ValueError):
        SandboxSession(sandbox_dir="/tmp/x")
