"""
Covenant - declarative policy DSL for AI agent behavior.

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

Loading is strict: an unknown key, a rule with no action or two, a
non-string target or a condition that does not read as "field op value"
raises CovenantError naming the rule, rather than loading a policy that
says something other than what was written (a misspelled "wehn:" used to
turn a guarded permit into an unconditional one).
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import yaml


class CovenantError(ValueError):
    """A covenant that cannot be loaded as written."""


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

    def condition_state(self, context: dict = None):
        """Tri-state activation of this rule's 'when'/'unless' guard.

        Returns True (guard satisfied), False (definitively not satisfied),
        or None (indeterminate - the guard could not be meaningfully
        evaluated). evaluate() resolves None fail-closed per the rule's
        action, so a missing or garbled guard can never silently open the
        gate or silently drop a forbid.
        """
        context = context or {}

        # 'unless' exception is an explicit, definitive deactivation.
        if self.unless and context.get(self.unless, False):
            return False

        # No condition means always active.
        if not self.when:
            return True

        return _eval_condition(self.when, context)

    def evaluate_condition(self, context: dict = None) -> bool:
        """Back-compat boolean: active only when the guard is definitively
        satisfied. Indeterminate (None) is treated as NOT active. Callers that
        need fail-closed forbid semantics use condition_state() via evaluate().
        """
        return self.condition_state(context) is True

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
        """Load a covenant from a YAML file. Raises CovenantError."""
        with open(path) as f:
            return cls.from_yaml_string(f.read())

    @classmethod
    def from_yaml_string(cls, content: str) -> "Covenant":
        """Load a covenant from a YAML string. Raises CovenantError."""
        try:
            data = yaml.load(content, Loader=_UniqueKeyLoader)
        except yaml.YAMLError as e:
            raise CovenantError(f"not valid YAML: {e}") from None
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Covenant":
        """Parse a covenant dict into a Covenant object. Raises CovenantError."""
        validate_covenant(data)
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

        uncertain_approval = False
        for rule in self.rules:
            if not rule.matches(action_name, context):
                continue
            state = rule.condition_state(context)
            if rule.action == RuleAction.FORBID:
                # Fail closed: a forbid applies unless its guard is
                # definitively False. An indeterminate guard (missing field,
                # non-numeric ordering, unparseable) keeps the forbid ACTIVE,
                # so it can't be disabled by omitting or garbling the field.
                if state is not False:
                    matched_rules.append(rule)
            elif state is True:
                matched_rules.append(rule)
            elif state is None and rule.action == RuleAction.REQUIRE_APPROVAL:
                uncertain_approval = True
            # An indeterminate permit never grants.

        if not matched_rules:
            # Default deny - if no rule matches, forbid. An approval rule
            # that might apply cannot lift this: it would only loosen it.
            return RuleAction.FORBID

        # Forbid wins over everything
        if any(r.action == RuleAction.FORBID for r in matched_rules):
            return RuleAction.FORBID

        # Require approval wins over permit. An approval rule whose guard
        # cannot be read counts here too: it can only make the decision
        # stricter, so "amount > 1000" with an unreadable amount turns a
        # permit into require_approval instead of letting it through.
        if uncertain_approval or any(
                r.action == RuleAction.REQUIRE_APPROVAL for r in matched_rules):
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


class _UniqueKeyLoader(yaml.SafeLoader):
    """safe_load, refusing a key repeated in one mapping (PyYAML otherwise
    keeps the last value silently, so a rule could carry two `when:`s)."""


def _construct_unique_mapping(loader, node, deep=False):
    keys = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in keys:
            raise CovenantError(
                f"duplicate key '{key}' at line {key_node.start_mark.line + 1}")
        keys.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)

_TOP_KEYS = ("agent", "version", "description", "rules")
_ACTIONS = ("permit", "forbid", "require_approval")
_RULE_KEYS = _ACTIONS + ("when", "unless", "category")
# As _eval_condition reads it, with the value starting at its first
# non-space character (so the space and value patterns cannot overlap).
_CONDITION = re.compile(r"(\w+)\s*(>=|<=|!=|==|>|<)\s*(\S.*)")
_DOTTED = re.compile(r"\w+(?:\.\w+)+\s*(?:>=|<=|!=|==|>|<)")
_FIELD = re.compile(r"\w+")


def validate_covenant(data) -> None:
    """Raise CovenantError unless `data` is a covenant as the YAML format
    defines it. The TypeScript package applies the same checks with the same
    messages, so a file one SDK refuses the other refuses too."""
    if not isinstance(data, dict):
        raise CovenantError("a covenant must be a YAML mapping with agent and rules")
    for key in data:
        if key not in _TOP_KEYS:
            raise CovenantError(f"unknown top-level key '{key}' "
                                f"(allowed: {', '.join(_TOP_KEYS)})")
    rules = data.get("rules", [])
    if rules is None:
        rules = []
    if not isinstance(rules, list):
        raise CovenantError("'rules' must be a list")
    for i, rule in enumerate(rules, start=1):
        where = f"rule {i}"
        if not isinstance(rule, dict):
            raise CovenantError(f"{where}: must be a mapping like '- permit: action_name'")
        for key in rule:
            if key not in _RULE_KEYS:
                raise CovenantError(f"{where}: unknown key '{key}' "
                                    f"(allowed: {', '.join(_RULE_KEYS)})")
        actions = [a for a in _ACTIONS if a in rule]
        if not actions:
            raise CovenantError(f"{where}: needs one of {', '.join(_ACTIONS)}")
        if len(actions) > 1:
            raise CovenantError(f"{where}: has {' and '.join(actions)}; a rule "
                                "takes exactly one of permit, forbid, require_approval")
        target = rule[actions[0]]
        if not isinstance(target, str) or not target.strip():
            raise CovenantError(f"{where}: the {actions[0]} target must be a non-empty "
                                "string (quote it if YAML would read it as a "
                                "number or yes/no)")
        if "when" in rule:
            _validate_condition(where, rule["when"])
        if "unless" in rule:
            unless = rule["unless"]
            if not isinstance(unless, str) or not _FIELD.fullmatch(unless):
                raise CovenantError(f"{where}: 'unless' must be a field name "
                                    "like human_approved")
        if "category" in rule:
            category = rule["category"]
            if not isinstance(category, str) or not category.strip():
                raise CovenantError(f"{where}: 'category' must be a non-empty string")


def _validate_condition(where: str, when) -> None:
    if not isinstance(when, str):
        raise CovenantError(f"{where}: 'when' must be a string like \"amount > 100\"")
    text = when.strip()
    if _DOTTED.match(text):
        raise CovenantError(f"{where}: 'when: {text}' reads a nested field; "
                            "conditions read top-level fields only")
    match = None if "\n" in text else _CONDITION.fullmatch(text)
    if not match:
        raise CovenantError(f"{where}: cannot read 'when: {text}'; write it as "
                            "field op value, e.g. amount > 100")
    _, op, value = match.groups()
    value = value.strip().strip('"').strip("'")
    if op in (">", "<", ">=", "<="):
        try:
            float(value)
        except ValueError:
            raise CovenantError(f"{where}: 'when: {text}' orders against "
                                f"'{value}', which is not a number") from None


def _eval_condition(condition: str, context: dict):
    """Evaluate a "field op value" condition to a tri-state.

    Supports: "field > value", "field < value", "field >= value",
    "field <= value", "field == value", "field != value"

    Returns:
        True / False for a definitive comparison, or None when the condition
        is indeterminate (unparseable, unknown field, or an ordering
        comparison on a non-numeric value). Callers MUST resolve None fail
        closed - see Covenant.evaluate().
    """
    import re

    # Parse "field op value"
    match = re.match(r"(\w+)\s*(>=|<=|!=|==|>|<)\s*(.+)", condition.strip())
    if not match:
        return None  # Unparseable: indeterminate, never silently "active"

    field_name, op, raw_value = match.groups()
    raw_value = raw_value.strip().strip('"').strip("'")

    ctx_value = context.get(field_name)
    if ctx_value is None:
        return None  # Unknown field: indeterminate

    # Numeric comparison when both sides are numbers.
    try:
        ctx_num = float(ctx_value)
        val_num = float(raw_value)
        return {">": ctx_num > val_num, "<": ctx_num < val_num,
                ">=": ctx_num >= val_num, "<=": ctx_num <= val_num,
                "==": ctx_num == val_num, "!=": ctx_num != val_num}[op]
    except (ValueError, TypeError):
        pass

    # Non-numeric: only equality/inequality are meaningful. An ordering
    # operator on a non-numeric value (e.g. "amount <= 1000" with
    # amount="1,000,000") is indeterminate, NOT true.
    ctx_str = str(ctx_value)
    if op == "==":
        return ctx_str == raw_value
    if op == "!=":
        return ctx_str != raw_value
    return None
