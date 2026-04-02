# Email to Deepchecks

**To**: philip@deepchecks.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Deepchecks (582 files scanned)

---

Hey Philip,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Deepchecks through the scanner and wanted to share what I found. With Deepchecks being used by enterprise teams to validate ML models and data, your users will increasingly need to demonstrate EU AI Act compliance for those same systems, and Deepchecks itself could be part of their compliance story.

**Summary**: 582 Python files scanned, 11/44 checks passing (25%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/7 passing |

The good news: your documentation game is strong. 86% docstring coverage and 77% type hint coverage are well above average for projects I've scanned. The biggest gaps are in record-keeping (only 2% of files use structured logging) and risk management (no risk assessment documentation). For a tool that enterprise teams rely on for ML validation, those are the areas regulators will look at first.

**To be clear**: this doesn't mean Deepchecks is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Would be curious to hear how you're thinking about EU AI Act readiness at Deepchecks, especially with the August 2026 enforcement deadline approaching. Happy to walk through the results in more detail if useful.

Best,
Jason Shotwell
https://airblackbox.ai
