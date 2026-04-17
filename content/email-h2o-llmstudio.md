# Email to H2O.ai (H2O LLM Studio)

**To**: sri@h2o.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for H2O LLM Studio (113 files scanned)

---

Hey Sri,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran H2O LLM Studio through the scanner and wanted to share what I found. H2O.ai's enterprise customers in the EU will be directly subject to the EU AI Act starting August 2, 2026, and a no-code LLM fine-tuning platform is exactly the kind of tool where compliance readiness becomes a competitive differentiator.

**Summary**: 113 Python files scanned, 14/57 checks passing (25%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/10 passing |

Strong points first: Record-keeping is solid with logging in 41% of files, tracing infrastructure in 6 files, and retry/backoff logic for API calls. H2O LLM Studio also has AI disclosure patterns and RNG seed determinism across numpy, random, and torch. The biggest gap is Article 14 (human oversight), which scored 0/9. The scanner found no kill switch, no human-in-the-loop gates, no token budget controls, and no execution bounding for agent processes. Article 15 also flagged missing deterministic algorithm flags for PyTorch, which means fine-tuning runs may produce different outputs across GPU types.

**To be clear**: this doesn't mean H2O LLM Studio is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer for OpenAI integrations that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
```

For a platform like H2O LLM Studio where enterprise customers are building production AI, being able to show EU AI Act readiness could be a real selling point. Happy to walk through the full results if useful.

Best,
Jason Shotwell
https://airblackbox.ai
