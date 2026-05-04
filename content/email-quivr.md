# Email to Quivr

**To**: stan@quivr.app
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Quivr (77 files scanned)

---

Hey Stan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Quivr through the scanner and wanted to share what I found. Quivr is one of the most-installed open-source "personal second brain" stacks on GitHub, and the moment a French or wider EU customer starts pointing it at HR documents, contracts, or healthcare notes, the deployer inherits Article 9 to Article 15 obligations on top of Quivr's own RAG pipeline. Since Quivr is YC W24 out of Paris, you sit closer to the AI Office than almost anyone else on this list.

**Summary**: 77 Python files scanned, 14/58 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 5/11 passing |

The strongest result is Article 15 at 5/11: Quivr passes on output parsing/validation, retry/backoff, and the determinism checks that don't apply to a non-training stack, and Pydantic input validation shows up in 15/77 files. Article 12 (3/9) is also working in your favor, with Python logging in 14 files, real tracing patterns in 6 files, and an action-level audit trail in your agent path. The Article 14 result (0/9 passing) is the one worth flagging: the scanner sees autonomous agent patterns in `examples/simple_question_megaparse.py` and `examples/pdf_parsing_tika.py` but no kill-switch, no token expiry / execution bounding, no agent-to-user identity binding, and no explicit per-action budget controls. For an EU enterprise customer running Quivr against their own data, that's the bottleneck on conformity evidence under Article 14 (Human Oversight) and Article 12 traceability.

**To be clear**: this doesn't mean Quivr is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The scanner also detected anthropic, langchain, and openai usage in Quivr. There are drop-in trust layers for each that add HMAC-SHA256 tamper-evident audit chains, identity binding, and runtime injection scanning without changing your code:

```python
import air_blackbox
air_blackbox.attach("langchain")  # or "anthropic" / "openai"
```

That alone closes a chunk of Article 12 (Record-Keeping) and Article 15 (runtime injection protection) in one import. Happy to share the full per-check report, or talk through what an "Article 9 to 15 ready" Quivr distribution might look like for your enterprise EU pilots.

Best,
Jason Shotwell
https://airblackbox.ai
