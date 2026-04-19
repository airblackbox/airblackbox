"""
Comprehensive stress tests for the bilateral receipt system.
Tests: covenant parsing, rule evaluation, receipt signing, verification,
delegation chains, edge cases, and adversarial scenarios.
"""

import json
import os
import shutil
import tempfile
import time
import traceback

# Track results
PASSED = 0
FAILED = 0
ERRORS = []


def test(name):
    """Decorator to run and report test results."""
    def decorator(fn):
        def wrapper():
            global PASSED, FAILED
            try:
                fn()
                PASSED += 1
                print(f"  ✓ {name}")
            except AssertionError as e:
                FAILED += 1
                ERRORS.append((name, str(e)))
                print(f"  ✗ {name}: {e}")
            except Exception as e:
                FAILED += 1
                ERRORS.append((name, f"{type(e).__name__}: {e}"))
                print(f"  ✗ {name}: {type(e).__name__}: {e}")
                traceback.print_exc()
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


# ============================================================
# 1. COVENANT TESTS
# ============================================================
print("\n=== COVENANT TESTS ===")

from air_blackbox.gate.covenant import Covenant, Rule, RuleAction, _eval_condition


@test("Covenant from YAML string — basic parsing")
def _():
    c = Covenant.from_yaml_string("""
agent: test-agent
version: "1.0"
rules:
  - permit: read_data
  - forbid: delete_data
  - require_approval: send_email
""")
    assert c.agent == "test-agent"
    assert c.version == "1.0"
    assert len(c.rules) == 3
    assert c.rules[0].action == RuleAction.PERMIT
    assert c.rules[0].target == "read_data"
    assert c.rules[1].action == RuleAction.FORBID
    assert c.rules[1].target == "delete_data"
    assert c.rules[2].action == RuleAction.REQUIRE_APPROVAL
    assert c.rules[2].target == "send_email"
_()


@test("Covenant with conditions — when/unless parsing")
def _():
    c = Covenant.from_yaml_string("""
agent: loan-bot
version: "2.0"
rules:
  - permit: approve_loan
    when: "amount <= 50000"
  - require_approval: approve_loan
    when: "amount > 50000"
  - forbid: send_email
    unless: human_approved
""")
    assert c.rules[0].when == "amount <= 50000"
    assert c.rules[1].when == "amount > 50000"
    assert c.rules[2].unless == "human_approved"
_()


@test("Covenant hash changes when rules change")
def _():
    c1 = Covenant.from_yaml_string("""
agent: a
version: "1.0"
rules:
  - permit: read
""")
    c2 = Covenant.from_yaml_string("""
agent: a
version: "1.0"
rules:
  - permit: read
  - forbid: write
""")
    assert c1.hash != c2.hash, "Different rules should produce different hashes"
_()


@test("Covenant hash is deterministic")
def _():
    yaml_str = """
agent: deterministic
version: "1.0"
rules:
  - permit: action_a
  - forbid: action_b
"""
    c1 = Covenant.from_yaml_string(yaml_str)
    c2 = Covenant.from_yaml_string(yaml_str)
    assert c1.hash == c2.hash, "Same rules should produce same hash"
_()


@test("Covenant evaluate — permit wins when matched")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: read_data
""")
    assert c.evaluate("read_data") == RuleAction.PERMIT
_()


@test("Covenant evaluate — default deny for unmatched actions")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: read_data
""")
    assert c.evaluate("delete_data") == RuleAction.FORBID
_()


@test("Covenant evaluate — forbid wins over permit")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: send_email
  - forbid: send_email
""")
    assert c.evaluate("send_email") == RuleAction.FORBID
_()


@test("Covenant evaluate — require_approval wins over permit")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: transfer_funds
  - require_approval: transfer_funds
""")
    assert c.evaluate("transfer_funds") == RuleAction.REQUIRE_APPROVAL
_()


@test("Covenant evaluate — condition 'when' numeric greater than")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: approve_loan
    when: "amount <= 50000"
  - require_approval: approve_loan
    when: "amount > 50000"
""")
    # Small loan — should be permitted
    assert c.evaluate("approve_loan", {"amount": 30000}) == RuleAction.PERMIT
    # Large loan — should require approval
    assert c.evaluate("approve_loan", {"amount": 75000}) == RuleAction.REQUIRE_APPROVAL
_()


@test("Covenant evaluate — 'unless' exception overrides rule")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - forbid: send_email
    unless: human_approved
  - permit: send_email
""")
    # Without human approval: forbid matches, should be forbidden
    assert c.evaluate("send_email", {}) == RuleAction.FORBID
    # With human approval: forbid's unless kicks in, forbid doesn't match, permit wins
    assert c.evaluate("send_email", {"human_approved": True}) == RuleAction.PERMIT
_()


@test("Covenant evaluate — wildcard rule")
def _():
    c = Covenant.from_yaml_string("""
agent: test
version: "1.0"
rules:
  - permit: "*"
  - forbid: delete_everything
""")
    assert c.evaluate("anything_goes") == RuleAction.PERMIT
    assert c.evaluate("delete_everything") == RuleAction.FORBID
_()


@test("Covenant to_yaml roundtrip")
def _():
    c1 = Covenant.from_yaml_string("""
agent: roundtrip
version: "1.0"
rules:
  - permit: read
  - forbid: write
    when: "level > 5"
""")
    yaml_out = c1.to_yaml()
    c2 = Covenant.from_yaml_string(yaml_out)
    assert c1.hash == c2.hash, f"Roundtrip should preserve hash: {c1.hash} != {c2.hash}"
_()


@test("Condition eval — all operators")
def _():
    assert _eval_condition("x > 5", {"x": 10}) == True
    assert _eval_condition("x > 5", {"x": 3}) == False
    assert _eval_condition("x < 5", {"x": 3}) == True
    assert _eval_condition("x >= 5", {"x": 5}) == True
    assert _eval_condition("x <= 5", {"x": 5}) == True
    assert _eval_condition("x == 5", {"x": 5}) == True
    assert _eval_condition("x != 5", {"x": 3}) == True
    assert _eval_condition("x != 5", {"x": 5}) == False
_()


@test("Condition eval — missing field returns False")
def _():
    assert _eval_condition("x > 5", {}) == False
_()


@test("Condition eval — string comparison")
def _():
    assert _eval_condition("status == active", {"status": "active"}) == True
    assert _eval_condition("status != active", {"status": "inactive"}) == True
_()


@test("Empty covenant — all actions forbidden by default")
def _():
    c = Covenant.from_yaml_string("""
agent: empty
version: "1.0"
rules: []
""")
    assert c.evaluate("anything") == RuleAction.FORBID
_()


# ============================================================
# 2. RECEIPT TESTS
# ============================================================
print("\n=== RECEIPT TESTS ===")

from air_blackbox.gate.receipt import (
    ActionReceipt, ReceiptStatus, ReceiptSigner,
    hash_payload, hash_result, HAS_ED25519,
)


@test(f"Signing method: {'Ed25519' if HAS_ED25519 else 'HMAC-SHA256 fallback'}")
def _():
    signer = ReceiptSigner()
    if HAS_ED25519:
        assert signer.method == "ed25519"
        assert signer.public_key_hex is not None
        assert len(signer.public_key_hex) == 64  # 32 bytes = 64 hex chars
    else:
        assert signer.method == "hmac-sha256"
_()


@test("Receipt creation — auto-generates ID and timestamp")
def _():
    r = ActionReceipt(agent_id="test", action_name="read")
    assert r.receipt_id != ""
    assert r.created_at != ""
    assert r.created_at.endswith("Z")
_()


@test("hash_payload — deterministic")
def _():
    h1 = hash_payload({"to": "jane@example.com", "amount": 500})
    h2 = hash_payload({"amount": 500, "to": "jane@example.com"})
    assert h1 == h2, "sort_keys should make hash order-independent"
_()


@test("hash_payload — different payloads produce different hashes")
def _():
    h1 = hash_payload({"to": "jane@example.com"})
    h2 = hash_payload({"to": "bob@example.com"})
    assert h1 != h2
_()


@test("Receipt sign and verify — authorization phase")
def _():
    signer = ReceiptSigner()
    r = ActionReceipt(
        agent_id="agent-1",
        action_name="send_email",
        payload_hash=hash_payload({"to": "test@test.com"}),
        covenant_hash="abc123",
        decision="permit",
        authorized=True,
    )
    signer.sign_authorization(r)
    assert r.authorization_sig != ""
    assert signer.verify_authorization(r) == True
_()


@test("Receipt sign and verify — tampered authorization fails")
def _():
    signer = ReceiptSigner()
    r = ActionReceipt(
        agent_id="agent-1",
        action_name="send_email",
        covenant_hash="abc123",
        decision="permit",
        authorized=True,
    )
    signer.sign_authorization(r)
    # Tamper with the receipt
    r.authorized = False
    assert signer.verify_authorization(r) == False, "Tampered receipt should fail verification"
_()


@test("Receipt sign and verify — full lifecycle (authorize + seal)")
def _():
    signer = ReceiptSigner()
    r = ActionReceipt(
        agent_id="agent-1",
        action_name="process",
        covenant_hash="abc",
        decision="permit",
        authorized=True,
    )
    signer.sign_authorization(r)

    # Seal
    r.result_hash = hash_result({"status": "done"})
    r.result_status = "success"
    r.sealed_at = "2026-04-17T12:00:00Z"
    signer.sign_seal(r)

    auth_ok, seal_ok = signer.verify_full(r)
    assert auth_ok == True
    assert seal_ok == True
_()


@test("Receipt sign and verify — tampered result fails seal")
def _():
    signer = ReceiptSigner()
    r = ActionReceipt(
        agent_id="agent-1",
        action_name="process",
        covenant_hash="abc",
        decision="permit",
        authorized=True,
    )
    signer.sign_authorization(r)
    r.result_hash = hash_result({"status": "done"})
    r.result_status = "success"
    r.sealed_at = "2026-04-17T12:00:00Z"
    signer.sign_seal(r)

    # Tamper with result
    r.result_hash = hash_result({"status": "TAMPERED"})
    assert signer.verify_seal(r) == False
_()


@test("Receipt to_dict and to_json — serialization")
def _():
    r = ActionReceipt(
        agent_id="test",
        action_name="read",
        decision="permit",
        authorized=True,
    )
    d = r.to_dict()
    assert d["agent_id"] == "test"
    assert d["action_name"] == "read"
    assert d["status"] == "authorized"

    j = r.to_json()
    parsed = json.loads(j)
    assert parsed["agent_id"] == "test"
_()


@test("Different signers produce different signatures")
def _():
    s1 = ReceiptSigner()
    s2 = ReceiptSigner()
    r = ActionReceipt(
        agent_id="test",
        action_name="read",
        covenant_hash="abc",
        decision="permit",
        authorized=True,
    )
    sig1 = s1.sign(r.authorization_payload)
    sig2 = s2.sign(r.authorization_payload)
    if HAS_ED25519:
        assert sig1 != sig2, "Different keys should produce different sigs"
_()


# ============================================================
# 3. GATE ENGINE TESTS
# ============================================================
print("\n=== GATE ENGINE TESTS ===")

from air_blackbox.gate.engine import Gate


def make_gate(yaml_str, tmpdir=None, **kwargs):
    """Helper to create a gate with a temp dir."""
    covenant = Covenant.from_yaml_string(yaml_str)
    runs_dir = tmpdir or tempfile.mkdtemp()
    return Gate(covenant=covenant, runs_dir=runs_dir, **kwargs), runs_dir


@test("Gate authorize — permitted action")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: read_data
""")
    receipt = gate.authorize("agent-1", "read_data")
    assert receipt.authorized == True
    assert receipt.decision == "permit"
    assert receipt.status == ReceiptStatus.AUTHORIZED
    assert receipt.authorization_sig != ""
    assert receipt.covenant_hash == gate.covenant.hash
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — forbidden action")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - forbid: delete_all
""")
    receipt = gate.authorize("agent-1", "delete_all")
    assert receipt.authorized == False
    assert receipt.decision == "forbid"
    assert receipt.status == ReceiptStatus.DENIED
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — unmatched action defaults to deny")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: read
""")
    receipt = gate.authorize("agent-1", "unknown_action")
    assert receipt.authorized == False
    assert receipt.decision == "forbid"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — require_approval with callback")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - require_approval: sensitive_action
""", on_approval_needed=lambda r: True)
    receipt = gate.authorize("agent-1", "sensitive_action")
    assert receipt.authorized == True
    assert receipt.decision == "require_approval"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — require_approval rejected by callback")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - require_approval: sensitive_action
""", on_approval_needed=lambda r: False)
    receipt = gate.authorize("agent-1", "sensitive_action")
    assert receipt.authorized == False
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — require_approval with no callback defaults to deny")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - require_approval: sensitive_action
""")
    receipt = gate.authorize("agent-1", "sensitive_action")
    assert receipt.authorized == False
    assert receipt.status == ReceiptStatus.DENIED
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — payload hash is computed correctly")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: send
""")
    payload = {"to": "jane@example.com", "amount": 500}
    receipt = gate.authorize("agent-1", "send", payload=payload)
    assert receipt.payload_hash == hash_payload(payload)
    assert receipt.payload_hash != ""
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate authorize — condition evaluation with context")
def _():
    gate, tmpdir = make_gate("""
agent: loan-bot
version: "1.0"
rules:
  - permit: approve_loan
    when: "amount <= 50000"
  - require_approval: approve_loan
    when: "amount > 50000"
""", on_approval_needed=lambda r: True)
    # Small loan
    r1 = gate.authorize("agent-1", "approve_loan", context={"amount": 30000})
    assert r1.authorized == True
    assert r1.decision == "permit"
    # Large loan — needs approval (callback returns True)
    r2 = gate.authorize("agent-1", "approve_loan", context={"amount": 75000})
    assert r2.authorized == True
    assert r2.decision == "require_approval"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate seal — full authorize + execute + seal lifecycle")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: process
""")
    receipt = gate.authorize("agent-1", "process", payload={"input": "data"})
    assert receipt.authorized == True
    assert receipt.seal_sig == ""

    # Seal with result
    result = {"output": "processed", "score": 0.95}
    gate.seal(receipt, result=result, status="success")

    assert receipt.status == ReceiptStatus.SEALED
    assert receipt.result_hash != ""
    assert receipt.result_status == "success"
    assert receipt.seal_sig != ""
    assert receipt.sealed_at != ""
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate seal — failed execution")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: risky_op
""")
    receipt = gate.authorize("agent-1", "risky_op")
    gate.seal(receipt, result={"error": "timeout"}, status="failure")
    assert receipt.status == ReceiptStatus.FAILED
    assert receipt.result_status == "failure"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate verify — full lifecycle verification")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: action
""")
    receipt = gate.authorize("agent-1", "action")
    gate.seal(receipt, result={"ok": True}, status="success")

    report = gate.verify(receipt)
    assert report["authorization_valid"] == True
    assert report["seal_valid"] == True
    assert report["is_sealed"] == True
    assert report["overall"] == True
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Gate verify — tampered receipt detected")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: action
""")
    receipt = gate.authorize("agent-1", "action")
    gate.seal(receipt, result={"ok": True}, status="success")

    # Tamper
    receipt.action_name = "TAMPERED_action"
    report = gate.verify(receipt)
    assert report["authorization_valid"] == False
    assert report["overall"] == False
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


# ============================================================
# 4. DELEGATION CHAIN TESTS
# ============================================================
print("\n=== DELEGATION CHAIN TESTS ===")


@test("Delegation chain — parent receipt linked")
def _():
    gate, tmpdir = make_gate("""
agent: multi
version: "1.0"
rules:
  - permit: orchestrate
  - permit: sub_task
""")
    parent = gate.authorize("orchestrator", "orchestrate")
    child = gate.authorize("worker", "sub_task", parent_receipt=parent)

    assert child.parent_receipt_id == parent.receipt_id
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Delegation chain — walk back to root")
def _():
    gate, tmpdir = make_gate("""
agent: chain
version: "1.0"
rules:
  - permit: step_1
  - permit: step_2
  - permit: step_3
""")
    r1 = gate.authorize("agent-a", "step_1")
    r2 = gate.authorize("agent-b", "step_2", parent_receipt=r1)
    r3 = gate.authorize("agent-c", "step_3", parent_receipt=r2)

    chain = gate.walk_delegation_chain(r3)
    assert len(chain) == 3
    assert chain[0].receipt_id == r1.receipt_id  # root first
    assert chain[1].receipt_id == r2.receipt_id
    assert chain[2].receipt_id == r3.receipt_id
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Delegation chain — each receipt independently verifiable")
def _():
    gate, tmpdir = make_gate("""
agent: chain
version: "1.0"
rules:
  - permit: a
  - permit: b
  - permit: c
""")
    r1 = gate.authorize("x", "a")
    r2 = gate.authorize("y", "b", parent_receipt=r1)
    r3 = gate.authorize("z", "c", parent_receipt=r2)

    for r in [r1, r2, r3]:
        gate.seal(r, result={"done": True}, status="success")
        report = gate.verify(r)
        assert report["overall"] == True, f"Receipt {r.receipt_id} failed verification"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


# ============================================================
# 5. PERSISTENCE TESTS
# ============================================================
print("\n=== PERSISTENCE TESTS ===")


@test("Receipts are persisted to disk")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: save_me
""")
    receipt = gate.authorize("agent-1", "save_me")

    # Check .receipt.json file exists
    receipt_path = os.path.join(tmpdir, f"{receipt.receipt_id}.receipt.json")
    assert os.path.exists(receipt_path), f"Receipt file not found at {receipt_path}"

    # Check it's valid JSON with correct content
    with open(receipt_path) as f:
        data = json.load(f)
    assert data["receipt_id"] == receipt.receipt_id
    assert data["agent_id"] == "agent-1"
    assert data["action_name"] == "save_me"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Audit chain records are persisted")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: logged
""")
    receipt = gate.authorize("agent-1", "logged")

    # Should have at least one .air.json file from the chain
    air_files = [f for f in os.listdir(tmpdir) if f.endswith(".air.json")]
    assert len(air_files) >= 1, f"Expected .air.json files, found: {os.listdir(tmpdir)}"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


# ============================================================
# 6. STRESS TESTS
# ============================================================
print("\n=== STRESS TESTS ===")


@test("Stress: 1000 authorizations in sequence")
def _():
    gate, tmpdir = make_gate("""
agent: stress
version: "1.0"
rules:
  - permit: action
""")
    start = time.time()
    for i in range(1000):
        r = gate.authorize(f"agent-{i}", "action", payload={"i": i})
        assert r.authorized == True
    elapsed = time.time() - start
    print(f"    → 1000 authorizations in {elapsed:.2f}s ({1000/elapsed:.0f}/sec)")
    assert gate.receipt_count == 1000
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Stress: 500 full lifecycles (authorize + seal + verify)")
def _():
    gate, tmpdir = make_gate("""
agent: stress
version: "1.0"
rules:
  - permit: full_cycle
""")
    start = time.time()
    for i in range(500):
        r = gate.authorize(f"agent-{i}", "full_cycle", payload={"i": i})
        gate.seal(r, result={"output": i}, status="success")
        report = gate.verify(r)
        assert report["overall"] == True, f"Iteration {i} failed"
    elapsed = time.time() - start
    print(f"    → 500 full lifecycles in {elapsed:.2f}s ({500/elapsed:.0f}/sec)")
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Stress: 100-deep delegation chain")
def _():
    gate, tmpdir = make_gate("""
agent: deep
version: "1.0"
rules:
  - permit: delegate
""")
    receipts = []
    parent = None
    for i in range(100):
        r = gate.authorize(f"agent-{i}", "delegate", parent_receipt=parent)
        assert r.authorized == True
        if parent:
            assert r.parent_receipt_id == parent.receipt_id
        receipts.append(r)
        parent = r

    # Walk the chain from the deepest receipt
    chain = gate.walk_delegation_chain(receipts[-1])
    assert len(chain) == 100, f"Expected 100, got {len(chain)}"
    assert chain[0].receipt_id == receipts[0].receipt_id  # root
    assert chain[-1].receipt_id == receipts[-1].receipt_id  # leaf
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Stress: covenant with 50 rules — evaluation still correct")
def _():
    rules_yaml = "\n".join([f"  - permit: action_{i}" for i in range(48)])
    rules_yaml += "\n  - forbid: blocked_action"
    rules_yaml += "\n  - require_approval: needs_approval"
    c = Covenant.from_yaml_string(f"""
agent: many-rules
version: "1.0"
rules:
{rules_yaml}
""")
    assert len(c.rules) == 50
    assert c.evaluate("action_0") == RuleAction.PERMIT
    assert c.evaluate("action_47") == RuleAction.PERMIT
    assert c.evaluate("blocked_action") == RuleAction.FORBID
    assert c.evaluate("needs_approval") == RuleAction.REQUIRE_APPROVAL
    assert c.evaluate("nonexistent") == RuleAction.FORBID  # default deny
_()


# ============================================================
# 7. EDGE CASES & ADVERSARIAL
# ============================================================
print("\n=== EDGE CASES & ADVERSARIAL ===")


@test("Edge: empty payload")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: no_payload
""")
    r = gate.authorize("agent-1", "no_payload", payload=None)
    assert r.authorized == True
    assert r.payload_hash == ""
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Edge: unicode action names")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: "読み取り"
""")
    r = gate.authorize("agent-1", "読み取り")
    assert r.authorized == True
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Edge: very long payload")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: big_payload
""")
    big_payload = {"data": "x" * 1_000_000}  # 1MB string
    r = gate.authorize("agent-1", "big_payload", payload=big_payload)
    assert r.authorized == True
    assert r.payload_hash != ""
    assert len(r.payload_hash) == 64  # SHA-256 = 64 hex chars
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Edge: metadata preserved through lifecycle")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: meta_action
""")
    meta = {"request_id": "req-123", "user": "jane", "priority": "high"}
    r = gate.authorize("agent-1", "meta_action", metadata=meta)
    assert r.metadata == meta
    gate.seal(r, result={"ok": True}, status="success")
    assert r.metadata == meta  # metadata survives sealing
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Adversarial: seal a denied receipt")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - forbid: blocked
""")
    r = gate.authorize("agent-1", "blocked")
    assert r.authorized == False
    # Try to seal it anyway
    gate.seal(r, result={"hacked": True}, status="success")
    # Should seal but status reflects the original denial
    assert r.seal_sig != ""  # seal happens (recording the attempt)
    # But original authorization still shows denied
    report = gate.verify(r)
    assert report["authorization_valid"] == True  # sig matches the denial
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Adversarial: swap receipt_id after signing")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: action
""")
    r = gate.authorize("agent-1", "action")
    original_id = r.receipt_id
    r.receipt_id = "forged-id-12345"
    report = gate.verify(r)
    assert report["authorization_valid"] == False, "Swapped ID should break verification"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Adversarial: change covenant_hash after signing")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - permit: action
""")
    r = gate.authorize("agent-1", "action")
    r.covenant_hash = "totally_different_covenant"
    report = gate.verify(r)
    assert report["authorization_valid"] == False
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Adversarial: change authorized flag after signing")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - forbid: blocked
""")
    r = gate.authorize("agent-1", "blocked")
    assert r.authorized == False
    r.authorized = True  # try to flip it
    report = gate.verify(r)
    assert report["authorization_valid"] == False, "Flipped authorized flag should break sig"
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


@test("Adversarial: change decision after signing")
def _():
    gate, tmpdir = make_gate("""
agent: test
version: "1.0"
rules:
  - forbid: blocked
""")
    r = gate.authorize("agent-1", "blocked")
    r.decision = "permit"  # try to change from forbid to permit
    report = gate.verify(r)
    assert report["authorization_valid"] == False
    shutil.rmtree(tmpdir, ignore_errors=True)
_()


# ============================================================
# 8. EXAMPLE COVENANT FILES
# ============================================================
print("\n=== EXAMPLE COVENANT FILES ===")


@test("Load loan-processor.covenant.yaml")
def _():
    path = os.path.join(os.path.dirname(__file__),
                        "sdk/air_blackbox/gate/examples/loan-processor.covenant.yaml")
    c = Covenant.from_yaml(path)
    assert c.agent == "loan-processor"
    assert len(c.rules) > 5
    # Test enforcement
    assert c.evaluate("read_credit_score") == RuleAction.PERMIT
    assert c.evaluate("delete_records") == RuleAction.FORBID
    assert c.evaluate("approve_loan", {"amount": 30000}) == RuleAction.PERMIT
    assert c.evaluate("approve_loan", {"amount": 75000}) == RuleAction.REQUIRE_APPROVAL
_()


@test("Load browser-agent.covenant.yaml")
def _():
    path = os.path.join(os.path.dirname(__file__),
                        "sdk/air_blackbox/gate/examples/browser-agent.covenant.yaml")
    c = Covenant.from_yaml(path)
    assert c.agent == "browser-agent"
    assert c.evaluate("navigate") == RuleAction.PERMIT
    assert c.evaluate("screenshot") == RuleAction.PERMIT
    assert c.evaluate("purchase", {"amount": 100}) == RuleAction.REQUIRE_APPROVAL
    assert c.evaluate("download_executable") == RuleAction.FORBID
    assert c.evaluate("install_extension") == RuleAction.FORBID
_()


# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print(f"RESULTS: {PASSED} passed, {FAILED} failed out of {PASSED + FAILED} tests")
print(f"{'='*60}")

if ERRORS:
    print("\nFAILURES:")
    for name, err in ERRORS:
        print(f"  ✗ {name}: {err}")

if FAILED == 0:
    print("\n✓ All tests passed.")
else:
    print(f"\n✗ {FAILED} test(s) failed.")
    exit(1)
