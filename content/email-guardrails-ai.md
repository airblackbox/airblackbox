# Email to Guardrails AI

**To**: shreya@getguardrails.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Guardrails (352 files scanned)

---

Hey Shreya,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Guardrails framework through the scanner and wanted to share what I found. This one felt especially relevant because Guardrails and AIR Blackbox are working on related problems from different angles. You're validating LLM outputs against safety specs; we're mapping codebases to EU AI Act requirements. Enterprise teams using Guardrails in the EU will need to demonstrate both output safety and regulatory compliance by August 2, 2026.

**Summary**: 352 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/5 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/4 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/4 passing |

The bright spot: Guardrails has actual PII detection/redaction in 6 files (library-grade), which puts it ahead of most projects I've scanned on Article 10 data governance. Injection defense and output validation are solid too, which makes sense given what the framework does. The gaps are in documentation (33% docstring coverage, no model card) and record-keeping (no structured audit trail). For a framework whose value proposition is LLM safety, having the compliance documentation to back that up would strengthen the story significantly.

**To be clear**: this doesn't mean Guardrails is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner detected LangChain and OpenAI usage. I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

There might be an interesting integration angle here. Guardrails handles the output validation side; AIR Blackbox handles the compliance audit side. Happy to explore that if it's interesting.

Best,
Jason Shotwell
https://airblackbox.ai
