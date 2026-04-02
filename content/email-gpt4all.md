# Email to GPT4All (Nomic AI)

**To**: andriy@nomic.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for GPT4All (21 files scanned)

---

Hey Andriy,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran GPT4All through the scanner and wanted to share what I found. With 77K+ GitHub stars and 250K+ monthly active users, GPT4All is one of the most widely used local LLM runtimes out there. As enterprise teams adopt it for on-prem deployments in the EU, the compliance surface is going to matter.

**Summary**: 21 Python files scanned, 6/44 checks passing (14%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/7 passing |

The good news: GPT4All already has solid type annotation coverage (66%) and fallback/recovery patterns in place. The biggest gap is in record-keeping and human oversight. There's no structured logging framework detected and no audit trail for model interactions, which are exactly the patterns EU regulators will look for as the August 2026 enforcement deadline approaches.

**To be clear**: this doesn't mean GPT4All is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Would love to hear if this is useful. Happy to walk through the results or discuss what a compliance-ready GPT4All deployment would look like for enterprise users.

Best,
Jason Shotwell
https://airblackbox.ai
