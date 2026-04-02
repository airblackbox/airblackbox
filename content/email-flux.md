# Email to FLUX (Black Forest Labs)

**To**: robin@blackforestlabs.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for FLUX (35 files scanned)

---

Hey Robin,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran FLUX through the scanner and wanted to share what I found. As a Freiburg-based company, Black Forest Labs falls directly under the EU AI Act's jurisdiction, and with the August 2, 2026 enforcement deadline approaching, the technical compliance patterns in your inference repo are worth examining now.

**Summary**: 35 Python files scanned, 6/44 checks passing (14%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/7 passing |

On the positive side, FLUX has strong type annotations at 81% coverage and solid input validation using Pydantic across 14 of 35 files. The biggest gap is record-keeping: no structured logging framework was detected, which is one of the easier things to fix but also one of the first things auditors look for under Article 12.

**To be clear**: this doesn't mean FLUX is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

  pip install air-blackbox
  air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally. No data leaves your machine.

Happy to walk through the results if useful. Given BFL's position as a leading EU AI company, getting ahead of compliance before the deadline could also be a strong signal to enterprise customers evaluating your API.

Best,
Jason Shotwell
https://airblackbox.ai
