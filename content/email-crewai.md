# Email to CrewAI

**To**: joao@crewai.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for CrewAI (1,051 files scanned)

---

Hey João,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran CrewAI through the scanner and wanted to share what I found. With 40-60% of Fortune 500 companies using CrewAI and 1.4B agentic automations running monthly, your enterprise customers are going to need to demonstrate EU AI Act readiness by August 2026. PwC, IBM, and Capgemini all have significant EU operations.

**Summary**: 1,051 Python files scanned, 19/51 checks passing (37%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 6/9 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

The standout: human oversight is CrewAI's strongest area at 6/9, which makes sense given the multi-agent architecture with explicit delegation patterns. You have human-in-the-loop patterns, identity binding across 51 files, permission validation, execution timeouts, and action boundaries. That's ahead of every other framework I've scanned.

Documentation is also strong: 74% docstrings and 98% type hints is excellent.

The gap: data governance at 1/5 and risk management at 1/4. For a framework where multiple AI agents autonomously make decisions, delegate tasks, and execute tool calls, the near-zero data governance coverage is the most critical finding. Enterprise customers running regulated workflows through CrewAI will need to show their compliance teams that data handling is governed.

**To be clear**: this doesn't mean CrewAI is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer specifically for CrewAI that adds HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks:

```python
import air_blackbox
air_blackbox.attach("crewai")
```

One import gives every CrewAI agent cryptographically verifiable records of every action, every delegation, and every tool call. That's the kind of evidence enterprise customers need when regulators come asking.

Happy to collaborate on improving CrewAI's compliance coverage. Your framework already has the strongest human oversight patterns I've seen in the agent ecosystem, and closing the data governance gap would make CrewAI the most audit-ready multi-agent framework available.

Best,
Jason Shotwell
https://airblackbox.ai
