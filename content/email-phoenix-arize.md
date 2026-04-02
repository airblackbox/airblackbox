# Email to Phoenix (Arize AI)

**To**: jason@arize.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Phoenix (1,015 files scanned)

---

Hey Jason,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Phoenix through the scanner and wanted to share what I found. With 2M+ monthly downloads and enterprise customers deploying Phoenix for AI observability, your users operating in the EU will increasingly need to demonstrate compliance with the EU AI Act (enforcement begins August 2026).

**Summary**: 1,015 Python files scanned, 17/45 checks passing (37.8%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 5/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

The good news: Phoenix already has strong human oversight patterns with rate limiting controls found in 22 files, permission validation, and execution bounding in 25 files. Type hint coverage is excellent at 94%. The biggest gap is documentation coverage, with only 27% of functions having docstrings, which maps directly to Art. 11 requirements. Record-keeping also has room to grow since logging exists but lacks tamper-evident audit chains.

**To be clear**: this doesn't mean Phoenix is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Phoenix is an observability platform, there's a natural fit: your users already care about monitoring and tracing their AI systems. Compliance visibility is the next logical layer. Happy to chat about how we might collaborate, or just wanted to put this on your radar as the August 2026 deadline approaches.

Best,
Jason Shotwell
https://airblackbox.ai
