# Email to LlamaIndex

**To**: jerry@llamaindex.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for LlamaIndex (4,154 files scanned)

---

Hey Jerry,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran LlamaIndex through the scanner and wanted to share what I found. LlamaIndex is one of the most important pieces of the AI application stack right now, and with KPMG, Salesforce, and Rakuten building on top of it, their compliance teams are going to start asking about EU AI Act readiness well before the August 2026 deadline.

**Summary**: 4,154 Python files scanned, 21/51 checks passing (41%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 5/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

The good news: LlamaIndex is ahead of most frameworks I've scanned. Your documentation is solid (64% docstrings, 95% type hints), and you have real tracing infrastructure with 470 files showing observability patterns. Human oversight is the strongest area at 5/9, with rate limiting, identity binding, and execution timeouts already in place.

The gap: record-keeping is at 2/6, and the two that pass are static patterns. There's no tamper-evident audit chain, which means the tracing data you're already collecting can't be used as evidence in a compliance audit. For a framework processing enterprise documents at scale through LlamaParse, that's the most critical finding.

**To be clear**: this doesn't mean LlamaIndex is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains and compliance hooks with a single import:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Since LlamaIndex integrates deeply with LangChain, this trust layer would give your users a path to audit-ready logging without changing their application code.

Happy to collaborate on improving LlamaIndex's compliance coverage. With your Series A and the enterprise push, getting ahead of this before customers start asking is a strong competitive signal.

Best,
Jason Shotwell
https://airblackbox.ai
