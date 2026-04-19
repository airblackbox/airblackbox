"""AIR Gate — pre-execution policy enforcement with bilateral receipts.

The gate sits between your agent and the actions it takes. Every action
goes through a policy check, and every decision produces a bilateral
receipt: authorization + execution result, cryptographically signed.

Usage:
    from air_blackbox.gate import Gate, Covenant

    covenant = Covenant.from_yaml("covenant.yaml")
    gate = Gate(covenant=covenant)

    # Before executing an action:
    receipt = gate.authorize("my-agent", "email", "send_email",
                             payload={"to": "user@example.com"})

    if receipt.authorized:
        result = execute_action(...)
        gate.seal(receipt, result=result, status="success")
    else:
        handle_blocked(receipt)
"""

from air_blackbox.gate.covenant import Covenant, Rule, RuleAction
from air_blackbox.gate.receipt import ActionReceipt, ReceiptStatus
from air_blackbox.gate.engine import Gate

__all__ = [
    "Gate",
    "Covenant",
    "Rule",
    "RuleAction",
    "ActionReceipt",
    "ReceiptStatus",
]
