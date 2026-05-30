"""
Gate - the pre-execution policy engine.

The Gate sits between an agent and the actions it takes. Every action is
checked against a Covenant before it runs, and every decision produces a
bilateral ActionReceipt:

  Phase 1 - authorize(): evaluate the covenant, decide permit / forbid /
            require_approval, and sign the authorization.
  Phase 2 - seal():      after the action runs, attach the result hash and
            sign the completed receipt.

The Gate does not execute actions itself. The caller runs the action and
reports the result back via seal(). This keeps the gate a pure policy and
evidence layer with no side effects of its own.

Usage:
    from air_blackbox.gate import Gate, Covenant

    covenant = Covenant.from_yaml("covenant.yaml")
    gate = Gate(covenant=covenant)

    receipt = gate.authorize(
        agent_id="loan-processor",
        action_name="approve_loan",
        category="loan",
        payload={"amount": 75000},
        context={"amount": 75000},
    )

    if receipt.authorized:
        result = do_the_thing()
        gate.seal(receipt, result=result, status="success")
    else:
        handle_blocked(receipt)
"""

from typing import Optional, Any
from datetime import datetime

from air_blackbox.gate.covenant import Covenant, RuleAction
from air_blackbox.gate.receipt import (
    ActionReceipt,
    ReceiptStatus,
    ReceiptSigner,
    hash_payload,
    hash_result,
)


# Maps a covenant decision to (authorized?, receipt status).
_DECISION_MAP = {
    RuleAction.PERMIT: (True, ReceiptStatus.AUTHORIZED),
    RuleAction.FORBID: (False, ReceiptStatus.DENIED),
    RuleAction.REQUIRE_APPROVAL: (False, ReceiptStatus.PENDING_APPROVAL),
}


class Gate:
    """Pre-execution policy enforcement with bilateral receipts."""

    def __init__(self, covenant: Covenant, signer: Optional[ReceiptSigner] = None):
        if covenant is None:
            raise ValueError("Gate requires a Covenant")
        self.covenant = covenant
        self.signer = signer or ReceiptSigner()

    @property
    def signing_method(self) -> str:
        return self.signer.method

    def authorize(
        self,
        agent_id: str,
        action_name: str,
        category: str = "",
        payload: Any = None,
        context: Optional[dict] = None,
        parent_receipt_id: Optional[str] = None,
    ) -> ActionReceipt:
        eval_context = dict(context or {})
        if category and "category" not in eval_context:
            eval_context["category"] = category

        decision = self.covenant.evaluate(action_name, eval_context)
        authorized, status = _DECISION_MAP[decision]

        receipt = ActionReceipt(
            agent_id=agent_id,
            action_name=action_name,
            action_category=category,
            payload_hash=hash_payload(payload) if payload is not None else "",
            covenant_hash=self.covenant.hash,
            decision=decision.value,
            authorized=authorized,
            parent_receipt_id=parent_receipt_id,
            status=status,
        )

        self.signer.sign_authorization(receipt)
        return receipt

    def seal(
        self,
        receipt: ActionReceipt,
        result: Any = None,
        status: str = "success",
    ) -> ActionReceipt:
        if not receipt.authorized:
            raise ValueError(
                f"cannot seal an unauthorized receipt "
                f"(decision was '{receipt.decision}', status '{receipt.status.value}')"
            )

        receipt.result_hash = hash_result(result) if result is not None else ""
        receipt.result_status = status
        receipt.sealed_at = datetime.utcnow().isoformat() + "Z"
        receipt.status = ReceiptStatus.SEALED if status == "success" else ReceiptStatus.FAILED

        self.signer.sign_seal(receipt)
        return receipt

    def verify(self, receipt: ActionReceipt) -> tuple[bool, bool]:
        return self.signer.verify_full(receipt)
