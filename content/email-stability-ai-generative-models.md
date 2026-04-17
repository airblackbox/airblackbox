# Email to Stability AI (generative-models)

**To**: prem@stability.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for generative-models (73 files scanned)

---

Hey Prem,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Stability AI's generative-models repo through the scanner and wanted to share what I found. As a London-headquartered company building generative AI models, Stability AI falls directly under EU AI Act jurisdiction with enforcement starting August 2, 2026.

**Summary**: 73 Python files scanned, 5/45 checks passing (11%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/8 passing |

On the positive side, the repo has tracing patterns in 6 files (Article 12), logging in 8 of 73 files, and a README for system documentation. The biggest gaps are in Article 14 (Human Oversight) and Article 15 (Security), where zero static checks pass. For models that generate images and video used by millions of downstream users, the absence of human approval gates, usage limits, and output validation are the areas that compliance teams will flag first.

**To be clear**: this doesn't mean generative-models is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given the August 2026 deadline and Stability AI's UK/EU presence, would it be worth connecting to walk through the findings in more detail?

Best,
Jason Shotwell
https://airblackbox.ai
