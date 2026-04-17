# Email to Arthur AI

**To**: adam@arthur.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Arthur Engine (603 files scanned)

---

Hey Adam,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Arthur Engine through the scanner and wanted to share what I found. As the team that open-sourced a real-time AI evaluation engine with built-in guardrails, you're already solving adjacent problems. Your enterprise customers using Arthur for AI governance in EU markets will need exactly this kind of compliance evidence.

**Summary**: 603 Python files scanned, 19/45 checks passing (42%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 6/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

Arthur Engine scored the highest of any project I've scanned this week, especially in Article 14 (Human Oversight): permission validation in 31 files, action boundary controls in 17 files, active rate limiting, and identity binding. That's exactly what regulators want to see. The PII detection/redaction in 4 files and injection defense patterns in 32 files are also strong signals. The biggest gap is Article 11 (Documentation), where docstring coverage sits at 35%. For an observability platform, the code-level documentation is the one area where the scanner expected more.

**To be clear**: this doesn't mean Arthur Engine is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
air_blackbox.attach("langchain")
```

Given how closely Arthur's mission aligns with EU AI Act compliance, I'd love to explore whether there's a natural integration point. Happy to walk through the scan results in more detail.

Best,
Jason Shotwell
https://airblackbox.ai
