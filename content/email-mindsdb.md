# Email to MindsDB

**To**: jorge@mindsdb.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for MindsDB (1,635 files scanned)

---

Hey Jorge,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran MindsDB through the scanner and wanted to share what I found. MindsDB connects to 200+ data sources and runs ML directly on live data, which means your enterprise users are deploying AI workflows that touch production databases. When the EU AI Act enforcement deadline hits on August 2, 2026, those enterprise customers with EU operations will need compliance evidence for their AI pipelines.

**Summary**: 1,635 Python files scanned, 20/48 checks passing (42%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/8 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 6/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

MindsDB's strongest area is Article 14 (Human Oversight), scoring 6/9. The scanner found kill switch mechanisms, human-in-the-loop patterns, identity binding, token scope validation, execution timeouts, and action boundary controls. That's enterprise-grade architecture. Article 12 is also strong at 5/8 with OpenTelemetry tracing across 44 files, HMAC patterns in 6 files, and retention policies in place.

The gaps are in Articles 9 and 10. No formal risk classification or data governance documentation. Given MindsDB's position as an AI layer sitting on top of live data sources, data governance is where your enterprise customers will scrutinize first.

**To be clear**: this doesn't mean MindsDB is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains for frameworks MindsDB integrates with:

```python
import air_blackbox
air_blackbox.attach("langchain")  # or "openai", "anthropic"
```

Happy to walk through the findings in more detail. As a YC company with enterprise customers, getting ahead of the compliance curve could be a real value-add for your users.

Best,
Jason Shotwell
https://airblackbox.ai
