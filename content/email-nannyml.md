# Email to NannyML

**To**: hakim@nannyml.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for nannyml (158 files scanned)

---

Hey Hakim,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran nannyml through the scanner and wanted to share what I found. NannyML is the library most EU teams reach for when they need to answer "is this model still performing" without ground truth, which puts it squarely in the Article 15 accuracy-and-robustness conversation. With the August 2, 2026 EU AI Act enforcement deadline, your users (especially on the Cloud and Soda side) are about to start asking what parts of Articles 9 through 15 the library already helps them cover. Some of the answers are genuinely strong.

**Summary**: 158 Python files scanned, 17/58 checks passing (29%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 2/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/11 passing |

The strong side: Art. 11 came in at 3/5 with 63% docstring coverage and 87% type hint coverage, and Art. 12 shows real logging infrastructure plus retention patterns, which is exactly what the scanner expects from a monitoring library. On Art. 15, retry/backoff and the tabular-only framing actually help (deterministic flags and hardware abstraction pass cleanly because there's no ML framework runtime to pin down).

The biggest gap is Art. 10 data governance (1/5). The scanner didn't find PII detection, masking, or a DATA_GOVERNANCE.md, and because NannyML is reading customer feature data and reference data to produce drift and CBPE estimates, the one question every DPO will ask is where that data sits and how it's treated. A short governance doc that clarifies "NannyML runs locally on the customer's infrastructure, no feature data leaves the library" would close most of that up for downstream teams.

**To be clear**: this doesn't mean nannyml is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

With NannyML now inside Soda, a lot of enterprise buyers are about to put data-quality and model-monitoring in the same conformity assessment column. A small pass over Art. 10 and Art. 14 (a documented "alert, then human confirms" flow on drift detections) would let your users cite NannyML directly in their Article 15 evidence. Happy to share the full scan output or open a PR against the docs if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
