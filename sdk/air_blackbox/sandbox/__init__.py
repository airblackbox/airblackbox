"""Compliance AI sandbox - agents graduate to production with a signed record.

A sandbox session provisions an isolated AIR gateway (fresh runs directory,
locally generated signing key), runs your agent against it, and produces a
graduation report: was every LLM call recorded, is the chain intact, did
anything error or get blocked. The exit artifact is a signed evidence bundle
an approver can verify independently.

    air-blackbox sandbox run --gateway-bin ./gateway -- python my_agent.py
"""

from air_blackbox.sandbox.session import SandboxSession, SandboxVerdict

__all__ = ["SandboxSession", "SandboxVerdict"]
