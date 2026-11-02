"""Covenant loading is strict, and an unreadable approval guard fails closed.

Before, mistakes loaded silently: a misspelled `wehn:` dropped the guard and
left an unconditional permit; a rule with both forbid and permit became a
permit; `amount >> 5` or `order.amount > 5` loaded and could never be true.
The TypeScript package refuses the same files with the same messages
(js/src/test/covenant.test.ts checks the two against each other).
"""

import glob
import os

import pytest

from air_blackbox.gate.covenant import Covenant, CovenantError, RuleAction

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "air_blackbox", "gate", "examples")

REFUSED = [
    ("agent: a\nrules:\n  - permit: x\n    wehn: \"amount > 1\"\n",
     "rule 1: unknown key 'wehn' (allowed: permit, forbid, require_approval, when, unless, category)"),
    ("agent: a\nrules:\n  - permit: y\n  - forbid: x\n    permit: x\n",
     "rule 2: has permit and forbid; a rule takes exactly one of permit, forbid, require_approval"),
    ("agent: a\nrules:\n  - when: \"a > 1\"\n",
     "rule 1: needs one of permit, forbid, require_approval"),
    ("agent: a\nrules:\n  - permit: x\n    when: amount >> 5\n",
     "rule 1: 'when: amount >> 5' orders against '> 5', which is not a number"),
    ("agent: a\nrules:\n  - permit: x\n    when: order.amount > 5\n",
     "rule 1: 'when: order.amount > 5' reads a nested field; conditions read top-level fields only"),
    ("agent: a\nrules:\n  - permit: x\n    when: amount is big\n",
     "rule 1: cannot read 'when: amount is big'; write it as field op value, e.g. amount > 100"),
    ("agent: a\nrules:\n  - permit: x\n    when: 5\n",
     "rule 1: 'when' must be a string like \"amount > 100\""),
    ("agent: a\nrules:\n  - permit: on\n",
     "rule 1: the permit target must be a non-empty string (quote it if YAML would read it as a number or yes/no)"),
    ("agent: a\nrules:\n  - forbid: 1.5\n",
     "rule 1: the forbid target must be a non-empty string (quote it if YAML would read it as a number or yes/no)"),
    ("agent: a\nrules:\n  - permit:\n",
     "rule 1: the permit target must be a non-empty string (quote it if YAML would read it as a number or yes/no)"),
    ("agent: a\nrules:\n  - forbid: x\n    unless: human approved\n",
     "rule 1: 'unless' must be a field name like human_approved"),
    ("agent: a\nrules:\n  - permit: x\n    category: 2\n",
     "rule 1: 'category' must be a non-empty string"),
    ("agent: a\nrules:\n  - just_a_string\n",
     "rule 1: must be a mapping like '- permit: action_name'"),
    ("agent: a\nrules:\n  permit: x\n",
     "'rules' must be a list"),
    ("agent: a\nowner: me\nrules: []\n",
     "unknown top-level key 'owner' (allowed: agent, version, description, rules)"),
    ("", "a covenant must be a YAML mapping with agent and rules"),
    ("- permit: x\n", "a covenant must be a YAML mapping with agent and rules"),
]


@pytest.mark.parametrize("yaml_text,message", REFUSED)
def test_malformed_covenants_are_refused_with_the_rule_named(yaml_text, message):
    with pytest.raises(CovenantError) as e:
        Covenant.from_yaml_string(yaml_text)
    assert str(e.value) == message


def test_a_key_repeated_in_one_mapping_is_refused():
    with pytest.raises(CovenantError, match="duplicate key 'when'"):
        Covenant.from_yaml_string("agent: a\nrules:\n  - permit: x\n    when: a > 1\n    when: a > 2\n")


def test_invalid_yaml_is_a_covenant_error():
    with pytest.raises(CovenantError, match="not valid YAML"):
        Covenant.from_yaml_string("agent: [unclosed\n")


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(EXAMPLES, "*.yaml"))))
def test_the_shipped_examples_load(path):
    assert Covenant.from_yaml(path).rules


def test_valid_corners_still_load():
    c = Covenant.from_yaml_string(
        "agent: a\nversion: 1.0\ndescription: d\nrules:\n"
        "  - permit: '*'\n"
        "  - forbid: send_email\n    unless: human_approved\n"
        "  - require_approval: pay\n    when: \"amount > 1e3\"\n"
        "  - forbid: tag\n    when: \"vocab != controlled\"\n"
        "  - permit: read\n    category: read_only\n")
    assert len(c.rules) == 5
    assert Covenant.from_yaml_string("agent: a\n").evaluate("x") == RuleAction.FORBID


GUARDED_PERMIT = """agent: a
rules:
  - permit: issue_refund
  - require_approval: issue_refund
    when: "amount > 1000"
"""


@pytest.mark.parametrize("ctx,want", [
    ({"amount": 5000}, RuleAction.REQUIRE_APPROVAL),
    ({"amount": 500}, RuleAction.PERMIT),
    # Unreadable amounts used to leave only the permit.
    ({"amount": "$5,000"}, RuleAction.REQUIRE_APPROVAL),
    ({}, RuleAction.REQUIRE_APPROVAL),
])
def test_an_unreadable_approval_guard_still_requires_approval(ctx, want):
    assert Covenant.from_yaml_string(GUARDED_PERMIT).evaluate("issue_refund", ctx) == want


def test_an_unreadable_approval_guard_never_loosens_a_forbid():
    """It can only make a decision stricter: with no permit, the default
    forbid stands rather than becoming require_approval."""
    only_approval = Covenant.from_yaml_string(
        "agent: a\nrules:\n  - require_approval: pay\n    when: \"amount > 1000\"\n")
    assert only_approval.evaluate("pay", {}) == RuleAction.FORBID
    assert only_approval.evaluate("pay", {"amount": 5000}) == RuleAction.REQUIRE_APPROVAL
    both_guarded = Covenant.from_yaml_string(
        "agent: a\nrules:\n  - permit: pay\n    when: \"amount <= 1000\"\n"
        "  - require_approval: pay\n    when: \"amount > 1000\"\n")
    assert both_guarded.evaluate("pay", {"amount": "$5,000"}) == RuleAction.FORBID
    forbidden = Covenant.from_yaml_string(
        "agent: a\nrules:\n  - permit: pay\n  - forbid: pay\n    when: \"amount > 9000\"\n"
        "  - require_approval: pay\n    when: \"amount > 1000\"\n")
    assert forbidden.evaluate("pay", {}) == RuleAction.FORBID
