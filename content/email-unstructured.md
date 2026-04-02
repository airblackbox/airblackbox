# Email to Unstructured (Unstructured.io)

**To**: brian@unstructured.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Unstructured (279 files scanned)

---

Hey Brian,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Unstructured through the scanner and wanted to share what I found. As the go-to ETL layer for LLM pipelines, Unstructured sits at a critical point in the data supply chain. The EU AI Act's data governance requirements (Art. 10) apply directly to how training and inference data is ingested, transformed, and validated, which is exactly what your users rely on Unstructured for.

**Summary**: 279 Python files scanned, 11/45 checks passing (24.4%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

The good news: Unstructured has the strongest documentation coverage in this batch, with 65% docstring coverage and 88% type hint coverage. Consent management patterns were detected in 5 files, and data retention patterns are in place. The biggest gaps are in human oversight (no execution bounding detected, meaning processing pipelines can run without explicit stop mechanisms) and record-keeping (logging exists but lacks tamper-evident audit trails).

**To be clear**: this doesn't mean Unstructured is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

As enterprise teams build RAG pipelines with Unstructured, their compliance teams will start asking about data lineage and governance through the entire pipeline. Showing that the ingestion layer has been scanned and documented against EU AI Act articles could be a competitive advantage for your enterprise product. Happy to chat if this is on your radar.

Best,
Jason Shotwell
https://airblackbox.ai
