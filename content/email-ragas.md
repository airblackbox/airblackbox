# Email to Ragas

**To**: shahul@ragas.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Ragas (387 files scanned)

---

Hey Shahul,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Ragas through the scanner and wanted to share what I found. With 12.9K+ stars, YC backing, and enterprises like AWS, Microsoft, and Databricks using Ragas to evaluate their RAG pipelines, you're sitting at a really interesting intersection. EU AI Act Article 15 specifically requires accuracy testing for high-risk AI systems, and that's exactly what Ragas does. Compliance-conscious teams are going to come looking for you.

**Summary**: 387 Python files scanned, 14/45 checks passing (31%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 3/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/7 passing |

Ragas already has strong fundamentals: 60% docstring coverage, 84% type hints, production-grade tracing in 7 files, action-level audit logging, and data retention/TTL policies. The biggest opportunity is in human oversight patterns and risk management documentation. As enterprise customers start asking "can we use Ragas to demonstrate Article 15 compliance?", having the framework itself pass compliance checks becomes a powerful selling point.

**To be clear**: this doesn't mean Ragas is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There might be something interesting in combining our tools: AIR Blackbox scans for compliance gaps, Ragas evaluates accuracy. Together they could cover most of Article 15. Happy to explore if that's interesting.

Best,
Jason Shotwell
https://airblackbox.ai
