# Email to Valohai

**To**: eero@valohai.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Valohai CLI (187 files scanned)

---

Hey Eero,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the valohai-cli repo through the scanner and wanted to share what I found. As a Helsinki-based MLOps platform serving teams running regulated ML pipelines (your customer pages list pharma, finance, and industrial use cases), you sit upstream of a lot of EU AI Act compliance workflows. Your customers will start asking you to show how Valohai helps them produce the technical documentation, logs, and audit trails that Articles 11 and 12 require, well before August 2, 2026.

**Summary**: 187 Python files scanned, 17/45 checks passing (38%) across Articles 9-15.

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/6 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 6/11 passing |

The good news: Article 15 is the strongest result in this scan, with reasonable coverage on output validation and hardware abstraction. Article 12 is also above average thanks to the CLI's logging patterns. The biggest gap is Article 14 (Human Oversight) at 0/9, where the scanner didn't find rate limiting, approval gates, or action boundaries. For a CLI that orchestrates training runs, adding structured approval hooks for destructive or high-cost operations would both close that gap and show up well in scans your customers run on their own pipelines.

**To be clear**: this doesn't mean Valohai is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

One angle worth considering: because Valohai already captures every pipeline run's lineage, adding tamper-evident signed audit chains to the execution records would be a strong compliance story for your enterprise and regulated customers. I've built a drop-in trust layer that does exactly this (HMAC-SHA256 chain per run). Would be happy to walk through how it fits.

Best,
Jason Shotwell
https://airblackbox.ai
