# Email to Rossum

**To**: petr@rossum.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for rossum-sdk (83 files scanned)

---

Hey Petr,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran rossum-sdk through the scanner and wanted to share what I found. Rossum sits inside the document workflows of a lot of EU enterprises (finance, logistics, public sector), and under the August 2, 2026 EU AI Act enforcement deadline those customers are going to be mapping their conformity assessments back to every AI component in the pipeline, including the Python SDK. The good news is the SDK already picks up a lot of what the scanner wants to see.

**Summary**: 83 Python files scanned, 16/57 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The strong side: Art. 12 (record-keeping) came in at 4/9, with real logging infrastructure, retention patterns, and tracing. Art. 15 also looked solid on retry/backoff and output validation, which makes sense given how much the SDK has to handle API-aligned naming across sync and async clients. For a Python SDK, 28% is on the higher end of what the scanner typically reports.

The gap that would land hardest on your enterprise customers is Art. 10 data governance. The scanner didn't find PII detection, redaction, or masking patterns in code, and didn't find a DATA_GOVERNANCE.md. Given Rossum's primary use case is extracting structured data from invoices, contracts, and IDs, documenting how the SDK handles PII fields (or explicitly delegates that to the Elis platform) would be a small change that prevents every customer's DPO from asking the same question. Same story for a short MODEL_CARD.md pointing to the Elis extraction models.

**To be clear**: this doesn't mean rossum-sdk is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Rossum is one of the rare Prague AI companies with deep EU enterprise penetration, so whatever the SDK documents is going to set the baseline. Happy to share the full scan output or open a PR against the docs if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
