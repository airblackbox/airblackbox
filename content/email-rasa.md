# Email to Rasa

**To**: alan@rasa.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Rasa (600 files scanned)

---

Hey Alan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Rasa open-source repo through the scanner and wanted to share what I found. As a Berlin-based conversational AI framework deployed in enterprise contact centers across Europe, Rasa is directly in scope for EU AI Act obligations. Your enterprise customers will need to demonstrate compliance for the AI systems they deploy, and Rasa is the foundation of many of those systems.

**Summary**: 600 Python files scanned, 21/48 checks passing (44%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 6/8 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 4/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

Rasa scored higher than most projects I've scanned. The codebase shows real engineering maturity: 87% docstring coverage, 99% type hints, tamper-evident logging via HMAC in the Facebook and Slack channel integrations, structured logging across 185 files, and tracing in 16 files. Article 12 (Record-Keeping) is nearly fully covered at 6/8.

The main gaps are in Articles 9 and 10. There's no formal risk classification document, no data governance documentation, and PII references exist in 8 files without a detection/redaction library. For a framework powering customer-facing conversations, PII handling is the check your enterprise customers will ask about first.

**To be clear**: this doesn't mean Rasa is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

With the August 2, 2026 enforcement deadline approaching, offering compliance tooling or compliance-ready documentation alongside Rasa Pro could be a powerful differentiator for your enterprise customers. Happy to dig into the details.

Best,
Jason Shotwell
https://airblackbox.ai
