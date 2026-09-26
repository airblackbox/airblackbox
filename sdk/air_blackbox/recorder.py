"""Record what an agent does into a signed evidence file anyone can verify.

No server, no tokens, no optional extras::

    import air_blackbox as air

    with air.record("support-agent") as rec:
        rec.action("read_ticket", "ticket #4821")
        rec.action("issue_refund", "order 991, $40", human_reviewer="dana@acme.com")

    print(rec.bundle_path)   # drop this file on https://airblackbox.ai/verify

Each action is chained (HMAC-SHA256), individually signed (Ed25519), and on
export the chain head is timestamped by an external RFC 3161 authority when
one is reachable. An unreachable authority is recorded in the bundle as a
gap, never hidden.

This is the single-process path. The chain has exactly one writer by design,
so several processes sharing one history should use the ingest server
instead: docs/guides/ingest-integration.md.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Union

from air_blackbox.gate.covenant import Covenant
from air_blackbox.gate.receipt import ActionReceipt, ReceiptSigner, hash_payload
from air_blackbox.trust.chain import AuditChain

logger = logging.getLogger(__name__)

__all__ = ["record", "Recorder", "Recorded"]

_KEY_FILE = ".air-receipt-key"


@dataclass(frozen=True)
class Recorded:
    """What happened to one recorded action."""
    action: str
    decision: str      # permit | require_approval | forbid
    chain_hash: str

    @property
    def allowed(self) -> bool:
        """True only when the covenant permits the action outright. An action
        needing approval is recorded but not yet allowed."""
        return self.decision == "permit"


def _load_or_create_signer(runs_dir: str) -> ReceiptSigner:
    """Ed25519, persisted beside the records so the signer's public key -
    the identity an auditor pins - survives restarts.

    Ed25519 rather than ML-DSA-65 even when the pqc extra is installed: the
    point of this path is a file a non-engineer can check in a browser, and
    WebCrypto verifies Ed25519 but not ML-DSA.
    """
    path = os.path.join(runs_dir, _KEY_FILE)
    if os.path.exists(path):
        try:
            with open(path) as f:
                doc = json.load(f)
            if doc.get("algorithm") == "ed25519":
                return ReceiptSigner(private_key=bytes.fromhex(doc["seed"]))
        except (OSError, ValueError, KeyError, AttributeError):
            pass
        # Never overwrite an existing key: replacing it silently rotates the
        # identity every earlier receipt in this directory was signed under.
        raise RuntimeError(
            f"{path} exists but is not an Ed25519 key this recorder can use. "
            f"Point runs_dir at a fresh directory rather than replacing it.")

    seed = os.urandom(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"algorithm": "ed25519", "seed": seed.hex()}, f)
    return ReceiptSigner(private_key=seed)


class Recorder:
    """Records actions for one agent into ``runs_dir`` and exports them as a
    signed ``.air-evidence`` bundle.

    Args:
        name: the agent's name; appears in the bundle as its tenant.
        runs_dir: where records and the signing key live. Defaults to
            ``./air-runs/<name>``. Reusing a directory continues its chain.
        covenant: optional policy - a Covenant or a path to a covenant YAML.
            Without one every action is recorded as permitted. With one,
            each action's decision is recorded and returned, and it is up to
            the caller to honour it: this records, it does not intercept.
        anchor: timestamp the chain head with an external RFC 3161 authority
            on export. Needs network access; failure is recorded as a gap.
        anchor_timeout: seconds to wait per timestamp authority.
    """

    def __init__(self, name: str = "agent", runs_dir: Optional[str] = None,
                 covenant: Union[Covenant, str, None] = None,
                 anchor: bool = True, anchor_timeout: float = 10.0):
        self.name = name
        self.runs_dir = runs_dir or os.path.join("air-runs", name)
        os.makedirs(self.runs_dir, exist_ok=True)
        if isinstance(covenant, str):
            covenant = Covenant.from_yaml(covenant)
        self.covenant: Optional[Covenant] = covenant
        self.anchor = anchor
        self.anchor_timeout = anchor_timeout
        self.bundle_path: Optional[str] = None
        self.last_export_note: str = ""
        self._chain = AuditChain(runs_dir=self.runs_dir, resume=True)
        self._signer = _load_or_create_signer(self.runs_dir)
        self._written = 0

    def action(self, name: str, detail: str = "", *,
               human_reviewer: Optional[str] = None,
               decision_type: Optional[str] = None,
               **fields: Any) -> Recorded:
        """Record one action.

        Args:
            name: snake_case action name, e.g. ``issue_refund``. With a
                covenant loaded this must match a rule exactly, or it is
                recorded as forbidden under default-deny.
            detail: human-readable description of what was done.
            human_reviewer: who reviewed the decision, if anyone. Evidence
                bundles flag consequential decisions that lack one.
            decision_type: marks the action as a screening decision
                (advance | reject | rank | recommend) so the bundle counts it.
            **fields: extra context. Passed to the covenant's guards and
                stored on the record.
        """
        decision = "permit"
        if self.covenant:
            decision = self.covenant.evaluate(
                name, {"detail": detail, **fields}).value

        record: dict = {
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "agent_action",
            "action": name,
            "detail": detail[:2000],
            "status": "blocked" if decision == "forbid" else "success",
            "covenant_decision": decision,
        }
        if fields:
            record["context"] = fields
        category = ""
        if decision_type or human_reviewer:
            category = "screening"
            screening = {"decision_type": decision_type or name}
            if human_reviewer:
                screening["human_reviewer"] = human_reviewer[:100]
            record["screening"] = screening
        if self.covenant:
            record["covenant_hash"] = self.covenant.hash

        receipt = ActionReceipt(
            agent_id=self.name,
            action_name=name,
            action_category=category,
            payload_hash=hash_payload(detail) if detail else "",
            covenant_hash=self.covenant.hash if self.covenant else "",
            decision=decision,
            authorized=(decision == "permit"),
        )
        self._signer.sign_authorization(receipt)
        record["receipt"] = receipt.to_dict()

        chain_hash = self._chain.write(record)
        self._written += 1
        return Recorded(action=name, decision=decision, chain_hash=chain_hash)

    def export(self, output_dir: Optional[str] = None) -> str:
        """Write a signed ``.air-evidence`` bundle and return its path.

        The chain is verified first and the result is stamped into the signed
        manifest, so a bundle never quietly attests a broken history.
        """
        from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
        from air_blackbox.replay.engine import ReplayEngine

        engine = ReplayEngine(runs_dir=self.runs_dir)
        total = engine.load()
        verification = engine.verify_chain()
        fully_intact = (verification.intact
                        and verification.verified_records == total)

        anchor_manifest = (self._anchor(engine._raw_records) if self.anchor
                           else {"anchored": False, "reason": "anchoring disabled"})

        path, _manifest = generate_evidence_bundle_v1(
            chain_entries=engine._raw_records,
            tenant=self.name,
            signer=self._signer,
            chain_verification={"fully_intact": fully_intact,
                                 **asdict(verification)},
            system={"name": self.name, "high_risk_rationale": "", "deployer": ""},
            anchor_manifest=anchor_manifest,
            output_dir=output_dir or self.runs_dir,
        )
        self.bundle_path = path
        if not fully_intact:
            logger.warning("exported %s but the chain did not fully verify; "
                           "the manifest records why", path)
        return path

    def _anchor(self, records: list) -> dict:
        import base64

        from air_blackbox.anchor import compute_head, timestamp_head

        head = compute_head(self.runs_dir)
        if not head:
            return {"anchored": False, "reason": "no records"}
        seq_max = max((r.get("chain_seq") or 0 for r in records), default=0)
        result = timestamp_head(head, None, timeout=self.anchor_timeout)
        if not result.ok:
            self.last_export_note = f"no external timestamp: {result.error}"
            return {"anchored": False, "head": head, "seq_max": seq_max,
                    "error": result.error}
        self.last_export_note = f"timestamped by {result.tsa_url}"
        return {"anchored": True, "head": head, "seq_max": seq_max,
                "tsa_url": result.tsa_url, "timestamp": result.timestamp,
                "tsr_b64": base64.b64encode(result.tsr).decode()}

    def __enter__(self) -> "Recorder":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        # Export even when the block raised: the record of a run that failed
        # is evidence too, and usually the evidence someone asks for.
        if self._written:
            self.export()
        return False


def record(name: str = "agent", **kwargs: Any) -> Recorder:
    """Start recording an agent. Use as a context manager so the evidence
    bundle is written on exit::

        with air_blackbox.record("my-agent") as rec:
            rec.action("send_email", "welcome email to new signup")
    """
    return Recorder(name, **kwargs)
