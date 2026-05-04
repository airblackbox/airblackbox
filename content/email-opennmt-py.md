# Email to OpenNMT-py

**To**: vince62s@yahoo.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for OpenNMT-py (152 files scanned)

---

Hey Vincent,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran OpenNMT-py through the scanner and wanted to share what I found. OpenNMT-py is one of the older, more battle-tested Python neural MT toolkits, and it's still embedded in a meaningful chunk of European translation infrastructure: SYSTRAN, Ubiqus-lineage shops, public-sector translation pipelines, and EU-funded research consortia. Translation systems sit in an awkward spot under the EU AI Act because Article 50 transparency obligations apply broadly, and any translation model used inside Annex III workflows (immigration, judicial, healthcare triage, employment screening) inherits the full Article 9 to Article 15 stack. Given Seedfall is in Paris, your downstream users sit very close to the AI Office.

**Summary**: 152 Python files scanned, 12/57 checks passing (21%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/10 passing |

The strongest result is Article 12 at 4/9: OpenNMT-py has clean Python logging, real tracing patterns, and an action-level audit trail in the training and inference loops. The lowest-scoring article is Article 15 at 1/10, and most of that is downstream of the scanner not finding ML determinism flags exposed at the API surface (RNG seeding, deterministic algorithms, hardware abstraction). Those are likely already implemented under the hood for reproducibility, but they aren't surfaced as configurable knobs the way EU deployers have to document them. Article 11 (1/5) is the second leverage point: docstring coverage on public functions and a `MODEL_CARD.md` for the trained checkpoints would meaningfully change the upstream story for any EU translation provider citing OpenNMT-py as Article 17 conformity evidence.

**To be clear**: this doesn't mean OpenNMT-py is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Two upstream changes would shift the score and make life easier for every EU MT provider downstream of OpenNMT-py: (1) a `MODEL_CARD.md` template covering intended use, training data summary, known limitations, and language pairs for the canonical recipes, and (2) explicit, documented `seed`, `deterministic`, and `device` configuration knobs surfaced in the public API and CLI. Both are small but they let downstream Article 11 (Technical Documentation) and Article 15 (Accuracy, Robustness) evidence inherit from OpenNMT-py instead of being reconstructed inside each EU translation deployment. Happy to share the full per-check report, or talk through what an "Article 9 to 15 ready" OpenNMT-py distribution would look like for SYSTRAN-lineage and EU public-sector users.

Best,
Jason Shotwell
https://airblackbox.ai
