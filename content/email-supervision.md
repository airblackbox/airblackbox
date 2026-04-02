# Email to supervision (Roboflow)

**To**: joseph@roboflow.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for supervision (169 files scanned)

---

Hey Joseph,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran supervision through the scanner and wanted to share what I found. With 36K+ GitHub stars and adoption across the Fortune 100, many of your enterprise users have EU operations that bring the EU AI Act into scope. Having compliance patterns baked into the library they depend on is a strong differentiator.

**Summary**: 169 Python files scanned, 7/44 checks passing (16%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/7 passing |

Your documentation game is genuinely impressive: 98% type hint coverage and 66% docstring coverage are the best numbers I've seen across any project I've scanned. The biggest gap is Article 9 (risk management), where no fallback or retry patterns were detected. For a library used in real-time video inference, having documented error recovery patterns would strengthen compliance posture considerably.

**To be clear**: this doesn't mean supervision is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

  pip install air-blackbox
  air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally. No data leaves your machine.

Would be happy to walk through the results. Given how many enterprise teams build on supervision, this could be a meaningful signal for your commercial users navigating EU compliance requirements.

Best,
Jason Shotwell
https://airblackbox.ai
