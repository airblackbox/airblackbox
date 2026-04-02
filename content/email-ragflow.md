# Email to RAGFlow / InfiniFlow Team

**To**: yingfeng.zhang@infiniflow.org (Co-Founder & CEO, confirmed from pre-sales contact)
**Also try**: yingfeng.zhang@infiniflow.ai
**From**: jason.j.shotwell@gmail.com
**Subject**: EU AI Act compliance scan results for RAGFlow (500 files scanned)

---

Hey Yingfeng,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran RAGFlow through the scanner and wanted to share what I found. As a RAG engine processing enterprise documents for 76K+ GitHub stars worth of users, RAGFlow sits right in the crosshairs of the EU AI Act's August 2026 enforcement deadline.

**Summary**: 500 Python files scanned, 7.9% aggregate compliance score (238/3000 checks).

Per-article breakdown:

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1.0% (5/500) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 7.6% (38/500) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 30.6% (153/500) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0.4% (2/500) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 4.8% (24/500) |
| Art. 15 (Security) | Injection defense, output validation | 3.2% (16/500) |

The documentation coverage stands out (Art. 11 at 30.6%), and there's some data governance in place. The biggest concern is record-keeping at 0.4%. For a RAG engine ingesting and retrieving enterprise documents, the EU AI Act specifically requires audit trails that show what data went in, what came out, and when. That's Article 12, and right now only 2 out of 500 files have the patterns the regulation expects.

**To be clear**: this doesn't mean RAGFlow is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer specifically for RAG pipelines that adds HMAC-SHA256 tamper-evident audit chains, input validation, and document provenance tracking:

```python
import air_blackbox
air_blackbox.attach("rag")
```

The audit chain produces cryptographically verifiable records of every retrieval and generation call. Each entry is hash-chained so tampering is detectable. For enterprise customers who need to prove what their RAG system retrieved and generated, this is the kind of evidence that holds up in an audit.

Happy to collaborate on improving RAGFlow's compliance coverage. Given your scale, any improvements would benefit the entire RAG ecosystem.

Best,
Jason Shotwell
https://airblackbox.ai
