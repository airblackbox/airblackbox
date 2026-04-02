# Email to ClearML

**To**: moses@clear.ml
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for ClearML (397 files scanned)

---

Hey Moses,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran ClearML through the scanner and wanted to share what I found. ClearML's enterprise customers running ML pipelines in production are going to need compliance documentation for every tool in their AI stack before August 2, 2026. As the orchestration layer, ClearML is in a unique position to either be the compliance bottleneck or the compliance enabler.

**Summary**: 397 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

The strong points: ClearML has excellent fallback/recovery patterns (found in 28 files), solid tracing infrastructure (69 files with observability patterns), and good type hint coverage at 75%. The biggest opportunity is in docstring coverage (19% of public functions documented) and Article 14 human oversight patterns. For an MLOps platform that manages experiment tracking and pipeline orchestration, adding explicit approval gates and budget controls would be a natural extension.

**To be clear**: this doesn't mean ClearML is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

ClearML already tracks experiments and pipelines. Adding a compliance dimension to that tracking (which articles does each pipeline satisfy?) could be a powerful differentiator for enterprise accounts facing the EU AI Act deadline.

Best,
Jason Shotwell
https://airblackbox.ai
