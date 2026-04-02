# Email to Ivy (Unify)

**To**: daniel@unify.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Ivy (1,473 files scanned)

---

Hey Daniel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Ivy through the scanner and wanted to share what I found. As a London-based company building the unified ML framework, Unify sits squarely in the EU AI Act's scope. With the August 2, 2026 enforcement deadline approaching, the compliance patterns in your codebase are worth looking at now, especially since developers building on Ivy inherit your framework's compliance posture.

**Summary**: 1,473 Python files scanned, 7/45 checks passing (16%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/7 passing |

Ivy has solid foundations: fallback patterns in 6 files, retry/backoff logic, and data retention patterns across 7 files. The biggest gap is documentation coverage, where 24% of public functions have docstrings and 45% have type hints. For a framework that wraps multiple ML backends, improving these numbers would strengthen both the developer experience and the Article 11 compliance story.

**To be clear**: this doesn't mean Ivy is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

  pip install air-blackbox
  air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally. No data leaves your machine.

Would be happy to walk through the results. As a framework layer, Ivy has an interesting opportunity to surface compliance metadata to downstream users, which could be a differentiator as the EU AI Act takes effect.

Best,
Jason Shotwell
https://airblackbox.ai
