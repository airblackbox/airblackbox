---
title: AIR Gate v0.2.0 — Local-First AI Action Firewall
published: false
tags: ai, python, opensource, euaiact
---

Your AI agent just sent an email containing a customer's SSN. Your LangChain workflow is about to delete production records without asking anyone. Your OpenAI assistant called an API with auth tokens still in the payload.

You don't know any of this is happening.

Until now, the gap between "AI agents can do anything" and "humans need to approve it" has been a compliance black hole. The EU AI Act deadline is August 2026. This post is about a tool built to close that gap.

## The Problem

AI agents are finally powerful enough to be dangerous. They can send emails, delete records, call APIs, transfer funds. But most deployments ship with zero visibility into what actions agents are taking—and zero controls on what they're allowed to do.

The EU AI Act (Articles 9, 12, 14, 15) requires:
- Risk management: Know which actions are high-risk
- Record-keeping: Audit trail of every decision, tamper-evident
- Human oversight: Real humans must approve sensitive actions
- Robustness: Block bad actors, protect PII, validate outputs

Most teams treat this as a legal problem. It's actually an engineering problem.

## What I Built

AIR Gate is an open-source action firewall that sits between your AI agents and the tools they call. You define a policy, attach a GateClient to your agent, and every action gets scanned, redacted, approved or blocked—with an immutable HMAC-SHA256 audit chain for every decision.

**Install:**
```bash
pip install air-gate
```

**Set up (30 seconds):**
```python
from gate import GateClient

gate = GateClient(
    policy_path="gate_config.yaml"
)

# Check every action before executing
result = gate.check("my-agent", "email", "send_email",
                    payload={"to": "jane@example.com"})
# result["decision"]: "auto_allowed", "pending", or "blocked"
```

**Policy engine (YAML):**
```yaml
policy:
  default: require_approval
  rules:
    - name: allow-search
      action_type: search
      decision: auto_allow
    - name: approve-emails
      action_type: email
      decision: require_approval
    - name: block-delete
      action_type: db_delete
      decision: block
```

**What happens in production:**

```
━━━ 1. Agent searches for candidates ━━━
POST /actions  tool: search_candidates
✓ AUTO-ALLOWED  — matched rule: allow-search

━━━ 2. Agent sends email (PII auto-redacted) ━━━
POST /actions  tool: send_email
Payload:
  to: jane.doe@stripe.com
  ssn: 123-45-6789
  body: ...Call me at 415-555-0199

⚡ PII REDACTED: 3 fields
  → email: payload.to [hash_sha256]
  → phone: payload.body [hash_sha256]
  → ssn: payload.ssn [hash_sha256]

⏳ PENDING APPROVAL  — sent to Slack #ai-approvals
✓ APPROVED by jason@airblackbox.ai (via Slack)

━━━ 3. Agent tries to delete records ━━━
POST /actions  tool: delete_records
✗ BLOCKED  — matched rule: block-delete
  AI agents cannot delete data

━━━ 4. Verify HMAC-SHA256 audit chain ━━━
Chain integrity: VALID
✓ 3 events verified
✓ Zero tampering detected
```

## How It Works Under the Hood

Every action flows through a pipeline:

**Agent → GateClient → PolicyEngine → EventStore**

The policy engine evaluates three outcomes:
- `auto_allow`: Tool call proceeds, logged
- `require_approval`: Tool call paused, humans notified (Slack, email, webhook), proceeds only on approval
- `block`: Tool call rejected, agent sees error

Every decision is recorded in an HMAC-SHA256 audit chain. This means regulators can later verify that no events were added, deleted, or modified after the fact. The chain is cryptographically tamper-evident.

**PII redaction (25+ categories):**
- Phone numbers, emails, SSNs, credit cards, API keys, auth tokens, IP addresses, passport numbers, medical record numbers, financial account numbers, and more
- Four redaction methods: `hash_sha256` (irreversible), `mask` (last 4 only), `remove` (deleted), `tokenize` (replaced with placeholder)

v0.2.0 ships with GateClient in two modes:
- **Local mode**: Policy engine runs in your Python process. Fast, no network dependency, zero config.
- **Server mode**: FastAPI server with Slack integration. Central governance, human approvals via Slack Block Kit, callback URLs.

## Framework Integrations

**LangChain:**
```python
from gate.integrations.langchain import GatedTool
from langchain.agents import Tool

search_tool = Tool(
    name="search",
    func=my_search_fn,
    description="Search candidates"
)

gated = GatedTool(tool=search_tool, agent_id="research-agent")
# Use gated in your agent — every call goes through Gate
```

**OpenAI Agents:**
```python
from gate.integrations.openai_agents import gated_tool
from gate import GateClient

gate = GateClient()

@gated_tool(gate=gate, agent_id="assistant-v1")
def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}"
```

Both integrations are transparent—your agent code barely changes. The gate wraps your tools, not the reverse.

## Callback URLs for Async Approval

In v0.2.0, when an action requires approval, you can configure callback URLs instead of blocking. This is critical for long-running agents:

```yaml
policies:
  - name: require-approval-email
    tool: send_email
    action: require_approval
    callback_url: "https://approval-service.internal/actions/{action_id}"
    timeout: 3600  # 1 hour to approve
```

Your approval service receives the action details (redacted), human reviews it, approves or rejects via webhook, and the agent resumes.

## What It Doesn't Do

Be clear on scope:

- **Not legal compliance**: AIR Gate provides the technical controls. You still need lawyers.
- **Not a WAF**: It doesn't monitor existing traffic or intercept network calls. It operates at agent-action boundaries.
- **Not monitoring**: It doesn't watch what your agent thinks—only what it does.
- **Not a replacement for training**: Proper guardrails come from both policy + model behavior.

## Try It

The full demo is on GitHub:

```bash
git clone https://github.com/airblackbox/air-gate
cd air-gate
pip install -e .
python examples/demo.py
```

Or go straight to PyPI:

```bash
pip install air-gate
```

More at [airblackbox.ai/gate](https://airblackbox.ai/gate).

## What's Next

The roadmap:
- More framework integrations (LlamaIndex, AutoGen, Langsmith)
- Dashboard UI for live policy audits
- Webhook templates for Slack, PagerDuty, Datadog
- Performance profiles (batch approval, rate limiting)

The broader AIR Blackbox ecosystem is 12 PyPI packages. AIR Gate is the runtime enforcement layer. The compliance scanning tools (air-blackbox itself) run at development time.

## Why It Matters

In August 2026, regulators will ask: "Show us your controls." This isn't theoretical. It's happening now.

If you're building with LangChain, OpenAI, or any agent framework, you need audit-ready action boundaries. AIR Gate ships that out of the box.

It's open-source. It's local-first. It's built to pass a compliance audit.

---

Questions? Open an issue on GitHub or reach out on the AIR Blackbox Discord.
