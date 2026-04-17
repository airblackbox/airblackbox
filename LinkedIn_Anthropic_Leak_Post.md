# LinkedIn Post — Anthropic Leak + Air Gate

## Post Text (copy-paste into LinkedIn)

Anthropic leaked 500,000 lines of Claude Code's source code last week. Not through a hack — through a build step. Their CI pipeline published raw source to NPM instead of compiled output.

A few days before that, ~3,000 unpublished assets (blog drafts, model details, event plans) were sitting in a publicly accessible data store. That's how we learned about "Claude Mythos" before Anthropic was ready to announce it.

Two leaks in five days. From the company building Claude.

Here's what's interesting: Claude Code is an AI coding agent. It writes code, runs commands, and publishes packages. The NPM publish that exposed half a million lines of source? That was an agent action.

And there was no gate between "agent decides to publish" and "code hits a public registry."

This is the exact problem I've been building for. AIR Gate is an open-source action firewall for AI agents. Every agent action goes through a policy engine before it executes:

- Low risk → auto-allow
- Medium risk → scan for PII, secrets, internal patterns → then allow
- High risk (like publishing to NPM) → require human approval
- Blocked → action never executes

If Anthropic's publish step had run through a gate:
1. Policy engine flags "publish to public registry" as high-risk
2. PII redactor scans the payload — finds internal comments, debug code, unreleased API patterns
3. Action gets routed to a human for review
4. HMAC-SHA256 audit chain logs exactly what was published, who approved it, when

Instead, the agent published. Nobody reviewed. 500K lines of internal code went public.

AI agents are taking real-world, irreversible actions. Shipping code. Sending emails. Making API calls. Modifying databases. The gap between "agent decides" and "action happens" is where trust infrastructure belongs.

We built that interception layer. It's open source. Apache 2.0.

pip install air-gate

GitHub: https://github.com/airblackbox/air-gate
Docs: https://airblackbox.ai/gate

#AIGovernance #AISecurity #OpenSource #EUAIAct #Python #DevTools #AIAgents
