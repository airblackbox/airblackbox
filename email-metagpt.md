# Email to MetaGPT / DeepWisdom

**To**: alexanderwu@deepwisdom.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for MetaGPT (500 files scanned)

---

Hey Alexander,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran MetaGPT through the scanner and wanted to share what I found. MetaGPT is one of the most ambitious multi-agent frameworks out there, simulating entire software teams with autonomous agents. That level of agent orchestration creates a large compliance surface area, and your enterprise users are going to need to demonstrate EU AI Act readiness by August 2026.

**Summary**: 500 Python files scanned (890 total), 5.9% aggregate compliance score (178/3000 checks).

Per-article breakdown:

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0.4% (2/500) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 0.8% (4/500) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 26.0% (130/500) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0.2% (1/500) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 7.2% (36/500) |
| Art. 15 (Security) | Injection defense, output validation | 1.0% (5/500) |

Documentation is strong (Art. 11 at 26%), and there are some human oversight patterns in place (7.2%). The biggest gaps are record-keeping (Art. 12 at 0.2%, meaning 1 file out of 500 has structured audit logging) and data governance (Art. 10 at 0.8%). For a framework where multiple AI agents autonomously generate code, make decisions, and hand off tasks to each other, the near-zero audit trail is the most critical finding.

**To be clear**: this doesn't mean MetaGPT is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers for OpenAI SDK and multi-agent frameworks that add HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks:

```python
import air_blackbox
air_blackbox.attach("openai")
```

For a multi-agent system like MetaGPT, the audit chain is especially valuable. It produces cryptographically verifiable records of every agent action, every LLM call, and every handoff between roles. Each entry is hash-chained so tampering is detectable. That's the kind of evidence enterprise customers need when regulators come asking.

Happy to collaborate on improving MetaGPT's compliance coverage. Your framework represents one of the most complex multi-agent architectures in the Python ecosystem, and getting it audit-ready would be a strong signal to the market.

Best,
Jason Shotwell
https://airblackbox.ai
