# AIR Blackbox — Product Hunt Launch Kit

## Launch Details
- **Target**: Tuesday, April 8, 2026 at 12:01am PT
- **URL**: producthunt.com (submit night before)
- **Days until EU AI Act deadline**: 116

---

## Tagline
**AIR Blackbox — Trust infrastructure between your team and AI**

## Subtitle (140 chars)
Open-source compliance layers that sit inside every AI call. HMAC audit chains, agent identity, injection scanning. 12 PyPI packages. Free.

---

## First Comment (post immediately after launch)

Hey Product Hunt! I'm Jason.

118 days from now, the EU AI Act starts enforcing. Most AI teams haven't done a single compliance check.

AIR Blackbox is open-source trust infrastructure that sits inside your AI calls — not around them. The trust layers wrap your LLM client and intercept every request/response at the point of use.

What it does:

→ **Decision traceability** — HMAC-SHA256 tamper-evident audit chains. Every AI decision is logged, hashed, and independently verifiable. No one can alter the record after the fact.

→ **Agent identity** — Article 14 requires AI systems to identify themselves. AgentIdentity binds a name, owner, version, and SHA-256 fingerprint to every event in the chain. Shipped this week in air-trust v0.2.0.

→ **PII + injection scanning** — Detects personal data and prompt injection attempts in real time, before they reach the LLM.

→ **39 compliance checks** — Covers 6 EU AI Act articles (9, 10, 11, 12, 14, 15). Run them in CI/CD or scan interactively.

→ **No-code scanner** — Don't want to install anything? Paste your Python agent code at airblackbox.ai/scan and get an instant compliance report. Runs entirely in your browser. Your code never touches a server.

12 PyPI packages. Trust layers for LangChain, CrewAI, OpenAI, Anthropic, Google ADK. 14,000+ downloads. Zero dependencies. Runs locally. Apache 2.0.

Quick start:
```
pip install air-trust
```

Try the scanner: airblackbox.ai/scan
GitHub: github.com/airblackbox/airblackbox

The thesis: compliance is the wedge, trust infrastructure is the platform. Would love your feedback.

---

## Gallery Images (in order)

1. **ph-gallery-1-hero.png** — Hero: "Trust Infrastructure Between Human Intent and AI Execution"
2. **ph-gallery-2-architecture.png** — Architecture: Your Code → Trust Layer → LLM Provider
3. **ph-gallery-3-terminal.png** — Terminal: air-compliance scan output showing 63% score
4. **ph-gallery-4-comparison.png** — Comparison: AIR Blackbox vs. Deepchecks, AgentLair, Arthur AI
5. **ph-gallery-5-stats.png** — Stats: 12 packages, 14K+ downloads, 39 checks, 118 days

---

## Launch Day Checklist

### Night Before (Monday April 7)
- [ ] Submit product to Product Hunt (scheduled for 12:01am PT Tuesday)
- [ ] Prep first comment (copy above)
- [ ] DM 5-10 people asking them to comment in the first 2 hours
- [ ] Pre-write 3-5 responses to likely questions (see below)
- [ ] Queue up cross-posts for LinkedIn, Twitter, Reddit

### Launch Morning (Tuesday April 8)
- [ ] Post first comment immediately when live
- [ ] Share on LinkedIn with personal story angle
- [ ] Tweet thread (5 tweets)
- [ ] Post to Reddit r/Python
- [ ] Monitor and respond to every comment within 30 min

### After Launch
- [ ] Update airblackbox.ai with "Featured on Product Hunt" badge
- [ ] Write a "what I learned from launching on Product Hunt" post
- [ ] Follow up with everyone who commented

---

## Pre-Written Responses to Likely Questions

### "How is this different from Deepchecks?"
Deepchecks validates ML model behavior — great at what it does. AIR Blackbox sits at a different layer: it wraps the LLM call itself to provide tamper-evident audit chains (HMAC-SHA256), agent identity binding, and real-time PII/injection scanning. Think of Deepchecks as "did the model behave correctly?" and AIR Blackbox as "can you prove the log of that behavior wasn't altered, and does the agent identify itself to users?" They're complementary.

### "Does this actually make you EU AI Act compliant?"
No tool makes you compliant by itself — compliance is an organizational process. What AIR Blackbox does is handle the technical requirements: record-keeping (Article 12), human oversight hooks (Article 14), risk management checks (Article 9), and security scanning (Article 15). You still need the organizational pieces — governance policies, risk assessments, documentation. But the technical layer is the hardest part to retrofit, and that's what we solve.

### "Why open source? What's the business model?"
The scanner and trust layers are free forever (Apache 2.0). The future business model is managed infrastructure — hosted audit chain storage, compliance dashboards, and enterprise support. But the core tools will always be open source and local-first.

### "39 checks sounds like a lot. What do they actually cover?"
Six EU AI Act articles: Risk Management (Art. 9), Data Governance (Art. 10), Technical Documentation (Art. 11), Record-Keeping (Art. 12), Human Oversight (Art. 14), and Security (Art. 15). Each check maps to a specific requirement in the regulation. You can see exactly what each check does at airblackbox.ai/scan — paste any Python agent code and the report breaks it down by article with pass/warn/fail for each.

### "What frameworks do you support?"
Trust layers for LangChain, CrewAI, OpenAI SDK, Anthropic SDK, and Google ADK. The compliance scanner also detects AutoGen, Haystack, smolagents, DSPy, and Claude Agent SDK. Adding more every week.
