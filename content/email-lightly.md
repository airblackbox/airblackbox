# Email to Lightly AI

**To**: matthias@lightly.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Lightly (752 files scanned)

---

Hey Matthias,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Lightly framework through the scanner and wanted to share what I found. As a Zurich-based company building data curation tools for computer vision teams, Lightly is directly in scope for the EU AI Act, and your enterprise customers using the platform for autonomous driving and industrial applications will need to demonstrate compliance.

**Summary**: 752 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

Strong points: 78% docstring coverage and 77% type hints are solid. You have excellent input validation, with 277 out of 752 files using Pydantic/dataclass patterns, and the scanner found fallback patterns in 16 files. Lightly also scored well on Article 15 with output validation and retry/backoff logic detected. The main gap is Article 12 (record-keeping): only 1% of files use structured logging, which matters a lot for audit trail requirements, especially in safety-critical CV applications.

**To be clear**: this doesn't mean Lightly is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Since Lightly works with data curation for ML pipelines, there could be an interesting fit between your data governance capabilities and the Article 10 requirements we check for. Would love to compare notes on how Swiss/EU-based AI companies are preparing for August 2026.

Best,
Jason Shotwell
https://airblackbox.ai
