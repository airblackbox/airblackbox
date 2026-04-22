---
title: "Building Bilateral Receipts for AI Agent Actions"
published: false
description: "How we built a covenant-based policy engine with Ed25519 bilateral receipts, delegation chains, and HMAC audit trails for EU AI Act compliance."
tags: ai, python, opensource, security
canonical_url: https://airblackbox.ai/blog/bilateral-receipts
---

Your AI agent just approved a $75,000 loan. Can you prove who authorized it? Can you prove what the result was? Can you prove the policy that was active when the decision was made?

If your answer involves grepping log files, you have a problem. August 2026 is coming, and the EU AI Act requires tamper-evident records for high-risk AI systems. Not logs. Records.

I built a system that solves this. Here's how it works.

## The Problem: Logging Is Not Proof

Most AI agent frameworks have some form of logging. LangChain has callbacks. CrewAI has verbose mode. OpenAI has the API response. But none of them answer the hard questions:

**Was this action authorized before it ran?** Logs record what happened. They don't prove what was *supposed* to happen.

**Can you verify the record hasn't been tampered with?** Anyone with write access to your log store can alter a record after the fact. During a regulatory audit, that's a problem.

**Can a third party verify without your help?** If the auditor needs your internal tooling to check a record, the verification isn't independent.

These aren't theoretical concerns. EU AI Act Article 12 requires record-keeping with integrity guarantees. Article 14 requires human oversight that's demonstrable. If your agent approved a high-stakes decision and a regulator asks for proof, "here are some log lines" won't cut it.

## The Solution: Covenants + Bilateral Receipts

I added a system called Gate to [AIR Blackbox](https://github.com/airblackbox/airblackbox) that handles both sides: what agents are **allowed** to do (pre-execution) and what they **actually did** (post-execution), with cryptographic proof at every step.

It has three components:

### 1. Covenants — Policy as YAML

A covenant is a YAML file that declares the rules before the agent runs. Three rule types: `permit`, `forbid`, `require_approval`. Conditions are supported via `when` and `unless`.

```yaml
agent: loan-processor
version: "1.0"
rules:
  - permit: read_credit_score
  - permit: calculate_risk
  - permit: approve_loan
    when: "amount <= 50000"
  - require_approval: approve_loan
    when: "amount > 50000"
  - forbid: delete_records
  - forbid: modify_credit_score
```

Precedence is strict: `forbid` > `require_approval` > `permit` > default deny. If no rule matches, the action is denied. This is deliberate — fail closed, not open.

The covenant is SHA-256 hashed, and that hash is embedded in every receipt. Change one rule, and every subsequent receipt carries a different hash. An auditor can verify exactly which policy was active for any past action.

### 2. Bilateral Receipts — Two-Phase Proof

Every action produces a receipt with two cryptographic phases:

**Phase 1 (Authorization):** The gate evaluates the covenant, makes a decision, and signs the authorization with Ed25519. The action payload is SHA-256 hashed — raw data (PII, financial details) never enters the receipt.

**Phase 2 (Seal):** After execution, the result is hashed and sealed into the same receipt with a second Ed25519 signature. The seal covers the authorization signature, binding the entire lifecycle.

```python
from air_blackbox.gate import Gate, Covenant

covenant = Covenant.from_yaml("covenant.yaml")
gate = Gate(covenant=covenant)

# Phase 1: Authorization
receipt = gate.authorize(
    agent_id="loan-processor",
    action_name="approve_loan",
    payload={"applicant": "jane@example.com", "amount": 75000},
    context={"amount": 75000},
)

if receipt.authorized:
    result = process_loan(...)

    # Phase 2: Seal
    gate.seal(receipt, result=result, status="success")

# Any third party can verify with just the public key
report = gate.verify(receipt)
print(report["overall"])  # True
```

A single receipt answers all three hard questions:

- **Was it authorized?** The authorization signature proves the covenant was checked and the decision was made before execution.
- **Is it tamper-proof?** Ed25519 signatures are asymmetric. Altering any field invalidates the signature. No shared secret needed to verify.
- **Can a third party verify?** Give them the public key and the receipt. That's it.

### 3. HMAC-SHA256 Audit Chains

Individual receipts are strong. But an attacker could delete a receipt entirely. To prevent that, every receipt is also chained into an HMAC-SHA256 audit trail — each entry includes the hash of the previous entry. Delete or alter one, and every entry after it breaks.

This is the same principle behind blockchain, but without the overhead. No consensus, no network, no tokens. Just a hash chain stored locally.

## Delegation Chains

The real world isn't one agent doing one thing. It's orchestrators delegating to sub-agents, which delegate to other sub-agents. Gate handles this with `parent_receipt_id`:

```python
# Orchestrator gets authorized
parent = gate.authorize("orchestrator", "delegate_task",
                        payload={"task": "send confirmation"})

# Sub-agent links back to parent
child = gate.authorize("notifier", "send_email",
                       payload={"to": "jane@co.com"},
                       parent_receipt=parent)

# Walk the chain back to the root
chain = gate.walk_delegation_chain(child)
# [orchestrator_receipt, notifier_receipt]
```

Every receipt in the chain is independently verifiable. If a sub-agent misbehaves, the chain shows exactly who authorized the delegation and when.

## Human Approval

When a covenant rule says `require_approval`, Gate pauses execution and calls your callback. You decide the interface — Slack, email, CLI prompt, whatever:

```python
def slack_approval(receipt):
    # Send to Slack, wait for button click
    return ask_slack_channel(receipt)

gate = Gate(covenant=covenant, on_approval_needed=slack_approval)
```

If no callback is registered, `require_approval` defaults to deny. Fail closed.

The approval decision is signed into the receipt. A regulator can verify that a human was in the loop for that specific action.

## What It Doesn't Do

Some things Gate deliberately avoids:

- **It doesn't store raw payloads.** Only SHA-256 hashes. Your PII never enters the receipt.
- **It doesn't require a network.** Everything runs locally. No cloud dependency.
- **It doesn't make legal compliance claims.** It provides technical building blocks for audit-readiness. A covenant + receipt + chain is evidence, not certification.

## Numbers

I stress-tested the system with 58 tests covering covenants, receipts, the gate engine, delegation chains, persistence, adversarial tampering, and edge cases.

Performance on Apple Silicon: 9,300+ authorizations per second, 3,500+ full lifecycles (authorize + seal + verify) per second with Ed25519 signing. A 100-deep delegation chain verifies correctly. A 50-rule covenant evaluates correctly.

Adversarial tests: swapping receipt IDs after signing, changing covenant hashes, flipping the authorized flag, altering the decision field — all detected by signature verification.

## Try It

```bash
pip install air-blackbox[gate]
```

```python
from air_blackbox.gate import Gate, Covenant

covenant = Covenant.from_yaml_string("""
agent: my-agent
version: "1.0"
rules:
  - permit: read
  - require_approval: write
  - forbid: delete
""")

gate = Gate(covenant=covenant)
receipt = gate.authorize("my-agent", "read")
print(receipt.authorized)  # True
print(gate.verify(receipt)["overall"])  # True
```

The full source is at [github.com/airblackbox/airblackbox](https://github.com/airblackbox/airblackbox) under `sdk/air_blackbox/gate/`. Example covenants for a loan processor and a browser automation agent are included.

## What's Next

The covenant DSL today handles simple field-operator-value conditions. Next up: boolean logic (`and`/`or`), regex matching on action names, and rate-limit rules (e.g., "permit send_email unless more than 10 in the last hour").

The receipt format is designed for interoperability. The long-term goal is a published spec that any framework can implement — so receipts from a LangChain agent and a CrewAI agent chain together seamlessly.

If this is useful to you, [star the repo](https://github.com/airblackbox/airblackbox). If you find a bug, open an issue. If you have a use case that doesn't fit, I want to hear about it.

---

*This is not a certified compliance test. It is a technical building block for teams preparing for EU AI Act enforcement (August 2, 2026).*
