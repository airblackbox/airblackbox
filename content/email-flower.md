# Email to Flower Labs

**To**: daniel@flower.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Flower (1,225 files scanned)

---

Hey Daniel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Flower through the scanner and wanted to share what I found. As a Hamburg-based company building the leading federated learning framework, Flower is in a unique position. Federated learning is one of the few approaches that naturally aligns with EU AI Act data governance requirements, since training data stays distributed. But the framework itself still needs to demonstrate compliance with Articles 9 through 15 for the enterprise teams deploying it in regulated environments.

**Summary**: 1,225 Python files scanned, 13/45 checks passing (29%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/5 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/4 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/4 passing |

Flower's documentation is solid: 84% docstring coverage and 74% type hints across 1,225 Python files is strong for a project of this scale. Data retention/TTL patterns were found in 52 files, which is excellent for Article 12 record-keeping. The biggest gaps are in security (Article 15), where no injection defense patterns were found (only output validation in 3 files), and data governance (Article 10), where no PII handling was detected. Given that Flower orchestrates model training across distributed nodes, the security posture is the area that will draw the most scrutiny from EU regulators.

**To be clear**: this doesn't mean Flower is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Being based in Hamburg and backed by $20M in funding, Flower is exactly the kind of project where demonstrating EU AI Act readiness early could be a competitive advantage, especially for regulated industries like healthcare and finance where federated learning shines.

Best,
Jason Shotwell
https://airblackbox.ai
