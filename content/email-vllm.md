# Email to vLLM

**To**: collaboration@vllm.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for vLLM (2,886 files scanned)

---

Hey Woosuk (and the vLLM team),

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran vLLM through the scanner and wanted to share what I found. vLLM is now the default inference backbone for most self-hosted LLM deployments I see, including a growing number at EU banks, insurers, and public-sector agencies that have very explicit AI Act obligations starting in August 2026. When those teams go through a compliance review, the inference layer is one of the first places auditors look.

**Summary**: 2,886 Python files scanned, 16/45 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 4/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

This is actually the highest score I have seen so far across ~50 projects in this batch. Article 14 (Human Oversight) stood out in particular — the scanner picked up rate limiting and execution bounding patterns that most frameworks simply do not have. The largest remaining gaps are in Article 10 (Data Governance) and Article 11 (Documentation) where the scanner did not detect explicit schema validation on inputs, PII handling patterns, or consistent system-level documentation for the serving layer.

**To be clear**: this doesn't mean vLLM is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer for OpenAI-compatible endpoints that adds HMAC-SHA256 tamper-evident audit chains around every request and response:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Since vLLM ships an OpenAI-compatible server, that trust layer drops in cleanly in front of the inference layer and gives EU operators something concrete to point their auditors at. Happy to send the full per-file report, or to open a PR adding an "EU AI Act notes" section to the docs if that would be useful.

Best,
Jason Shotwell
https://airblackbox.ai
