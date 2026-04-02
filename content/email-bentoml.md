# Email to BentoML

**To**: chaoyu@bentoml.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for BentoML (425 files scanned)

---

Hey Chaoyu,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran BentoML through the scanner and wanted to share what I found. BentoML is the serving layer for production AI systems, which means your enterprise users deploying models to EU-facing customers need compliance documentation for the infrastructure they run on. With the August 2, 2026 enforcement deadline approaching, the serving layer is exactly where compliance checks need to happen at runtime.

**Summary**: 425 Python files scanned, 13/45 checks passing (29%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

BentoML has some of the strongest infrastructure patterns I've seen: 33% of files have structured logging (well above average), tracing is production-grade in 13 files, and type hint coverage is 91%. The main gaps are in Article 14 (no explicit human approval gates or budget enforcement) and Article 15 (no prompt injection defense detected). For a model serving platform, adding request-level compliance checks at the inference boundary would be a natural fit.

**To be clear**: this doesn't mean BentoML is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains to AI calls at the serving layer. If BentoML ever wants to offer compliance-ready serving as a feature, this could plug right in:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Happy to walk through the integration if it's interesting.

Best,
Jason Shotwell
https://airblackbox.ai
