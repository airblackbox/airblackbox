# air-gate

HMAC-SHA256 audit chain engine with human-in-the-loop tool gating for AI agents. Implements EU AI Act Article 14 (Human Oversight).

## Overview

`air-gate` sits between your AI agent and its tools. Before calling a dangerous operation (send email, delete files, execute SQL), it pauses execution and requires explicit human approval. Every approval or denial is logged to a tamper-evident HMAC-SHA256 audit chain.

## Quick Start

```bash
pip install air-gate
```

### Basic Usage

```python
from air_gate import GateKeeper, RiskTier
from air_trust import AuditChain

# Initialize with audit chain
audit_chain = AuditChain(secret_key="your-secret")
gatekeeper = GateKeeper(audit_chain=audit_chain)

# Configure risk tiers
gatekeeper.set_risk_tier("send_email", RiskTier.HIGH)
gatekeeper.set_risk_tier("read_file", RiskTier.LOW)
gatekeeper.set_risk_tier("execute_sql", RiskTier.HIGH)

# Gate a tool call
def send_email(to, subject, body):
    # Returns True if approved, False if denied
    if not gatekeeper.request_approval("send_email", {"to": to}):
        raise PermissionError("Tool call denied by human")
    # ... actual email logic
    
# Automatic approval for low-risk tools, human review for HIGH
result = send_email("user@example.com", "Hello", "Test message")

# Access audit trail
for entry in audit_chain.entries():
    print(f"{entry['timestamp']} | {entry['action']} | HMAC: {entry['signature']}")
```

## Risk Tier Configuration

Configure tools by risk level. Use a dict or YAML config:

```python
risk_config = {
    "LOW": ["read_file", "list_directory", "get_current_time"],
    "MEDIUM": ["write_file", "send_slack_message"],
    "HIGH": ["send_email", "execute_sql", "delete_file", "deploy_service"]
}

gatekeeper.load_config(risk_config)
```

**AUTO_APPROVE** (LOW): Tools execute without human intervention.  
**REQUIRE_APPROVAL** (MEDIUM/HIGH): Execution pauses; human must approve/deny.

## Audit Chain & Tamper-Evidence

Every gate decision is cryptographically signed using HMAC-SHA256. The chain prevents tampering:

```python
# Each entry includes timestamp, action, decision, and HMAC signature
entry = {
    "timestamp": "2026-04-10T14:32:05Z",
    "tool": "send_email",
    "decision": "APPROVED",
    "approver": "alice@company.com",
    "signature": "abc123def456..."  # HMAC-SHA256
}

# Verify chain integrity
is_valid = audit_chain.verify()  # True if unmodified, False if tampered
```

All entries are chained: each signature depends on the previous entry, making it impossible to insert, delete, or reorder decisions without detection.

## Integration with air-trust

`air-gate` uses `air-trust`'s `AuditChain` class under the hood for cryptographic signing and verification. This ensures your approval log is tamper-evident and compliant with Article 14 record-keeping requirements.

```python
from air_trust import AuditChain

# air-gate automatically uses this for HMAC signing
audit_chain = AuditChain(secret_key="your-secret-key")
gatekeeper = GateKeeper(audit_chain=audit_chain)
```

## Part of AIR Blackbox

`air-gate` is one component of the **AIR Blackbox** ecosystem for EU AI Act compliance:

- **[air-gate](https://github.com/airblackbox/air-gate)** — Human-in-the-loop tool gating (Article 14)
- **[air-trust](https://github.com/airblackbox/air-trust)** — HMAC audit chains + Ed25519 signed handoffs
- **[air-blackbox](https://github.com/airblackbox/gateway)** — EU AI Act compliance scanner (39 checks)
- **[air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp)** — Claude Desktop / Cursor integration

## License

Apache License 2.0. See LICENSE file.

## Installation from PyPI

```bash
pip install air-gate
```

---

**Questions?** Open an issue on [GitHub](https://github.com/airblackbox/air-gate).
