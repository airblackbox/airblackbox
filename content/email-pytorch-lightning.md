# Email to PyTorch Lightning (Lightning AI)

**To**: will@lightning.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PyTorch Lightning (646 files scanned)

---

Hey William,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran PyTorch Lightning through the scanner and wanted to share what I found. With 130M+ cumulative downloads and hundreds of enterprises training models on Lightning, many of your users building AI systems for the EU market will need to demonstrate compliance with the EU AI Act (enforcement begins August 2026).

**Summary**: 646 Python files scanned, 10/45 checks passing (22.2%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/8 passing |

The good news: Lightning has solid schema enforcement across its codebase (Pydantic/dataclass patterns) and type hint coverage is strong at 89%. Record-keeping benefits from the deep TensorBoard and logging integrations already in place, with retention/TTL patterns in 7 files and processing records in 25 files. The biggest gaps are in human oversight (iteration bounding exists in 62 files but lacks explicit stop mechanisms) and documentation, where docstring coverage sits at 38%.

**To be clear**: this doesn't mean PyTorch Lightning is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Lightning is the training framework for a huge slice of production AI. As your enterprise users start getting questions from their compliance teams about EU AI Act readiness, having a path to scan and document their training pipelines could be valuable. Would love to explore if there's a natural fit here.

Best,
Jason Shotwell
https://airblackbox.ai
