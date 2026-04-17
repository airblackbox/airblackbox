# Hacker News — Show HN Post

## Title
Show HN: AIR Gate – An open-source action firewall for AI agents (Python)

## URL
https://github.com/airblackbox/air-gate

---

## First Comment (post immediately)

I built Gate because I kept watching agents do things they shouldn't.

The problem: AI agents can now send emails, call APIs, write files, delete records. Most teams have no runtime controls — the agent either has full access or no access. There's no middle ground.

Gate is that middle ground. It sits between your agent and the tools it calls. Every action goes through a policy check:

- **auto_allow** — read-only stuff passes through instantly
- **require_approval** — sensitive actions go to Slack, a human clicks approve/reject, the agent gets a callback
- **block** — some things AI just shouldn't do

Every decision gets signed into an HMAC-SHA256 tamper-evident chain. You can verify the entire audit trail hasn't been modified: `gate.verify()`.

v0.2.0 (shipped this week) added:

→ PII auto-redaction before data enters the audit chain (25+ categories — emails, SSNs, credit cards, medical records). Covers GDPR, HIPAA, PCI-DSS.

→ GateClient SDK so you can use it as a library without running a server.

→ Drop-in wrappers for LangChain tools and OpenAI function tools.

→ Callback URLs so your agent gets notified when a human approves/rejects (no polling).

Quick start:

    pip install air-gate

    from gate import GateClient
    gate = GateClient()
    result = gate.check("my-agent", "email", "send_email",
                        payload={"to": "jane@example.com"})

Runs entirely local. No cloud. No API keys. Apache 2.0.

What this doesn't do: legal compliance review. Gate provides technical controls — policy enforcement, audit trails, PII handling. You still need a lawyer for the legal side.

Part of the broader AIR Blackbox project (12 PyPI packages for AI governance). Gate handles runtime; the scanner handles build-time compliance checks.

Would appreciate feedback on the policy engine design and the audit chain approach. Code's at the link above, demo GIF in the README.
