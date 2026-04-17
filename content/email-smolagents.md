# Email to smolagents (Hugging Face)

**To**: clement@huggingface.co
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for smolagents (75 files scanned)

---

Hey Clement,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran smolagents through the scanner and wanted to share what I found. I know Hugging Face has already been thinking about this seriously. Your EU AI Act guide for open-source developers (co-authored with the Linux Foundation and Mozilla) is one of the best resources out there, and the compliance leaderboard on HF Spaces shows you're treating this as a first-class problem. With Hugging Face headquartered in Paris and the August 2026 enforcement deadline four months away, your 50K+ customers building agent systems on smolagents will be asking what compliance looks like at the framework level.

**Summary**: 75 Python files scanned, 13/45 checks passing (29%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

**Where smolagents is already strong:**

Article 15 (Security) is the highlight. The scanner found prompt injection defense patterns in 7 files, structured LLM output validation in 10 files, and retry/backoff logic in 5 files. That puts smolagents ahead of most agent frameworks I've scanned. The type annotation coverage at 65% (271/419 public functions) is solid, and there's already tracing infrastructure in 8 files with production-grade observability, plus agent action audit trails in 5 files. Input validation via Pydantic/dataclass patterns appears in 21 of 75 Python files.

**Where the gaps are:**

Article 14 (Human Oversight) scored 2/9, and for an agent framework, this is the article regulators will focus on first. Specifically:

- No token expiry or execution bounding detected. Agents can run indefinitely without guardrails.
- No action boundary controls. The scanner couldn't find restrictions on what tools/actions an agent can invoke.
- No agent-to-user identity binding. Agent actions aren't tied to an authorizing user, which matters for audit accountability.
- `gradio_ui.py` has possible raw user input flowing into prompts without sanitization.

Article 12 (Record-Keeping) is the other notable gap. While smolagents has tracing infrastructure, there's no tamper-evident audit chain and application logging only appears in 12 of 75 files (16%). For enterprise deployments where customers need to demonstrate compliance to regulators, immutable audit logs are table stakes.

Article 9 (Risk Management) flagged that 15 of 30 files with LLM calls have error handling, but the other 15 don't, including `gradio_ui.py`, `vision_web_browser.py`, and several test files. No risk assessment document was found.

**To be clear**: this doesn't mean smolagents is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it quantifies where the gaps are so engineering teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner detected LangChain usage in smolagents. I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains to every LLM call:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

This wraps the LangChain runtime with structured logging, injection scanning, and cryptographic audit trails, addressing most of the Article 12 and Article 15 runtime gaps in one line. No code changes to smolagents itself.

Given that Hugging Face is already leading the conversation on open-source AI compliance, I'd love to hear how you're thinking about compliance tooling for the agent layer. Happy to walk through the full verbose scan or discuss how the trust layers work.

Best,
Jason Shotwell
https://airblackbox.ai
