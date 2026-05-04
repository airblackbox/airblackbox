# Email to PyMC

**To**: thomas@pymc-labs.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PyMC (253 files scanned)

---

Hey Thomas,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran PyMC through the scanner and wanted to share what I found. Bayesian models built on PyMC are showing up inside European banks, insurers, pharma, and energy companies (PyMC Labs' own client base is a leading indicator), and the moment those models inform credit decisions, underwriting, or clinical work, the EU AI Act treats them as Annex III high-risk - which means PyMC's API surface and documentation become the upstream foundation for someone else's Article 9 to Article 15 evidence.

**Summary**: 253 Python files scanned, 16/58 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 0/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 6/11 passing |

The standout result is Article 15 at 6/11 - PyMC checks every box on the determinism side (RNG seeding, deterministic algorithm flags, hardware abstraction, retry/backoff, output validation, prompt-injection defense), which makes sense given how seriously the project takes reproducibility. Article 12 (3/9) reflects logging infrastructure in 25 files plus tracing patterns in 12, plus a passing log-retention setup. The Article 11 result (0/5) is the one worth flagging: the scanner couldn't find a `README.md` (PyMC ships `README.rst`), and the type-annotation coverage is 546/1,718 public functions. Both of those bite EU deployers because Article 11 (Technical Documentation) requires a system description and Article 11 evidence collection is mostly automated against `README.md` plus type signatures. Article 13's "Instructions for Use" check fails for the same reason - it's looking for `INSTRUCTIONS.md` / `USAGE.md` next to the README.

**To be clear**: this doesn't mean PyMC is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Two upstream changes would shift the score meaningfully and unblock a lot of EU enterprise deployers: (1) a `README.md` shim that points at the existing `.rst` content, and (2) type hints on the public `pm.Model`, `pm.sample`, and posterior-predictive entry points. Both are small but they let downstream evidence collection move from "custom rewrite" to "library default." Happy to share the full per-check report, or - given PyMC Labs' EU customer footprint - talk through what an "Article 9 to 15 ready" PyMC distribution might look like for regulated clients.

Best,
Jason Shotwell
https://airblackbox.ai
