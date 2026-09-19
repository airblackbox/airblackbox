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


# --- #57 residuals: authenticity anchoring for keys ------------------------

def test_verify_receipt_rejects_untrusted_key():
    # An attacker's self-signed receipt verifies for consistency, but must be
    # rejected once we require a specific expected/trusted key.
    from air_blackbox.gate.receipt import ActionReceipt, ReceiptSigner, verify_receipt
    attacker = ReceiptSigner(private_key=os.urandom(32))
    receipt = ActionReceipt(agent_id="evil", action_name="delete_all",
                            authorized=True, decision="permit")
    attacker.sign_authorization(receipt)   # mutates in place
    d = receipt.to_dict()
    # No expected key: passes (self-consistent).
    assert verify_receipt(d)[0] is True
    # Wrong expected key: rejected on authenticity.
    ok, detail = verify_receipt(d, expected_public_key="00" * 32)
    assert ok is False and "authenticity" in detail
    # Correct expected key: passes.
    assert verify_receipt(d, expected_public_key=d["signing_public_key"])[0] is True


def test_verify_chain_reports_key_source(tmp_path, monkeypatch):
    from air_blackbox.replay.engine import ReplayEngine
    monkeypatch.delenv("TRUST_SIGNING_KEY", raising=False)
    eng = ReplayEngine(runs_dir=str(tmp_path))
    eng.load()
    assert eng.verify_chain(signing_key="k").key_source == "argument"
    monkeypatch.setenv("TRUST_SIGNING_KEY", "envk")
    assert eng.verify_chain().key_source == "env"


class TestRecruitingScreenerTagging:
    """Tagging must not fall through to default-deny.

    The covenant is default-deny, so an action with no rule is forbidden. The
    recruiting-screener covenant shipped without any tagging rule, which meant
    a product recording `tag_candidate` got a BLOCKED verdict - the tagging
    feature worked, but the governed record of it did not.
    """

    def _covenant(self):
        from air_blackbox.gate.covenant import Covenant
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return Covenant.from_yaml(os.path.join(
            here, "air_blackbox", "gate", "examples",
            "recruiting-screener.covenant.yaml"))

    @pytest.mark.parametrize("action", ["tag_candidate", "auto_tag_candidate", "retag_bench"])
    def test_tagging_is_permitted(self, action):
        from air_blackbox.gate.covenant import RuleAction
        assert self._covenant().evaluate(action) == RuleAction.PERMIT

    @pytest.mark.parametrize("action", [
        "reject_candidate", "advance_candidate", "score_candidate", "rank_candidates",
    ])
    def test_outcome_decisions_still_need_a_human(self, action):
        """Tagging being free must not have loosened the decisions that matter."""
        from air_blackbox.gate.covenant import RuleAction
        assert self._covenant().evaluate(action) == RuleAction.REQUIRE_APPROVAL

    def test_protected_attribute_inference_still_forbidden(self):
        """A parser that emits age or nationality proxies stays banned
        whichever tagging name it runs under."""
        from air_blackbox.gate.covenant import RuleAction
        assert self._covenant().evaluate("infer_protected_attributes") == RuleAction.FORBID

    def test_unknown_action_still_denied(self):
        """The fix must not have turned the covenant permissive."""
        from air_blackbox.gate.covenant import RuleAction
        assert self._covenant().evaluate("exfiltrate_bench") == RuleAction.FORBID


class TestCovenantVocabularyKeepsGuards:
    """The agent-facing vocabulary must not flatten a conditional rule.

    `forbid: llm_call when tokens_total > 100000` rendered bare as
    `forbid: llm_call` sits beside `permit: llm_call`; since forbid outranks
    permit, an agent reading that concludes llm_call is banned outright.
    """

    def test_guard_is_rendered(self):
        from air_blackbox.gate.covenant import Covenant
        from air_blackbox.mcp_server import _covenant_vocabulary
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cov = Covenant.from_yaml(os.path.join(
            here, "air_blackbox", "gate", "examples",
            "recruiting-screener.covenant.yaml"))
        text = _covenant_vocabulary(cov)
        assert "llm_call (only when tokens_total > 100000)" in text
        forbid_line = next(l for l in text.splitlines() if l.strip().startswith("forbid:"))
        assert "llm_call (only when" in forbid_line
