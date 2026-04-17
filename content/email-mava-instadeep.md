# Email to InstaDeep (Mava)

**To**: karim@instadeep.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Mava (86 files scanned)

---

Hey Karim,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Mava through the scanner and wanted to share what I found. As a BioNTech subsidiary headquartered in the UK with deep ties to the EU market, InstaDeep's AI systems will be directly subject to the EU AI Act when enforcement begins August 2, 2026. Multi-agent RL frameworks like Mava that could be deployed in enterprise or healthcare settings make this especially relevant.

**Summary**: 86 Python files scanned, 15/57 checks passing (26%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/10 passing |

Mava's documentation game is strong: 100% type hint coverage and 71% docstring coverage put you ahead of most projects on Article 11. Record-keeping is also solid with logging in 28% of files, tracing infrastructure, and action-level audit trails. The biggest gaps are in Article 14 (human oversight), where the scanner found no kill switch, no human-in-the-loop gates, and no token expiry bounding for autonomous agent execution, and Article 9 (risk management), where no risk assessment or classification documents were found.

**To be clear**: this doesn't mean Mava is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Mava is a multi-agent framework, I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains and agent identity binding. It takes two lines to integrate and covers several of those Article 12 and 14 gaps the scanner flagged.

Would love to hear how InstaDeep is thinking about EU AI Act readiness across your open-source portfolio. Happy to walk through the results if helpful.

Best,
Jason Shotwell
https://airblackbox.ai
