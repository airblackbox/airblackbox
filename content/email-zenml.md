# Email to ZenML

**To**: adam@zenml.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for ZenML (2,153 files scanned)

---

Hey Adam,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran ZenML through the scanner and wanted to share what I found. As an MLOps framework headquartered in Munich, ZenML's enterprise customers deploying AI pipelines in the EU will be directly subject to the EU AI Act when enforcement begins August 2, 2026. This makes compliance readiness a differentiator for you.

**Summary**: 2,153 Python files scanned, 16/45 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/5 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/4 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/4 passing |

The good news: ZenML's documentation game is strong. 96% docstring coverage and 99% type hint coverage is exceptional and well ahead of most projects I've scanned. Your Article 11 score is one of the highest I've seen. The biggest gap is in data governance (Article 10), where no PII detection, data governance docs, or data vault patterns were found. For a platform that orchestrates ML pipelines handling training data, that's the area where EU regulators will look first.

**To be clear**: this doesn't mean ZenML is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner also detected LangChain usage in the codebase. I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

With the August 2026 deadline four months out and ZenML's EU customer base, it might be worth a quick scan on your end to see where things stand.

Best,
Jason Shotwell
https://airblackbox.ai
