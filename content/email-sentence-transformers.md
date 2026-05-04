# Email to sentence-transformers

**To**: tom.aarsen@huggingface.co
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for sentence-transformers (428 files scanned)

---

Hey Tom,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran sentence-transformers through the scanner and wanted to share what I found. The library has effectively become the default embedding stack inside European RAG and search systems (banks, healthcare, legal, government), and now that it sits under the Hugging Face org and you're maintaining it from the EU, the same Article 9 to Article 15 obligations that apply to any high-risk component land on whoever ships an embedding pipeline built on top of this code.

**Summary**: 428 Python files scanned, 15/58 checks passing (26%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

26% is one of the better embedding-library scores I've seen, and the Article 12 result (4/9) reflects how much structured logging is already in the training and evaluation paths. The interesting gap is Article 15, where the scanner picked up some output-validation patterns (3/11) but still flagged missing input-shape validation around the encode and similarity entry points. For European deployers, the second item that tends to bite is Article 14: there's no built-in low-confidence threshold or human-review hook on similarity outputs, so a downstream RAG pipeline using this for retrieval has to wire Article 14 evidence elsewhere. Both are surface-level things that wouldn't change the API.

**To be clear**: this doesn't mean sentence-transformers is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how universally this library is used inside EU RAG stacks now, even small upstream patterns (a documented confidence threshold parameter on `SentenceTransformer.encode`, a structured-record helper in the trainer) would let downstream Article 14 and Article 12 evidence collection move from "custom wrapper" to "library default." Happy to share the full per-check report or open a draft issue at huggingface/sentence-transformers if you'd find that useful.

Best,
Jason Shotwell
https://airblackbox.ai
