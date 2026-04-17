# Email to txtai (NeuML)

**To**: dave@neuml.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for txtai (363 files scanned)

---

Hey Dave,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran txtai through the scanner and wanted to share what I found. With 12K+ stars and adoption across semantic search and LLM orchestration use cases, txtai is exactly the kind of framework enterprise teams are building on. When those teams have EU operations, compliance questions follow.

**Summary**: 363 Python files scanned, 7/44 checks passing (16%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 0/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/7 passing |

Your docstring coverage is excellent at 80%, which is one of the strongest numbers I've seen across any project. Fallback patterns and output validation are also solid. The biggest opportunity is type hints (currently 4%) and structured input validation. For a framework that handles embeddings and LLM orchestration, adding Pydantic models or dataclass validation to the agent and workflow layers would move the needle significantly on both Article 10 and Article 11.

**To be clear**: this doesn't mean txtai is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer for OpenAI that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
```

The scanner detected OpenAI usage in txtai. The trust layer wraps every API call with compliance logging, zero code changes needed.

Would love to hear your take on this. Happy to dig into any of the findings.

Best,
Jason Shotwell
https://airblackbox.ai
