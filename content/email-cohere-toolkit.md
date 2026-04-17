# Email to Cohere Toolkit

**To**: aidan@cohere.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Cohere Toolkit (345 files scanned)

---

Hey Aidan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Cohere Toolkit through the scanner and wanted to share what I found. With Cohere's enterprise customer base spanning multiple continents, many of those deployments involve EU operations subject to EU AI Act enforcement starting August 2, 2026. The toolkit is what those teams use to build RAG applications, so its compliance posture matters.

**Summary**: 345 Python files scanned, 8/44 checks passing (18%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/7 passing |

Cohere Toolkit has some solid foundations. It has strong type annotations at 84%, good tracing patterns in 7 files, token expiry/execution bounding in 11 files, and LLM output validation in 10 files. The biggest gap is around GDPR data protection (0/8 checks passing) and the record-keeping article (Article 12), where application logging covers only 14% of files. For a RAG toolkit that processes enterprise documents and user queries, the absence of PII handling patterns and data governance documentation is the area that will draw the most scrutiny from EU compliance teams.

**To be clear**: this doesn't mean Cohere Toolkit is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner detected LangChain framework usage in the toolkit. I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Given Cohere's enterprise positioning and EU customer base, would it be worth a quick call to walk through the findings?

Best,
Jason Shotwell
https://airblackbox.ai
