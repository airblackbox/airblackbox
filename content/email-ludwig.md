# Email to Ludwig (Predibase / Rubrik)

**To**: travis@predibase.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Ludwig (641 files scanned)

---

Hey Travis,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Ludwig through the scanner and wanted to share what I found. With Rubrik's enterprise customer base now behind Ludwig, many of those customers have EU operations and will need to demonstrate that the ML tooling in their stack meets EU AI Act requirements by August 2, 2026. Compliance gaps in the framework become compliance gaps for every team deploying models through it.

**Summary**: 641 Python files scanned, 14/45 checks passing (31%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/9 passing |

Ludwig is stronger than most projects I scan. Article 15 (Security) stands out with injection defense patterns and structured output validation across 6 files. Article 12 (Record-Keeping) is solid with logging in 30% of files and tracing in 64 files. The biggest opportunity is Article 14 (Human Oversight), where only action boundary controls pass, and Article 10 (Data Governance), where input validation covers 108 of 641 files but PII handling patterns are absent.

**To be clear**: this doesn't mean Ludwig is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Ludwig's declarative approach actually makes it well-suited for compliance: if you know the full config driving a training run, you can audit it. Baking compliance checks into the Ludwig pipeline could be a strong differentiator for enterprise adoption.

Best,
Jason Shotwell
https://airblackbox.ai
