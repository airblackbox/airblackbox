# Email to Weights & Biases (wandb)

**To**: lukas@wandb.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for wandb (1,386 files scanned)

---

Hey Lukas,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the wandb client library through the scanner and wanted to share what I found. W&B is embedded in ML pipelines across thousands of teams globally, and with CoreWeave's infrastructure scale behind it, many of those teams have EU operations subject to the EU AI Act. When the experiment tracking layer has compliance gaps, every model trained through it inherits those gaps. Enforcement starts August 2, 2026.

**Summary**: 1,386 Python files scanned, 15/45 checks passing (33%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/9 passing |

wandb scores well where it matters most for an observability platform. Article 12 (Record-Keeping) shows tracing patterns in 847 files and action-level audit logging in 25 files, which makes sense for a tool built around experiment tracking. Article 15 (Security) is solid with injection defense in 7 files and retry/backoff in 80 files. The biggest gaps are in Article 10 (Data Governance), where PII-aware references exist in 13 files but no detection/redaction library is integrated, and Article 9 (Risk Management), where formal risk documentation is missing.

**To be clear**: this doesn't mean wandb is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

W&B already tracks everything about model training. Adding an EU AI Act compliance dimension to that tracking could be a natural extension, and a differentiator for enterprise teams navigating the August 2026 deadline.

Best,
Jason Shotwell
https://airblackbox.ai
