# Email to Fondant (ML6)

**To**: matthias@ml6.eu
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Fondant (108 files scanned)

---

Hey Matthias,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Fondant through the scanner and wanted to share what I found. Ghent-based, built around foundation-model data preparation, used by teams that will be directly in scope when the EU AI Act hits enforcement on August 2, 2026. Article 10 (Data Governance) is the exact article that data pipeline frameworks get graded on, so Fondant is in an interesting position where its defaults quietly set the compliance posture for every team that adopts it.

**Summary**: 108 Python files scanned, 13/58 checks passing (22%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

The good parts first: Fondant has solid logging infrastructure, clean hardware abstraction (no hardcoded CUDA device strings), and a decent spread of type-annotated public functions. Article 12 (Record-Keeping) at 4/9 is actually above the median of what I see on this kind of framework.

The biggest lever is Article 10. Since Fondant's core value prop is "production-ready data processing," the data governance checks are the ones your users will look for first. Right now the scanner flags no data governance documentation (a DATA_GOVERNANCE.md or similar), no declared PII-exclusion policy at the dataset schema level, and no controlled-storage vault pattern. Those three additions would shift Art. 10 from 1/5 to 4/5 without touching the framework internals.

**To be clear**: this doesn't mean Fondant is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given ML6's consulting footprint with EU enterprise clients, a public Art. 10 posture on Fondant could become a real differentiator when those same clients start asking "how do we prove our training-data pipeline is EU AI Act ready." Happy to share the full scan output or walk through which checks are cheap wins versus bigger architectural shifts.

Best,
Jason Shotwell
https://airblackbox.ai
