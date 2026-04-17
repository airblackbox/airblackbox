# Email to Snorkel AI

**To**: alex@snorkel.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Snorkel (146 files scanned)

---

Hey Alex,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Snorkel through the scanner and wanted to share what I found. Snorkel's enterprise customers building training data pipelines for production AI systems will be directly affected by the EU AI Act starting August 2, 2026. Article 10 (Data Governance) specifically requires documentation and quality controls for training data, which puts Snorkel right in the center of the compliance conversation.

**Summary**: 146 Python files scanned, 10/58 checks passing (17%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

The documentation is excellent: 90% docstring coverage and 98% type hint coverage put Snorkel in the top tier of projects I've scanned on Article 11. The CHANGELOG is also a plus for Article 13. The biggest gaps are in Articles 9, 12, and 14. The scanner found no risk assessment documents, no tamper-evident audit chain for training data operations, no kill switch, and logging in only 8% of files. For a data labeling framework, the Article 10 gap is worth noting: the scanner found no PII detection or data governance documentation, which matters because weak supervision over unlabeled data can inadvertently surface PII in training sets.

**To be clear**: this doesn't mean Snorkel is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given Snorkel's position as the training data layer for enterprise AI, being able to demonstrate EU AI Act readiness could differentiate you in regulated industries like finance and healthcare. Happy to walk through the results if helpful.

Best,
Jason Shotwell
https://airblackbox.ai
