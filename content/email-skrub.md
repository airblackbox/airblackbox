# Email to skrub (:probabl.)

**To**: yann@probabl.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for skrub (171 files scanned)

---

Hey Yann,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran skrub through the scanner and wanted to share what I found. Paris-based, commercialized through :probabl., sitting on the scikit-learn lineage, and squarely aimed at the data preparation layer where a huge amount of EU-regulated tabular ML work happens. Article 10 (Data Governance) reads almost like it was written with tools like skrub in mind, and the August 2, 2026 enforcement deadline means downstream users are going to be asking "can I defend my data-prep pipeline" pretty soon. I noticed your team's recent AI-BOM post on the Probabl blog, so this is probably aligned with thinking you're already doing.

**Summary**: 171 Python files scanned, 10/58 checks passing (17%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 0/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

Two quick notes on how the scanner sees skrub, because some of these are scanner quirks worth calling out:

1. Art. 11 shows 0/5 partly because skrub uses README.rst rather than README.md, and the type-annotation check counts PEP-484 hints rather than numpy-style docstrings, so the "2/599 functions have type hints" number undersells what's actually documented. That's a scanner limitation I should fix on my side, not a real gap.
2. The real Art. 11 gap is that there's no MODEL_CARD.md or capability-and-limitation doc at the repo root. For a preprocessing library feeding regulated models, even a short capabilities doc that says "skrub does X, does not do Y, edge cases Z" becomes valuable paper for downstream Art. 13 transparency compliance.

The more interesting finding is Art. 12. There's no Python logging, structlog, or OpenTelemetry patterns detected across the 171 files, and Art. 12 is what regulators lean on when they ask "show me the audit trail for how this feature got into the model." For a preprocessing library, even a lightweight optional transform-level logger would move this meaningfully.

**To be clear**: this doesn't mean skrub is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given :probabl.'s mandate around the scikit-learn ecosystem and enterprise commercial support, a clean Art. 10 and Art. 12 posture on skrub would be a strong proof point for the exact enterprise customers who need scikit-learn lineage plus EU AI Act defensibility. Happy to share the full report or talk through the audit-trail angle in particular.

Best,
Jason Shotwell
https://airblackbox.ai
