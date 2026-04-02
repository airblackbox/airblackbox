# Email to whylogs (WhyLabs)

**To**: alessya@whylabs.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for whylogs (313 files scanned)

---

Hey Alessya,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran whylogs through the scanner and wanted to share what I found. WhyLabs is already in the data and model monitoring space, so EU AI Act compliance is a natural extension of what your customers already care about. As enforcement begins in August 2026, teams using whylogs for data quality monitoring will need to show they're also meeting the Act's technical requirements.

**Summary**: 313 Python files scanned, 10/45 checks passing (22.2%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

The good news: whylogs has excellent type hint coverage at 94% and solid schema enforcement through its profiling system. The data retention patterns are in place. The biggest gap is human oversight: the scanner found no explicit approval workflows, confirmation patterns, or execution bounding mechanisms. This makes sense for a logging library, but as whylogs gets used in production ML pipelines, the oversight patterns become relevant. Documentation coverage at 21% docstrings is also an area to improve.

**To be clear**: this doesn't mean whylogs is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There's a natural synergy: WhyLabs monitors data quality and model performance, AIR Blackbox monitors compliance posture. Your customers already log data profiles with whylogs. Adding compliance checks as another monitoring dimension could be a compelling story. Happy to explore what a partnership or integration might look like.

Best,
Jason Shotwell
https://airblackbox.ai
