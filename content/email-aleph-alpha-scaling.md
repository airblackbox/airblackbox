# Email to Aleph Alpha (Scaling)

**To**: jonas@aleph-alpha.de
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Scaling (256 files scanned)

---

Hey Jonas,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Scaling distributed training library through the scanner and wanted to share what I found. As a Heidelberg-based AI company building foundational LLM infrastructure, Aleph Alpha is directly subject to the EU AI Act, with enforcement starting August 2, 2026. Your training infrastructure touches every model that comes out of it, so compliance patterns here propagate downstream.

**Summary**: 256 Python files scanned, 8/45 checks passing (18%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/9 passing |

The good news: Scaling has 100% type hint coverage across all 626 public functions, which is exceptional and puts you ahead of nearly every project I've scanned. The biggest gap is Article 14 (Human Oversight) with zero checks passing, and Article 12 (Record-Keeping) where structured logging only appears in 11% of files. For a distributed training library that orchestrates GPU clusters, having audit trails and oversight mechanisms becomes critical under the Act.

**To be clear**: this doesn't mean Scaling is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given Aleph Alpha's position as one of Europe's leading AI companies, having a clean compliance posture before August 2026 could be a competitive differentiator, especially with enterprise and public sector customers who are already asking about EU AI Act readiness.

Best,
Jason Shotwell
https://airblackbox.ai
