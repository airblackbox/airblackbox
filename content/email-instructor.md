# Email to Instructor (567 Labs)

**To**: jason@jxnl.co
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Instructor (368 files scanned)

---

Hey Jason,

I'm Jason (yes, another one), the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Instructor through the scanner and wanted to share what I found. With 6M+ monthly downloads and enterprise teams relying on Instructor for structured LLM extraction, many of those users have EU operations that fall under the EU AI Act enforcement starting August 2, 2026.

**Summary**: 368 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

Instructor scores well in several areas. It has strong input validation via Pydantic in 221 of 368 files (60%), excellent type annotations at 85%, retry/backoff patterns in 46 files, prompt injection defense in 7 files, and structured output validation in 175 files. Article 15 (Security) is the strongest at 3/8 passing. The biggest gap is Article 14 (Human Oversight), where 8 of 9 checks are warnings or failures. For a library that extracts structured data from LLMs at scale, the absence of human approval gates and action boundaries is the area enterprise compliance teams will focus on.

**To be clear**: this doesn't mean Instructor is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner detected Anthropic and OpenAI framework usage. I also built drop-in trust layers that add HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
```

With Instructor's enterprise adoption, this could be a differentiator. Would a quick walkthrough of the findings be useful?

Best,
Jason Shotwell
https://airblackbox.ai
