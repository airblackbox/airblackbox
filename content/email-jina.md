# Email to Jina AI

**To**: han.xiao@jina.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Jina (643 files scanned)

---

Hey Han,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Jina through the scanner and wanted to share what I found. With the Elastic acquisition and Jina's Berlin headquarters, you're directly subject to the EU AI Act. Elastic's Fortune 500 customer base makes compliance readiness even more critical, and the August 2026 enforcement deadline is approaching fast.

**Summary**: 643 Python files scanned, 9/50 checks passing (18%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Documentation has strong foundations: 75% docstrings is solid. The tracing infrastructure is also notable, with 28 files showing production-grade observability patterns.

The critical finding: human oversight is at 0/9. No kill switch, no approval gates, no rate limiting, no execution bounding, no action boundaries. For a neural search framework that processes enterprise data at scale, zero human oversight mechanisms is the most urgent gap. This is especially relevant as Jina's models are now deployed through Elastic's inference service to thousands of enterprise customers.

**To be clear**: this doesn't mean Jina is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks:

```python
import air_blackbox
air_blackbox.attach("openai")
```

For a Berlin-based company now part of Elastic, getting ahead of EU AI Act compliance is a strategic advantage, not just a regulatory requirement.

Happy to collaborate on improving Jina's compliance coverage.

Best,
Jason Shotwell
https://airblackbox.ai
