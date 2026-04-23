# Email to Verba (Weaviate)

**To**: bob@weaviate.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Verba (55 files scanned)

---

Hey Bob,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Verba through the scanner and wanted to share what I found. Verba sits in an interesting spot: it's Weaviate's flagship open-source RAG surface, and because it's what a lot of EU teams clone first when they're standing up "talk to our docs" internally, it becomes the de facto pattern they ship. With the August 2, 2026 enforcement deadline coming up and Verba being the most visible RAG reference app out of Amsterdam, the scan results are going to reflect on the broader Weaviate ecosystem as well.

**Summary**: 55 Python files scanned, 11/57 checks passing (19%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The brightest spot is Art. 15: retry/backoff patterns are present in four files and the deterministic-flag checks come back clean because Verba doesn't pin an ML framework runtime directly. Art. 11 gets half credit for README coverage and type hints at 68%.

The biggest gap is Art. 12 record-keeping (1/9). Verba today doesn't have structured Python logging or an audit trail around the agent-style actions in goldenverba/server/api.py, which is the exact surface regulators will want replayable when a RAG response goes sideways. Article 12 is specifically about being able to reconstruct what the system did and why; adding a JSON logger around the ingestion pipeline, query path, and tool calls would move this from 1/9 to something closer to 5/9 on a single PR.

Art. 14 (human oversight) is the other one worth a look: 0/9 today. Verba is operator-run, but some lightweight rate-limit or approval signals on the generation endpoint would register here.

**To be clear**: this doesn't mean Verba is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner also picked up LangChain and Google ADK usage in Verba. I maintain drop-in trust layers for both that add HMAC-SHA256 tamper-evident audit chains and close out most of Art. 12:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Given where Weaviate sits in the EU vector database story, it might be worth having a simple compliance posture on Verba so Dutch and German users can point to it when their procurement teams ask. Happy to share the full scan output or open a PR that adds structured logging plus a short AI_GOVERNANCE.md if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
