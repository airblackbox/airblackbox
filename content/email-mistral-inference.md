# Email to Mistral AI (mistral-inference)

**To**: arthur@mistral.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for mistral-inference (14 files scanned)

---

Hey Arthur,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran mistral-inference through the scanner and wanted to share what I found. As a Paris-based AI company building the foundation models that thousands of EU enterprises rely on, Mistral is going to be front and center when the EU AI Act enforcement deadline hits on August 2, 2026. Your downstream users will be looking to you for compliance signals.

**Summary**: 14 Python files scanned, 5/47 checks passing (11%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/8 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/7 passing |

The good news: type annotations are at 100% across all public functions, and input validation via Pydantic is solid in 5 of 14 files. The biggest gaps are in Articles 9 and 14. There's no risk classification document (required by Article 6), no fallback/recovery patterns, and no human oversight mechanisms. For an inference library that enterprise teams will deploy in production, those are the patterns regulators will look for.

**To be clear**: this doesn't mean mistral-inference is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Mistral is positioned as Europe's leading AI company, having a public compliance posture ahead of the August deadline could be a real differentiator. Happy to share more details on what the scanner found or talk about how other teams are approaching this.

Best,
Jason Shotwell
https://airblackbox.ai
