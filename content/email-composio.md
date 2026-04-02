# Email to Composio

**To**: karan@composio.dev
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Composio (169 files scanned)

---

Hey Karan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Composio through the scanner and wanted to share what I found. With 27K+ stars and integrations across LangChain, CrewAI, OpenAI Agents SDK, and Google ADK, Composio is becoming the default agent tooling layer. As your enterprise customers deploy agents that take real-world actions in the EU, the compliance question is going to come up fast.

**Summary**: 169 Python files scanned, 13/45 checks passing (29%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 3/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/7 passing |

Composio's documentation game is strong: 62% docstring coverage, 88% type hints, and you already have human-in-the-loop patterns, token expiry controls, and action boundaries in the code. That's better than most projects I've scanned. The main gaps are in record-keeping (only 4% of files have logging) and data governance documentation, which regulators will specifically ask about for agent systems that interact with external services.

**To be clear**: this doesn't mean Composio is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains for agent frameworks:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Given that Composio already supports multiple agent frameworks, this could be an interesting add for enterprise customers who need compliance artifacts. Would love to hear your thoughts.

Best,
Jason Shotwell
https://airblackbox.ai
