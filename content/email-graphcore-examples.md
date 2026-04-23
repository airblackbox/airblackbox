# Email to Graphcore (examples)

**To**: nigelt@graphcore.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Graphcore examples (1,225 files scanned)

---

Hey Nigel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the graphcore/examples repo through the scanner and wanted to share what I found. As a UK-headquartered AI compute company now under SoftBank, with enterprise customers across Europe deploying IPU-accelerated models, the training and inference code in this repo directly shapes how downstream teams build systems that will be subject to the EU AI Act when enforcement begins August 2, 2026.

**Summary**: 1,225 Python files scanned, 14/58 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

Good news up front: the scanner found deterministic seeding across NumPy, PyTorch and TF in the training scripts, plus processing-record patterns in 31 files. The weakest signal is Article 11 (Technical Documentation), where only 1 of 5 checks passes. For a repo that other teams use as reference implementations for BERT, GPT-2, GNNs and speech models on IPU hardware, that gap matters most: downstream adopters will inherit whatever documentation hygiene the reference code has.

**To be clear**: this does not mean Graphcore examples is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It is a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

With SoftBank-backed enterprise reach in Europe and a reference-implementation repo that teaches people how to build on IPUs, you are in a unique position: every example you ship sets the default compliance posture for a lot of downstream ML teams. Happy to walk through the detailed findings if useful.

Best,
Jason Shotwell
https://airblackbox.ai
