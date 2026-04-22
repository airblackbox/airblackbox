# Show HN: Open-source CLI that scans Python AI code for EU AI Act compliance

## Post Body

We shipped AIR Blackbox, an open-source linter for AI agent code. It scans Python implementations against 48 technical requirements from 6 EU AI Act articles (9, 10, 11, 12, 14, 15).

Think ESLint for AI governance. You run it locally on your codebase. It checks for missing error handling, input validation, audit trails, injection defense, rate limiting, and other technical safeguards the regulation actually requires.

**What it does:**
- Scans 7 frameworks (LangChain, CrewAI, OpenAI Agents SDK, Claude Agent SDK, Google ADK, AutoGen, Haystack)
- Gap analysis across 48 checks
- Generates audit-ready evidence bundles with HMAC-SHA256 tamper-evident chains and ML-DSA-65 quantum-safe signing
- Runs 100% locally — no cloud, no API keys
- 1,500+ tests, 74% coverage, zero lint warnings

**Important:** This checks technical requirements, not legal compliance. It's a linter, not a lawyer. Real legal review is still required.

Enforcement deadline is August 2, 2026. Potential fines go up to €35M or 7% global revenue for non-compliance.

Source: github.com/airblackbox | Website: airblackbox.ai | Demo: airblackbox.ai/demo | Apache 2.0 license

---

## First Comment

A few things upfront since this will likely come up:

**On "compliance":** We never claim this makes code compliant. It surfaces gaps against the technical requirements in Articles 9-15. A linter finds bugs; a lawyer confirms you've fixed them. We're the linter.

**On the deadline:** August 2, 2026 is real. NIST's AI Risk Management Framework and various EU guidance documents map to these same articles. This tool handles the repetitive scanning so human reviewers can focus on context and risk judgment.

**On coverage:** The 48 checks target detectible technical patterns — error handling, logging depth, injection defense, rate limiting, HITL design, documentation. We don't check business logic, training data decisions, or fairness at scale (those require different tooling). If a check doesn't apply to your agent, it still runs but you can triage false positives.

**On the frameworks:** We auto-detect which framework you're using. If we're missing one or the detection is wrong, file an issue or ping us. This is early and we're actively maintaining.

**On trust layers:** These aren't magic. The HMAC and quantum-safe signing mean you can cryptographically prove "I scanned this code on this date with this version and these are the findings." Useful for audit trails and evidence bundles, not a substitute for real compliance work.

Happy to take questions on the technical checks, the frameworks, or how to integrate this into your CI/CD pipeline.

