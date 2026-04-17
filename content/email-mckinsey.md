# Email to McKinsey

**To**: henning_soller@mckinsey.com
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act scanner for client AI assessments

---

Hey Henning,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I read your piece on trusted AI compliance and the work you're doing at the McKinsey Technology Institute. With the August 2026 enforcement deadline approaching, I wanted to share a tool that might be useful for client engagements where technical AI compliance assessment is part of the scope.

AIR Blackbox scans Python AI codebases and maps technical patterns directly to EU AI Act Articles 9 through 15. It checks for risk management patterns, data governance controls, documentation coverage, record-keeping infrastructure, human oversight mechanisms, and security posture. A full scan takes about 30 seconds and produces a per-article compliance breakdown.

I've scanned 30+ major AI projects. The average score is around 25%. Most organizations don't have visibility into where their technical gaps are until they run something like this.

**What makes this relevant for your practice:**

- **Runs entirely on-premise.** Zero client data leaves their environment. No API calls, no cloud processing. This is critical for the kind of clients McKinsey works with.
- **Open source and inspectable.** Apache 2.0 license. Your teams can validate every check against the regulation text.
- **Complements the Credo AI partnership.** I know QuantumBlack has a strategic alliance with Credo AI for governance and policy. AIR Blackbox operates at the code level, scanning the actual implementation. Policy-level governance (Credo AI) plus code-level scanning (AIR Blackbox) covers the full stack.

You can try the live demo here: https://airblackbox.ai/demo

Or run it locally:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built drop-in trust layers for popular agent frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, Agno) that add HMAC-SHA256 tamper-evident audit chains. These generate cryptographically verifiable compliance artifacts, the kind of evidence that regulators will expect.

**To be clear**: the scanner checks for technical patterns, not legal compliance. It's a linter for AI governance that gives technical teams a starting point for remediation.

I'd welcome the chance to walk through the tool or scan a sample project with your team. Would that be useful?

Best,
Jason Shotwell
https://airblackbox.ai
