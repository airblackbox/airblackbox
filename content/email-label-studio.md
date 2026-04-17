# Email to Label Studio (HumanSignal)

**To**: michael@humansignal.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Label Studio (670 files scanned)

---

Hey Michael,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Label Studio through the scanner and wanted to share what I found. As the most widely adopted open-source data labeling platform, Label Studio is part of the AI pipeline for thousands of teams. When the EU AI Act enforcement deadline hits in August 2026, those teams will need to demonstrate data governance across their entire stack, and that includes the tooling they use to prepare training data.

**Summary**: 670 Python files scanned, 17/45 checks passing (38%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 2/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 5/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Label Studio shows real strength in Article 14 (Human Oversight): rate limiting, permission validation across 30 files, and token scope controls. That makes sense for a multi-user platform. Article 12 (Record-Keeping) also looks solid with logging in 137 files and data retention patterns in 27 files. The biggest gap is Article 11 (Documentation), where docstring coverage is at 22% and type hints at 18%. The scanner also flagged possible raw user input in prompts in `label_studio/server.py`, which is worth a look from a security perspective.

**To be clear**: this doesn't mean Label Studio is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Given how central Label Studio is to the AI data pipeline, I'd love to explore how compliance tooling could add value for your Enterprise customers. Happy to walk through the scan results in detail.

Best,
Jason Shotwell
https://airblackbox.ai
