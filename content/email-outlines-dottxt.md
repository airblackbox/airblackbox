# Email to Outlines (.txt / dottxt)

**To**: remi@dottxt.co
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Outlines (119 files scanned)

---

Hey Remi,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Outlines through the scanner and wanted to share what I found. As a Paris-based, VC-backed company with enterprise customers using structured generation in production, you're directly subject to EU AI Act enforcement starting August 2, 2026.

**Summary**: 119 Python files scanned, 8/45 checks passing (18%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Good news first: Outlines has solid input validation via Pydantic across 62 of 119 files (52%), strong type annotations at 73%, and LLM output validation in 14 files. Those are real strengths. The biggest gap is record-keeping (Article 12), where zero checks pass. For a library that enterprise teams use to constrain LLM outputs in production, the lack of structured logging and audit trails is the area that would get flagged first by a compliance auditor.

**To be clear**: this doesn't mean Outlines is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner detected Anthropic and OpenAI framework usage in Outlines. I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Given the August 2026 deadline and the fact that .txt is EU-domiciled, would it be worth a quick call to walk through the findings? Happy to dig into the Article 12 gaps specifically.

Best,
Jason Shotwell
https://airblackbox.ai
