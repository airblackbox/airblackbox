# Email to Cleanlab

**To**: curtis@cleanlab.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Cleanlab (154 files scanned)

---

Hey Curtis,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Cleanlab through the scanner and wanted to share what I found. With 100+ Fortune 500 companies using Cleanlab for data quality and ML, many of those customers have EU operations and will need to show compliance for the AI systems your tools support. Your data governance angle is a natural fit for Article 10 requirements.

**Summary**: 154 Python files scanned, 9/45 checks passing (20%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/8 passing |

Strong points: 75% docstring coverage and 84% type hint coverage are excellent. You also have solid input validation with Pydantic/dataclass patterns in place and good tracing/observability across 13 files. The biggest gap is record-keeping: no structured logging framework was detected, which is one of the first things auditors look for under Article 12. Human oversight patterns (Article 14) also had no passing checks.

**To be clear**: this doesn't mean Cleanlab is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Cleanlab already solves a core piece of the compliance puzzle (data quality and governance), there might be an interesting integration story here. Would love to hear how you're thinking about positioning Cleanlab for the EU AI Act deadline in August 2026.

Best,
Jason Shotwell
https://airblackbox.ai
