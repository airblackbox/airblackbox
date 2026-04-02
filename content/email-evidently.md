# Email to Evidently AI

**To**: elena@evidentlyai.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Evidently (804 files scanned)

---

Hey Elena,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Evidently through the scanner and wanted to share what I found. With Evidently being used at thousands of companies and your London HQ, your enterprise customers with EU operations are going to need compliance documentation for the monitoring tools in their AI stack.

**Summary**: 804 Python files scanned, 15/45 checks passing (33%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 5/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Evidently actually scored the best of any project I've scanned this week. Your Article 14 (Human Oversight) coverage is strong with identity binding, token scope validation, and execution timeouts all detected. Type hints are at 88% which is solid. The main gap is Article 11 documentation: only 24% of public functions have docstrings, and there's no model card. For a monitoring framework used in production AI systems, closing that doc gap would make a big difference for compliance-conscious teams.

**To be clear**: this doesn't mean Evidently is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There's a natural fit here too: Evidently monitors model performance, AIR Blackbox monitors compliance posture. If you're ever thinking about adding a compliance monitoring dimension to the Evidently platform, I'd love to chat about how these could work together.

Best,
Jason Shotwell
https://airblackbox.ai
