# Email to Langfuse

**To**: marc@langfuse.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Langfuse Python SDK (432 files scanned)

---

Hey Marc,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran langfuse-python through the scanner and wanted to share what I found. Langfuse sits on the observability path for a lot of teams shipping LLM apps into production, and with the August 2, 2026 EU AI Act enforcement deadline, your users are going to start asking you what parts of Articles 9 through 15 the SDK already helps them cover. The tracing and audit story in Langfuse is genuinely strong, so some of these answers look great.

**Summary**: 432 Python files scanned, 19/58 checks passing (33%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 5/11 passing |

The good news: Art. 12 is your strongest area, as expected. Tracing patterns in 158 files, action-level audit logging, type hints at 85% coverage on public functions. That is rare in observability SDKs and exactly the kind of evidence downstream teams will cite in their own conformity assessments.

The biggest gap the scanner flagged is Art. 12's tamper-evident audit chain check. Langfuse captures the traces, but right now nothing cryptographically binds them. For high-risk AI systems under Article 12, logs need to be resistant to modification, and the scanner also flagged agent identity binding (Agent Action Receipts / Session Continuity Certificates) as missing in langfuse/_client/client.py. If Langfuse added an optional HMAC-SHA256 chain over its existing trace format, every team using Langfuse for enterprise workloads would inherit that evidence by default.

**To be clear**: this doesn't mean Langfuse is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how many teams ship Langfuse into the audit path, I'd love to compare notes on what a "trust layer" for the Langfuse Python SDK could look like. Happy to send a draft spec if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
