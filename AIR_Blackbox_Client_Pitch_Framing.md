# AIR Blackbox — Client Conversation Framing

## The One-Liner

"We help teams put a trust layer between their people and their AI stack, so they can prove what happened, escalate risky outputs, detect policy drift, and maintain human oversight."

---

## The Category Reframe

| Old framing | New framing |
|-------------|-------------|
| Compliance tooling | **Trust infrastructure for AI operations** |
| "We scan for compliance gaps" | **"We own the interception layer"** |
| Audit logs | **Decision traceability** |
| Security scanning | **Escalation intelligence** |
| Code linting | **Operational drift detection** |
| Checkbox compliance | **Human oversight attestation** |

This changes the price ceiling immediately.

---

## The 60-Second Pitch

Your team adopted AI across how many workflows last quarter? Twelve? Twenty?

How many of those have a trust layer between your people and the AI? Something that proves what was decided, catches risky outputs before they ship, and detects when your team drifts from your own policies?

That's what we built. AIR Blackbox sits inside every AI call — not after it. It's the trust infrastructure between human intent and AI execution.

Most governance tools audit retrospectively. They scan your logs. They tell you what went wrong last week.

We catch it in real time. At the point of use.

The trust layer intercepts every LLM request and response and gives you four things:

1. **Decision traceability** — cryptographic proof of what the AI said, what the human chose, and when
2. **Escalation intelligence** — real-time detection of PII leaks and prompt injection, routed to human review
3. **Drift detection** — 39 compliance checks run on every commit, catching policy divergence before it ships
4. **Human oversight proof** — cryptographic attestation that a human reviewed and approved AI-assisted output

10 open-source packages. Runs locally. Your code never leaves your environment. EU AI Act compliant, GDPR-aware, ISO 42001 mapped.

---

## The Wedge-to-Platform Narrative

**Wedge:** Compliance scanning and trust layers (the thing they'll buy today)

**Why now:** AI usage is scaling without internal control systems. The EU AI Act deadline is August 2, 2026. Fines up to €35M or 7% of global turnover.

**The moat:** We sit inside the interaction layer, not outside it. Interception, not retrospective reporting. That's a fundamentally different architecture from every competitor.

**Expansion path:**
- Decision lineage (prove why decisions were made)
- Escalation intelligence (route risky outputs to humans)
- Operational drift detection (catch policy divergence)
- Human review attestation (prove a human actually reviewed it)
- Liability mapping (show exactly where AI creates legal exposure)

---

## Pricing Positioning

| Tier | Who | Price | What |
|------|-----|-------|------|
| Free | Individual devs, startups | $0 | Full scanner, all 10 PyPI packages, local only |
| Pro | Teams, mid-market | $299/mo | Managed infrastructure, team dashboards, priority support |
| Enterprise | Regulated industries | Custom | Air-gapped deployment, fine-tuned model, dedicated infra, SLA |

**Key point:** The open-source core builds trust and adoption. Enterprise customers pay for deployment, infrastructure, and support — not for the scanner itself.

---

## Objection Handling

**"We already use Credo AI / Holistic AI / Vanta"**
→ Those audit after the fact. We sit inside the call. You can use both — they're complementary. We catch issues at the point of use; they provide board-level reporting. But ask yourself: would you rather know about a compliance gap before it ships, or after an auditor finds it?

**"We'll build this ourselves"**
→ Of course you can build audit logging. But will you build HMAC-SHA256 tamper-evident chains? PII scanning across 4 categories? Prompt injection detection across 7 attack patterns? Framework-specific trust layers for LangChain, CrewAI, OpenAI, Anthropic, Google ADK, Haystack, and Claude Agent SDK? We're 10 packages and 14,000+ downloads in. This is our entire focus.

**"We don't need compliance yet"**
→ The deadline is August 2026. The lead time for compliance infrastructure is 6-12 months. Companies that start now get to iterate. Companies that start in July panic-buy. Also — compliance is just the wedge. The real value is decision traceability, escalation routing, and drift detection. Those matter whether or not you have a regulatory deadline.

**"Is this just AI for AI?"**
→ No. AI is a force multiplier inside the solution, not the product. The product is trust infrastructure — verifying, filtering, stabilizing, and protecting machine-assisted work. The fine-tuned model helps with contextual compliance analysis, but the core architecture is cryptographic (HMAC-SHA256 chains, audit records, attestation) and deterministic (regex-based PII detection, pattern-based injection scanning).

**"What's your traction?"**
→ 10 PyPI packages, 14,294+ downloads, trust layers for 7 frameworks plus standalone SDK packages. Open-source (Apache 2.0) with growing community adoption. Comparison blog post ranking for EU AI Act compliance keywords. CI/CD integration guide shipping this week.

---

## Vertical-Specific Angles

**Healthcare:**
"When your AI suggests a diagnosis, regulators want the decision lineage: what was asked, what was returned, who reviewed it, and what was overridden. We capture that entire chain."

**Financial Services:**
"Trading desks and advisory platforms need to prove what the model said, who approved it, and whether it should have been escalated to a human. We provide decision traceability and escalation intelligence at the call level."

**Legal:**
"Law firms using AI for contract review need to prove a human actually reviewed the output. Our trust layers create cryptographic human oversight attestation — not just a checkbox."

**Enterprise AI Teams:**
"Your team adopted AI across 12 workflows last quarter. How many drifted from policy? We scan on every commit, detect divergence, and block violations before they ship."

---

## The Thesis (memorize this)

AI made generation abundant.

What becomes valuable now is the infrastructure that verifies, routes, constrains, and records machine-assisted work in real time.

That is the company.
