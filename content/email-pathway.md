# Email to Pathway

**To**: zuzanna@pathway.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Pathway (457 files scanned)

---

Hey Zuzanna,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Pathway through the scanner and wanted to share what I found. With Pathway headquartered in Paris and powering live RAG and data pipelines for enterprise customers across the EU, the AI Act's August 2026 enforcement window is going to put a very direct spotlight on frameworks that sit in the hot path of production data.

**Summary**: 457 Python files scanned, 12/45 checks passing (27%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Pathway scored higher than most of the agent frameworks I have scanned recently, particularly on Record-Keeping and Human Oversight where the streaming persistence model gives you some natural wins. The biggest gaps are in Article 10 (Data Governance) and Article 15 (Security): the scanner did not detect explicit schema validation at ingest, prompt injection defenses, or structured LLM output validation. Given that Pathway is typically the surface where untrusted user data first meets the LLM, those are the checks EU compliance reviewers tend to zoom in on first.

**To be clear**: this doesn't mean Pathway is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer for RAG pipelines that adds HMAC-SHA256 tamper-evident audit chains on top of your retrieve-and-generate path:

```python
import air_blackbox
air_blackbox.attach("rag")
```

Since Pathway is already pitched as the live data layer for RAG, stapling an audit chain onto it would give your enterprise users something concrete to hand their auditors. Happy to send the full per-file report, or to jump on a quick call if any of this is useful for the roadmap.

Best,
Jason Shotwell
https://airblackbox.ai
