"""
Covenant — declarative policy DSL for AI agent behavior.

A covenant is a set of rules an agent commits to BEFORE execution.
The covenant hash is included in every receipt, proving which rules
were active when the action was authorized.

YAML format:
    agent: loan-processor
    version: "1.0"
    rules:
      - permit: read_credit_score
      - permit: calculate_risk
      - require_approval: approve_loan
        when: "amount > 50000"
      - forbid: delete_records
      - forbid: send_email
        unless: human_approved

Enforcement: forbid wins. If an action matches both a permit and a
forbid rule, the forbid takes precedence. This matches the principle
of least privilege.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import yaml


class RuleAction(str, Enum):
    """What the policy engine does when this rule matches."""
    PERMIT = "permit"
    FORBID = "forbid"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class Rule:
    """A single policy rule in a covenant.

    Attributes:
        action: permit, forbid, or require_approval
        target: the action name this rule applies to (e.g. "send_email")
        when: optional condition string (e.g. "amount > 50000")
        unless: optional exception (e.g. "human_approved")
        category: optional grouping (e.g. "email", "database", "file")
    """
    action: RuleAction
    target: str
    when: Optional[str] = None
    unless: Optional[str] = None
    category: Optional[str] = None

    def matches(self, action_name: str, context: dict = None) -> bool:
        """Check if this rule applies to the given action.

        Args:
            action_name: The action being attempted (e.g. "send_email")
            context: Runtime context for condition evaluation

        Returns:
            True if this rule's target matches the action name.
        """
        if self.target == "*":
            return True
        # Exact match or category match
        if action_name == self.target:
            return True
        if self.category and context and context.get("category") == self.category:
            return True
        return False

    def evaluate_condition(self, context: dict = None) -> bool:
        """Evaluate the 'when' condition against runtime context.

        Returns True if:
        - No 'when' condition is set (rule always applies), OR
        - The 'when' condition evaluates to true

        Returns False if:
        - 'unless' condition is met (exception overrides)
        """
        context = context or {}

        # Check 'unless' exception first
        if self.unless and context.get(self.unless, False):
            return False

        # No condition means always active
        if not self.when:
            return True

        # Simple condition evaluation: "field op value"
        return _eval_condition(self.when, context)

    def to_dict(self) -> dict:
        """Serialize to the same format the YAML parser expects.

        The YAML format uses the action type as the key:
            - permit: read
            - forbid: delete_records
        So to_dict() must match that, not {"action": "permit", "target": "read"}.
        """
        d = {self.action.value: self.target}
        if self.when:
            d["when"] = self.when
        if self.unless:
            d["unless"] = self.unless
        if self.category:
            d["category"] = self.category
        return d


@dataclass
class Covenant:
    """A complete policy declaration for an agent.

    The covenant hash is a SHA-256 of the canonical JSON representation,
    ensuring any rule change produces a different hash. This hash is
    included in every ActionReceipt.
    """
    agent: str
    version: str = "1.0"
    rules: list[Rule] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_yaml(cls, path: str) -> "Covenant":
        """Load a covenant from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)

    @classmethod
    def from_yaml_string(cls, content: str) -> "Covenant":
        """Load a covenant from a YAML string."""
        data = yaml.safe_load(content)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Covenant":
        """Parse a covenant dict into a Covenant object."""
        rules = []
        for r in data.get("rules", []):
            # Each rule has exactly one of: permit, forbid, require_approval
            for action_type in RuleAction:
                if action_type.value in r:
                    rules.append(Rule(
                        action=action_type,
                        target=r[action_type.value],
                        when=r.get("when"),
                        unless=r.get("unless"),
                        category=r.get("category"),
                    ))
                    break

        return cls(
            agent=data.get("agent", "unknown"),
            version=str(data.get("version", "1.0")),
            rules=rules,
            description=data.get("description", ""),
        )

    def evaluate(self, action_name: str, context: dict = None) -> RuleAction:
        """Evaluate what to do for a given action.

        Precedence: forbid > require_approval > permit > default(forbid)

        Args:
            action_name: The action being attempted
            context: Runtime context for condition evaluation

        Returns:
            The RuleAction to take (permit, forbid, or require_approval)
        """
        context = context or {}
        matched_rules = []

        for rule in self.rules:
            if rule.matches(action_name, context):
                if rule.evaluate_condition(context):
                    matched_rules.append(rule)

        if not matched_rules:
            # Default deny — if no rule matches, forbid
            return RuleAction.FORBID

        # Forbid wins over everything
        if any(r.action == RuleAction.FORBID for r in matched_rules):
            return RuleAction.FORBID

        # Require approval wins over permit
        if any(r.action == RuleAction.REQUIRE_APPROVAL for r in matched_rules):
            return RuleAction.REQUIRE_APPROVAL

        return RuleAction.PERMIT

    @property
    def hash(self) -> str:
        """SHA-256 hash of the canonical covenant representation.

        This hash is included in every receipt to prove which rules
        were active at authorization time.
        """
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "version": self.version,
            "description": self.description,
            "rules": [r.to_dict() for r in self.rules],
        }

    def to_yaml(self) -> str:
        """Serialize the covenant to YAML."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


def _eval_condition(condition: str, context: dict) -> bool:
    """Evaluate a simple condition string against context.

    Supports: "field > value", "field < value", "field >= value",
    "field <= value", "field == value", "field != value"

    Args:
        condition: e.g. "amount > 50000"
        context: e.g. {"amount": 75000}

    Returns:
        True if the condition is met.
    """
    import re

    # Parse "field op value"
    match = re.match(r"(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)", condition.strip())
    if not match:
        return True  # Unparseable conditions default to active

    field_name, op, raw_value = match.groups()
    raw_value = raw_value.strip().strip('"').strip("'")

    ctx_value = context.get(field_name)
    if ctx_value is None:
        return False  # Missing context field = condition not met

    # Try numeric comparison
    try:
        ctx_num = float(ctx_value)
        val_num = float(raw_value)
        ops = {">": ctx_num > val_num, "<": ctx_num < val_num,
               ">=": ctx_num >= val_num, "<=": ctx_num <= val_num,
               "==": ctx_num == val_num, "!=": ctx_num != val_num}
        return ops.get(op, True)
    except (ValueError, TypeError):
        pass

    # String comparison
    ctx_str = str(ctx_value)
    ops = {"==": ctx_str == raw_value, "!=": ctx_str != raw_value}
    return ops.get(op, True)
