"""Browser session recording with covenant governance and a signed passport."""

import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from air_blackbox.gate.covenant import Covenant
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.trust.chain import AuditChain


@dataclass
class ActionDecision:
    """The governance result for one attempted action."""
    action: str
    decision: str            # permit | require_approval | forbid
    run_id: str
    chain_hash: Optional[str] = None
    approved: bool = False

    @property
    def allowed(self) -> bool:
        """True if the agent may perform the action now (permitted, or an
        approval-required action that has been approved)."""
        return self.decision == "permit" or (
            self.decision == "require_approval" and self.approved)

    @property
    def needs_approval(self) -> bool:
        return self.decision == "require_approval" and not self.approved

    @property
    def blocked(self) -> bool:
        return self.decision == "forbid"


@dataclass
class SessionPassport:
    """A verifiable summary of everything an agent did in one session."""
    session_id: str
    covenant_agent: Optional[str]
    covenant_hash: Optional[str]
    started_at: str
    ended_at: str
    total_actions: int
    action_counts: dict
    approvals: int
    blocked: int
    chain_intact: bool
    chain_verified: int
    verdict: str                 # CLEAN | VIOLATIONS
    violations: list = field(default_factory=list)


class BrowserSession:
    """Records governed browser/agent actions and issues a session passport.

    Framework-agnostic: it does not drive a browser, it governs and records
    whatever driver you use. Each `action()` call is evaluated against the
    covenant and written into the tamper-evident chain before you act.
    """

    def __init__(self, runs_dir: str = "./passport-runs",
                 covenant: Optional[str] = None,
                 signing_key: Optional[str] = None):
        self.session_id = str(uuid.uuid4())
        self.runs_dir = os.path.join(runs_dir, self.session_id)
        os.makedirs(self.runs_dir, exist_ok=True)
        self._chain = AuditChain(runs_dir=self.runs_dir, signing_key=signing_key)
        self._covenant = Covenant.from_yaml(covenant) if covenant else None
        self._counts: Counter = Counter()
        self._approvals = 0
        self._blocked = 0
        self._decisions: dict = {}
        self._started = datetime.now(timezone.utc).isoformat()
        self._ended: Optional[str] = None
        self._signing_key = signing_key

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._ended = datetime.now(timezone.utc).isoformat()
        return False

    def action(self, action: str, target: str = "", **context) -> ActionDecision:
        """Evaluate and record an attempted action. Returns the decision;
        the caller must honor it (only act when `.allowed`)."""
        decision = "permit"
        if self._covenant:
            ctx = {"target": target, "category": "browser", **context}
            decision = self._covenant.evaluate(action, ctx).value

        run_id = str(uuid.uuid4())
        record = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "browser_action",
            "action": action,
            "target": str(target)[:500],
            "session_id": self.session_id,
            "status": "blocked" if decision == "forbid" else "success",
            "covenant_decision": decision,
        }
        if self._covenant:
            record["covenant_hash"] = self._covenant.hash
        chain_hash = self._chain.write(record)

        self._counts[action] += 1
        if decision == "forbid":
            self._blocked += 1

        result = ActionDecision(action=action, decision=decision,
                                run_id=run_id, chain_hash=chain_hash)
        self._decisions[run_id] = result
        return result

    def approve(self, decision: ActionDecision, approver: str = "human") -> None:
        """Record explicit human approval for a require_approval action.

        This is the Article 14 / GDPR Art 22 moment: a human authorized a
        candidate-affecting action, recorded into the chain as its own event.
        """
        decision.approved = True
        self._approvals += 1
        self._chain.write({
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "human_approval",
            "action": "human_approval",
            "approves_run_id": decision.run_id,
            "approves_action": decision.action,
            "approver": approver,
            "session_id": self.session_id,
            "status": "success",
        })

    def passport(self) -> SessionPassport:
        """Compute the session passport from the recorded evidence."""
        engine = ReplayEngine(runs_dir=self.runs_dir)
        engine.load()
        chain = engine.verify_chain(signing_key=self._signing_key)

        violations = []
        # An approval-required action that was never approved is a violation:
        # the agent either acted without sign-off or the session is incomplete.
        for run_id, d in self._decisions.items():
            if d.decision == "forbid":
                violations.append(f"blocked action attempted: {d.action}")
            elif d.decision == "require_approval" and not d.approved:
                violations.append(f"unapproved sensitive action: {d.action}")

        verdict = "CLEAN" if (chain.intact and not violations) else "VIOLATIONS"
        return SessionPassport(
            session_id=self.session_id,
            covenant_agent=self._covenant.agent if self._covenant else None,
            covenant_hash=self._covenant.hash if self._covenant else None,
            started_at=self._started,
            ended_at=self._ended or datetime.now(timezone.utc).isoformat(),
            total_actions=sum(self._counts.values()),
            action_counts=dict(self._counts),
            approvals=self._approvals,
            blocked=self._blocked,
            chain_intact=chain.intact,
            chain_verified=chain.verified_records,
            verdict=verdict,
            violations=violations,
        )

    def export_passport(self, output_dir: Optional[str] = None) -> Optional[str]:
        """Package the session into a signed .air-evidence bundle whose scan
        payload is the passport - the document to show a platform or client."""
        from dataclasses import asdict
        try:
            from air_blackbox.export.evidence_bundle import generate_evidence_zip
        except ImportError:
            return None
        engine = ReplayEngine(runs_dir=self.runs_dir)
        engine.load()
        key = self._signing_key or os.environ.get(
            "TRUST_SIGNING_KEY", "air-blackbox-default")
        return generate_evidence_zip(
            chain_entries=engine._raw_records,
            scan_results={"session_passport": asdict(self.passport())},
            signing_key=key,
            output_dir=output_dir or self.runs_dir,
        )
