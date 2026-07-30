"""
Gate - the policy enforcement engine.

Sits between the agent and the actions it takes. Every action goes through
the covenant, produces a bilateral receipt, and gets chained into the
HMAC-SHA256 audit trail.

Usage:
    from air_blackbox.gate import Gate, Covenant

    # Load policy
    covenant = Covenant.from_yaml("covenant.yaml")

    # Create gate
    gate = Gate(covenant=covenant)

    # Authorize an action (Phase 1)
    receipt = gate.authorize(
        agent_id="loan-processor",
        action_name="approve_loan",
        payload={"applicant": "jane@example.com", "amount": 75000},
        context={"amount": 75000},
    )

    if receipt.authorized:
        # Execute the action
        result = process_loan(...)

        # Seal the receipt with the result (Phase 2)
        gate.seal(receipt, result=result, status="success")
    else:
        print(f"Blocked: {receipt.decision}")

    # Verify the full receipt chain
    print(gate.verify(receipt))

    # Cross-agent delegation
    child_receipt = gate.authorize(
        agent_id="notifier-agent",
        action_name="send_confirmation",
        payload={"to": "jane@example.com"},
        parent_receipt=receipt,  # links delegation chain
    )
"""

import json
import os
import logging
from typing import Any, Optional, Callable

from air_blackbox.gate.covenant import Covenant, RuleAction
from air_blackbox.gate.receipt import (
    ActionReceipt,
    ReceiptStatus,
    ReceiptSigner,
    hash_payload,
    hash_result,
)
from air_blackbox.trust.chain import AuditChain

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_RuntimeMonitor = None


def _get_runtime_monitor_class():
    global _RuntimeMonitor
    if _RuntimeMonitor is None:
        from air_blackbox.gate.runtime import RuntimeMonitor
        _RuntimeMonitor = RuntimeMonitor
    return _RuntimeMonitor


class Gate:
    """Policy enforcement gate with bilateral receipts and runtime monitoring.

    The gate evaluates every action against the covenant, signs the
    authorization decision, and produces a receipt. After execution,
    the result is sealed into the same receipt.

    When a RuntimeMonitor is attached, authorize() also runs real-time
    compliance checks (PII, injection, boundary, token budget) and
    blocks actions that violate runtime policy.

    Args:
        covenant: The policy rules for this agent
        signing_key: Ed25519 private key bytes (or None to auto-generate)
        hmac_key: HMAC key for the audit chain (separate from Ed25519)
        runs_dir: Directory for receipt storage
        on_approval_needed: Callback when human approval is required.
            Signature: (receipt: ActionReceipt) -> bool
            Returns True if approved, False if rejected.
        runtime_monitor: Optional RuntimeMonitor for real-time compliance checks.
            When set, authorize() scans payloads before policy evaluation.
    """

    def __init__(
        self,
        covenant: Covenant,
        signing_key: Optional[bytes] = None,
        hmac_key: Optional[str] = None,
        runs_dir: Optional[str] = None,
        on_approval_needed: Optional[Callable[[ActionReceipt], bool]] = None,
        runtime_monitor=None,
    ):
        self.covenant = covenant
        self.signer = ReceiptSigner(private_key=signing_key, hmac_key=hmac_key)
        self.on_approval_needed = on_approval_needed
        self.runtime_monitor = runtime_monitor

        self._runs_dir = runs_dir or os.path.join(
            os.path.expanduser("~"), ".air-blackbox", "receipts"
        )
        os.makedirs(self._runs_dir, exist_ok=True)

        # HMAC audit chain - receipts get chained for Art. 12
        self._chain = AuditChain(
            runs_dir=self._runs_dir,
            signing_key=hmac_key,
        )

        # In-memory receipt index for delegation chain lookups
        self._receipts: dict[str, ActionReceipt] = {}

    @property
    def public_key_hex(self) -> Optional[str]:
        """The Ed25519 public key for third-party verification."""
        return self.signer.public_key_hex

    @property
    def signing_method(self) -> str:
        """Whether we're using Ed25519 or HMAC-SHA256 fallback."""
        return self.signer.method

    def authorize(
        self,
        agent_id: str,
        action_name: str,
        payload: Any = None,
        context: dict = None,
        category: str = "",
        parent_receipt: Optional[ActionReceipt] = None,
        metadata: dict = None,
    ) -> ActionReceipt:
        """Evaluate an action against the covenant and produce a receipt.

        This is Phase 1 of the bilateral receipt. The gate checks the
        covenant rules, makes a decision, signs the authorization, and
        chains it into the audit trail.

        If a RuntimeMonitor is attached, the payload text and tool names
        are scanned for PII, injection, boundary violations, and budget
        overruns BEFORE the covenant is evaluated. A runtime block
        overrides a covenant permit.

        Args:
            agent_id: Identifier for the requesting agent
            action_name: What action is being attempted
            payload: The action arguments (hashed, never stored raw)
            context: Runtime context for condition evaluation
            category: Action category for rule matching
            parent_receipt: Receipt from the delegating agent (for chains)
            metadata: Arbitrary context to include in the receipt

        Returns:
            ActionReceipt with authorization decision and signature
        """
        context = context or {}
        metadata = metadata or {}
        if category:
            context["category"] = category

        # Runtime compliance checks (if monitor is attached)
        runtime_blocked = False
        if self.runtime_monitor is not None:
            # Extract text from payload for scanning
            scan_text = ""
            tool_names = []
            token_count = 0

            if isinstance(payload, str):
                scan_text = payload
            elif isinstance(payload, dict):
                # Common payload shapes: {"text": ...}, {"prompt": ...}, {"input": ...}
                scan_text = str(payload.get("text", payload.get("prompt", payload.get("input", ""))))
                tool_names = payload.get("tools", payload.get("tool_names", []))
                token_count = payload.get("tokens", payload.get("token_count", 0))

            if not tool_names:
                tool_names = [action_name]

            check_result = self.runtime_monitor.check(
                text=scan_text,
                tool_names=tool_names,
                token_count=token_count,
                metadata={"agent_id": agent_id, "action_name": action_name},
            )

            if check_result.has_violations:
                metadata["runtime_violations"] = [v.to_dict() for v in check_result.violations]
                metadata["runtime_check_ms"] = check_result.check_duration_ms

            if check_result.blocked:
                runtime_blocked = True
                metadata["runtime_blocked"] = True
                metadata["runtime_block_reasons"] = check_result.block_reasons

        # Evaluate covenant
        decision = self.covenant.evaluate(action_name, context)

        # Handle human approval
        authorized = False
        status = ReceiptStatus.DENIED

        if decision == RuleAction.PERMIT:
            authorized = True
            status = ReceiptStatus.AUTHORIZED

        elif decision == RuleAction.REQUIRE_APPROVAL:
            status = ReceiptStatus.PENDING_APPROVAL
            if self.on_approval_needed:
                # Create preliminary receipt for the approval callback
                preliminary = ActionReceipt(
                    agent_id=agent_id,
                    action_name=action_name,
                    action_category=category,
                    payload_hash=hash_payload(payload) if payload else "",
                    covenant_hash=self.covenant.hash,
                    decision=decision.value,
                    metadata=metadata or {},
                )
                approved = self.on_approval_needed(preliminary)
                if approved:
                    authorized = True
                    status = ReceiptStatus.AUTHORIZED
                    context["human_approved"] = True
                else:
                    status = ReceiptStatus.DENIED
            else:
                # No callback registered - safe default is deny
                status = ReceiptStatus.DENIED

        elif decision == RuleAction.FORBID:
            authorized = False
            status = ReceiptStatus.DENIED

        # Runtime block overrides covenant permit
        if runtime_blocked and authorized:
            authorized = False
            status = ReceiptStatus.DENIED
            logger.info(
                "gate.runtime_override agent=%s action=%s reasons=%s",
                agent_id, action_name, metadata.get("runtime_block_reasons", []),
            )

        # Build the receipt
        receipt = ActionReceipt(
            agent_id=agent_id,
            action_name=action_name,
            action_category=category,
            payload_hash=hash_payload(payload) if payload else "",
            covenant_hash=self.covenant.hash,
            decision=decision.value,
            authorized=authorized,
            parent_receipt_id=parent_receipt.receipt_id if parent_receipt else None,
            status=status,
            metadata=metadata or {},
        )

        # Sign the authorization
        self.signer.sign_authorization(receipt)

        # Chain into audit trail
        chain_hash = self._chain.write(receipt.to_dict())
        if chain_hash:
            receipt.chain_hash = chain_hash

        # Index for delegation lookups
        self._receipts[receipt.receipt_id] = receipt

        # Persist receipt
        self._write_receipt(receipt)

        logger.info(
            "gate.authorize agent=%s action=%s decision=%s authorized=%s receipt=%s",
            agent_id, action_name, decision.value, authorized, receipt.receipt_id,
        )

        return receipt

    def seal(
        self,
        receipt: ActionReceipt,
        result: Any = None,
        status: str = "success",
    ) -> ActionReceipt:
        """Seal a receipt with the execution result (Phase 2).

        After the action executes, call this to attach the result hash
        and seal the receipt with a second signature. The seal covers
        the authorization signature, so the entire lifecycle is bound.

        Args:
            receipt: The receipt from authorize()
            result: The execution result (hashed, never stored raw)
            status: "success", "failure", or "error"

        Returns:
            The sealed receipt
        """
        from datetime import datetime

        receipt.result_hash = hash_result(result) if result is not None else ""
        receipt.result_status = status
        receipt.sealed_at = datetime.utcnow().isoformat() + "Z"
        receipt.status = ReceiptStatus.SEALED if status == "success" else ReceiptStatus.FAILED

        # Sign the seal
        self.signer.sign_seal(receipt)

        # Update the chain with sealed receipt
        chain_hash = self._chain.write({
            "type": "seal",
            "receipt_id": receipt.receipt_id,
            "result_hash": receipt.result_hash,
            "result_status": receipt.result_status,
            "seal_sig": receipt.seal_sig,
            "sealed_at": receipt.sealed_at,
        })
        if chain_hash:
            receipt.chain_hash = chain_hash

        # Update stored receipt
        self._receipts[receipt.receipt_id] = receipt
        self._write_receipt(receipt)

        logger.info(
            "gate.seal receipt=%s status=%s result_hash=%s",
            receipt.receipt_id, status, receipt.result_hash[:16] if receipt.result_hash else "none",
        )

        return receipt

    def verify(self, receipt: ActionReceipt) -> dict:
        """Verify a receipt's signatures and chain integrity.

        Returns a verification report that a third party can use to
        confirm the receipt hasn't been tampered with.

        NOTE: `overall` is a *cryptographic* verdict - the signatures are
        valid and the receipt is internally consistent. It is NOT a statement
        that the action was allowed: a correctly-signed receipt for a *denied*
        action verifies as overall=True (the denial is a legitimate recorded
        outcome). Read `authorized`/`decision` to know whether the action was
        permitted.
        """
        auth_valid, seal_valid = self.signer.verify_full(receipt)

        return {
            "receipt_id": receipt.receipt_id,
            "signing_method": self.signer.method,
            "authorization_valid": auth_valid,
            "seal_valid": seal_valid,
            "is_sealed": receipt.status in (ReceiptStatus.SEALED, ReceiptStatus.FAILED),
            "has_parent": receipt.parent_receipt_id is not None,
            "covenant_hash": receipt.covenant_hash,
            "chain_hash": receipt.chain_hash,
            # The action's policy outcome, surfaced so callers don't mistake
            # a valid signature on a denial for permission.
            "authorized": receipt.authorized,
            "decision": receipt.decision,
            "overall": auth_valid and (seal_valid or not receipt.seal_sig),
        }

    def walk_delegation_chain(self, receipt: ActionReceipt) -> list[ActionReceipt]:
        """Walk the delegation chain from a receipt back to the root.

        Returns a list of receipts from the given receipt up to the
        root (the original authorization with no parent).
        """
        chain = [receipt]
        current = receipt
        seen = {receipt.receipt_id}

        while current.parent_receipt_id:
            # Cycle guard: a self- or mutually-referential parent link (which
            # nothing prevents when receipts are rebuilt from stored JSON)
            # must not spin forever.
            if current.parent_receipt_id in seen:
                break
            parent = self._receipts.get(current.parent_receipt_id)
            if not parent:
                break
            seen.add(parent.receipt_id)
            chain.append(parent)
            current = parent

        chain.reverse()  # Root first
        return chain

    def get_receipt(self, receipt_id: str) -> Optional[ActionReceipt]:
        """Look up a receipt by ID."""
        return self._receipts.get(receipt_id)

    @property
    def receipt_count(self) -> int:
        """Total receipts issued by this gate."""
        return len(self._receipts)

    def _write_receipt(self, receipt: ActionReceipt) -> None:
        """Persist a receipt to disk as JSON."""
        try:
            path = os.path.join(self._runs_dir, f"{receipt.receipt_id}.receipt.json")
            with open(path, "w") as f:
                json.dump(receipt.to_dict(), f, indent=2)
        except Exception:
            pass  # Non-blocking
