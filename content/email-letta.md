# Email to Letta (MemGPT)

**To**: charles@letta.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Letta (852 files scanned)

---

Hey Charles,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Letta through the scanner and wanted to share what I found. As an agent framework with persistent memory, Letta's architecture has unique compliance implications: agents that remember and evolve raise specific questions under the EU AI Act around record-keeping, human oversight, and data governance that most frameworks don't address.

**Summary**: 852 Python files scanned, 17/45 checks passing (38%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 4/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/7 passing |

This is one of the strongest scans I've seen. Letta already has action-level audit logging across 22 files, production-grade tracing in 208 files, agent identity binding in 11 files, and injection defense patterns in 5 files. You're clearly thinking about this stuff. The main gap is Article 10 (data governance): no data governance documentation was detected, and while PII-aware variable names appear in 20 files, there's no detection/redaction library integrated.

**To be clear**: this doesn't mean Letta is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

  pip install air-blackbox
  air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally. No data leaves your machine.

Given Letta's focus on persistent memory agents, there's a natural fit here. Would be happy to walk through how the scanner maps to the specific compliance challenges that stateful agent architectures face.

Best,
Jason Shotwell
https://airblackbox.ai
