# Email to LightOn (PyLate)

**To**: antoine.chaffin@lighton.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PyLate (104 files scanned)

---

Hey Antoine,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran PyLate through the scanner and wanted to share what I found. LightOn is one of the few Paris-based sovereign GenAI platforms serving French and EU enterprise customers directly, and PyLate is increasingly the default toolkit for teams training ColBERT-style retrieval models. That puts the hygiene of the training code squarely in scope for the EU AI Act when enforcement begins August 2, 2026.

**Summary**: 104 Python files scanned, 11/57 checks passing (19%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 2/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/10 passing |

The strongest signal is Article 9 (Risk Management): 2 of 5 checks pass, driven by error handling in the training loop. The weakest is Article 14 (Human Oversight) at 0/9. For a library whose users typically fine-tune retrieval models on internal corpora, the lack of any detectable approval-workflow or rate-limiting patterns will be one of the first things an auditor flags when these models get deployed inside a regulated enterprise.

**To be clear**: this does not mean PyLate is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It is a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

LightOn sells into French banks and the public sector, where "sovereign" is the whole pitch. Making PyLate the first ColBERT toolkit that ships with an explicit EU AI Act audit posture would be a very LightOn move, and I would be happy to help.

Best,
Jason Shotwell
https://airblackbox.ai
