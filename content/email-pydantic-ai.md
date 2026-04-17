# Email to PydanticAI

**To**: samuel@pydantic.dev
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PydanticAI (488 files scanned)

---

Hey Samuel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran PydanticAI through the scanner and wanted to share what I found. Given that PydanticAI powers agent workflows across OpenAI, Anthropic, and Gemini integrations, enterprise teams building with it in the EU will need to demonstrate compliance when enforcement starts August 2, 2026. Compliance-readiness baked into the framework itself would be a huge selling point.

**Summary**: 488 Python files scanned, 17/44 checks passing (39%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/5 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/4 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/4 passing |

Input validation is where PydanticAI really shines, which shouldn't surprise anyone given the Pydantic DNA. 429 out of 488 Python files have schema enforcement, which is phenomenal. Injection defense patterns were found in 25 files, and output validation in 63 files. Your security posture is solid. The biggest gap is in data governance documentation and PII handling. The scanner found PII-aware variable names in 6 files but no detection or redaction library. For an agent framework handling user prompts, that's the area with the most exposure.

**To be clear**: this doesn't mean PydanticAI is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

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
air_blackbox.attach("anthropic")
```

Given PydanticAI's position as the type-safe agent framework, baking in compliance tooling could be a natural extension of the "do it the right way" philosophy.

Best,
Jason Shotwell
https://airblackbox.ai
