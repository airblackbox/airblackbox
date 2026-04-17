# Email to Photoroom

**To**: matthieu@photoroom.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Photoroom datago (12 files scanned)

---

Hey Matt,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Photoroom's datago through the scanner and wanted to share what I found. As a Paris-based AI company with a large consumer footprint, image-generation pipelines, and a growing enterprise business, you're directly subject to the EU AI Act starting August 2, 2026. Article 50 transparency rules on AI-generated content and the data-governance requirements around image training pipelines are going to land squarely on teams like yours.

**Summary**: 12 Python files scanned, 9/44 checks passing (20%) across Articles 9-15. The repo is small (dataloader utility), so this is a narrow snapshot, not a full platform audit.

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 0/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/6 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/10 passing |

The good news: Article 11 (Documentation) is passing 4/6, which is strong for a repo of this size. The biggest gap is Article 10 (Data Governance) at 0/5, which matters because datago is a data-pipeline tool. Adding lightweight schema validation and a documented PII-exclusion policy at ingestion would address both the scan and the questions your enterprise customers will ask about how training data flows through Photoroom's stack. The scanner will be more informative if you point it at one of your larger internal Python services, where data handling, logging, and oversight patterns have more surface area to analyze.

**To be clear**: this doesn't mean Photoroom is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves on any internal Python codebase:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine, which matters for you specifically given that your image training pipelines are competitive IP.

One angle worth flagging: I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains to model calls. For Photoroom's enterprise and brand-safety customers, signed records of which image went through which model would be a strong answer to the provenance questions that are already showing up in procurement reviews.

Best,
Jason Shotwell
https://airblackbox.ai
