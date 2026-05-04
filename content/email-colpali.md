# Email to ColPali (Illuin Technology)

**To**: quentin.mace@illuin.tech
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for ColPali (138 files scanned)

---

Hey Quentin,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran ColPali through the scanner and wanted to share what I found. Paris-based, built out of the academic-industry partnership between CentraleSupélec and Illuin, and now the de facto reference stack for vision-language document retrieval. ColPali is quickly becoming the thing teams reach for when they need visual-document RAG, which means its defaults will shape how those downstream RAG systems hit the EU AI Act's enforcement deadline on August 2, 2026.

**Summary**: 138 Python files scanned, 9/58 checks passing (16%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/11 passing |

The repo's a clean research-to-prod codebase, and the scanner caught that. Type annotations are present, hardware abstraction is clean, and Art. 11 is already partly there.

The two articles worth flagging: Art. 9 and Art. 14. For Art. 9, the two LLM-calling scripts (scripts/api_call.py and scripts/reasoning_queries.py) have no error handling around the external calls, which means a transient API failure surfaces as an uncaught exception rather than a logged fallback. For Art. 14, there's no kill switch or token-expiry / execution-bounding on any of the retrieval loops. Those are both straightforward to add and move the score materially. A second angle on Art. 15 is that torch is in use but the deterministic-algorithm flags and RNG seeds aren't set, which means reviewers benchmarking ColPali for regulated deployments (legal, healthcare, public sector) won't be able to reproduce results across hardware.

**To be clear**: this doesn't mean ColPali is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Happy to send the full report or talk through the determinism checks specifically. That's the angle that tends to matter most for vision retrievers that end up inside regulated document pipelines.

Best,
Jason Shotwell
https://airblackbox.ai
