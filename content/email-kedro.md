# Email to Kedro (QuantumBlack / McKinsey)

**To**: yetunde_dada@mckinsey.com *(unverified - McKinsey email pattern. Jason: may need manual verification via LinkedIn)*
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Kedro (198 files scanned)

---

Hey Yetunde,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Kedro through the scanner and wanted to share what I found. As a McKinsey/QuantumBlack project now hosted by the Linux Foundation, Kedro is used by enterprise teams across the EU to build production ML pipelines. That makes EU AI Act compliance directly relevant to the teams deploying Kedro in regulated environments.

**Summary**: 198 Python files scanned, 10/45 checks passing (22%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/7 passing |

The good news: Kedro's documentation game is strong. 74% of public functions have docstrings and 69% have type hints, which puts you ahead of most projects on Article 11. Input validation via Pydantic is also solid. The biggest gap is Article 14 (Human Oversight), where the scanner found no approval gates, rate limiting, or execution bounding patterns. For a pipeline framework that orchestrates ML workflows, that's the area enterprise compliance teams will scrutinize first.

**To be clear**: this doesn't mean Kedro is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that McKinsey has enterprise clients across the EU building on Kedro, having a built-in compliance check could be a differentiator. Happy to chat about how other frameworks are approaching this.

Best,
Jason Shotwell
https://airblackbox.ai
