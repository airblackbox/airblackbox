"""Covenant fail-closed evaluation and Gate hardening (issue #58).

The covenant DSL previously resolved ambiguity toward *allow*: an ordering
comparison on a non-numeric value, a forbid whose field was missing, and an
unparseable guard all defaulted to granting. A policy layer must fail closed.
"""

import os

import pytest

from air_blackbox.gate.covenant import Covenant, Rule, RuleAction


def _permit(target, when=None):
    return Covenant(agent="t", version="1",
                    rules=[Rule(action=RuleAction.PERMIT, target=target, when=when)])


def test_ordering_op_on_non_numeric_denies():
    # "amount <= 1000" must not PERMIT when amount can't be compared numerically.
    cov = _permit("wire_transfer", when="amount <= 1000")
    assert cov.evaluate("wire_transfer", {"amount": 500}) == RuleAction.PERMIT
    for bad in ("1,000,000", [10**9], "lots", {"x": 1}):
        assert cov.evaluate("wire_transfer", {"amount": bad}) == RuleAction.FORBID, bad


def test_numeric_boundaries_still_correct():
    cov = _permit("a", when="amount > 50000")
    assert cov.evaluate("a", {"amount": 50000}) == RuleAction.FORBID   # not strictly >
    assert cov.evaluate("a", {"amount": 50001}) == RuleAction.PERMIT
    assert cov.evaluate("a", {"amount": -5}) == RuleAction.FORBID


def test_forbid_with_missing_field_stays_active():
    # Omitting the guarded field must NOT drop a forbid (fail closed).
    cov = Covenant(agent="t", version="1", rules=[
        Rule(action=RuleAction.PERMIT, target="*"),
        Rule(action=RuleAction.FORBID, target="wire_transfer", when="amount > 0")])
    assert cov.evaluate("wire_transfer", {"amount": 5}) == RuleAction.FORBID
    assert cov.evaluate("wire_transfer", {}) == RuleAction.FORBID          # field missing
    assert cov.evaluate("wire_transfer", {"amount": "N/A"}) == RuleAction.FORBID


def test_unparseable_guard_denies_for_permit():
    cov = _permit("act", when="garbage no operator here")
    assert cov.evaluate("act", {}) == RuleAction.FORBID


def test_permit_without_guard_still_permits():
    # No regression to the normal path.
    assert _permit("act").evaluate("act", {}) == RuleAction.PERMIT
    assert _permit("act").evaluate("other", {}) == RuleAction.FORBID  # default deny


# --- Gate engine hardening ------------------------------------------------

def _gate():
    from air_blackbox.gate.engine import Gate
    cov = _permit("*")
    return Gate(covenant=cov, signing_key=os.urandom(32))


def test_walk_delegation_chain_survives_a_cycle():
    import signal
    g = _gate()
    r = g.authorize("a", "act", payload={})
    r.parent_receipt_id = r.receipt_id      # self-referential loop
    g._receipts[r.receipt_id] = r
    signal.alarm(3)
    try:
        chain = g.walk_delegation_chain(r)
    finally:
        signal.alarm(0)
    assert chain  # returned instead of hanging


def test_verify_surfaces_the_decision_not_just_signatures():
    g = _gate()
    r = g.authorize("a", "act", payload={})
    v = g.verify(r)
    # A valid signature on a receipt is not the same as "the action was allowed".
    assert "authorized" in v and "decision" in v
    assert v["authorized"] is r.authorized
    assert v["decision"] == r.decision
