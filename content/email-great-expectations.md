# Email to Great Expectations (Superconductive)

**To**: abe@greatexpectations.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Great Expectations (1,655 files scanned)

---

Hey Abe,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Great Expectations through the scanner and wanted to share what I found. GX is the industry standard for data quality testing, and with the EU AI Act enforcement deadline in August 2026, data governance (Article 10) is front and center. Your users are exactly the people who will need to demonstrate compliance.

**Summary**: 1,655 Python files scanned, 12/45 checks passing (27%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/7 passing |

Strong points: type hints at 79% are excellent, input validation with Pydantic in 396 files is solid, and the injection defense patterns show security awareness. Agent identity binding also passed, which is uncommon. The biggest opportunity is Article 11 (Documentation), where docstring coverage is at 42%. For a project that's all about testing and validation, pushing that number up reinforces the brand.

Here's the interesting angle: Great Expectations already does data quality checks. The EU AI Act requires data governance (Article 10) for AI systems. There's a natural product extension where GX Expectations could map to EU AI Act Article 10 requirements. That's a powerful story for enterprise sales.

**To be clear**: this doesn't mean Great Expectations is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I'd love to explore whether there's a natural integration between GX data quality checks and EU AI Act Article 10 compliance reporting. Could be a win for both projects.

Best,
Jason Shotwell
https://airblackbox.ai
