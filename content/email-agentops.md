# Email to AgentOps

**To**: alex@agentops.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for AgentOps (501 files scanned)

---

Hey Alex,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran AgentOps through the scanner and wanted to share what I found. AgentOps is already doing agent observability, cost tracking, and session replay. That puts you closer to EU AI Act compliance than almost any other project I've scanned. Article 12 (record-keeping) and Article 14 (human oversight) are the hardest checks for most teams, and you're already building the infrastructure.

**Summary**: 501 Python files scanned, 19/45 checks passing (42%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 6/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/7 passing |

This is one of the strongest scans I've seen. 74% docstring coverage, 72% type hints, logging in 27% of files, tracing patterns in 202 files, consent management, human oversight, token scope validation, identity binding, and action-level audit trails across 28 files. The remaining gaps are mostly in formal risk assessment documentation, data governance docs, and GDPR-specific patterns.

**To be clear**: this doesn't mean AgentOps is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There's a natural alignment between what AgentOps tracks at runtime and what AIR Blackbox checks for at the code level. Your session data could feed directly into compliance reports. Would be interested to explore whether an integration makes sense. Happy to jump on a call if you're curious.

Best,
Jason Shotwell
https://airblackbox.ai
