# Email to Browser Use Team

**To**: gregor@browser-use.com (confirmed), magnus@browser-use.com (confirm before sending)
**From**: jason.j.shotwell@gmail.com
**Subject**: EU AI Act compliance scan results for Browser Use (362 files scanned)

---

Hey Gregor and Magnus,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Browser Use through the scanner and wanted to share what I found. With 79K+ stars and YC backing, Browser Use is one of the most widely deployed AI agent frameworks out there, which means your users are going to be asking about EU AI Act readiness as August 2026 gets closer.

**Summary**: 362 Python files scanned, 9.4% aggregate compliance score (205/2172 checks).

Per-article breakdown:

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1.1% (4/362) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 5.0% (18/362) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 26.0% (94/362) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0.3% (1/362) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 12.2% (44/362) |
| Art. 15 (Security) | Injection defense, output validation | 12.2% (44/362) |

The documentation coverage is solid (Art. 11 at 26%), and there are some human oversight and security patterns already in place. The biggest gaps are record-keeping (Art. 12 at 0.3%) and risk management (Art. 9 at 1.1%). For a browser automation agent that interacts with live web pages and user data, the near-zero audit trail is the most actionable finding.

**To be clear**: this doesn't mean Browser Use is non-compliant. The scanner checks for technical patterns that map to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer for LangChain (which Browser Use builds on) that adds audit logging, input validation, and oversight hooks. Single import:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Happy to collaborate on improving coverage. No pitch, just one open-source maintainer to another.

Best,
Jason Shotwell
https://airblackbox.ai
