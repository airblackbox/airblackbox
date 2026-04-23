# Email to Soda Core (Soda.io)

**To**: maarten@soda.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for soda-core (267 files scanned)

---

Hey Maarten,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran soda-core through the scanner and wanted to share what I found. Soda sits in an almost perfect spot for the EU AI Act moment: data contracts and data quality are exactly what Article 10 (data governance) asks providers of high-risk AI systems to evidence, and Brussels-headquartered tooling is going to get leaned on first by EU banks, insurers, and health systems for that posture. With NannyML now inside Soda, the ML-monitoring and data-quality stories are about to be told as one Article 10 plus Article 15 answer, which I think is a strong position.

**Summary**: 267 Python files scanned, 18/57 checks passing (32%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 2/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The strong side: Art. 12 at 4/9 is one of the better record-keeping scores I've seen in this batch. Structured logging and retention-style patterns are present in enough of the engine that the scanner picked them up without any runtime data. Art. 15 at 4/10 also registers retry/backoff logic and some output validation, which is in line with what you'd expect from a mature data-quality engine.

The result worth flagging is Art. 10 at 1/5, which is ironic given that Soda's product surface is literally data governance. The scanner didn't pick up explicit PII detection patterns or data-minimization documentation in the repo, likely because those live in the SCL (Soda Checks Language) definitions users write, not in the engine code. A short section in the README or a DATA_GOVERNANCE.md that maps Soda Checks types (missing, schema, duplicate, freshness) to Article 10 sub-requirements would convert that 1/5 into something closer to 4/5, and it would give your EU enterprise buyers a straight-line answer for their conformity assessments.

Art. 14 at 2/9 is the other lever. Soda already has the "alert, human reviews, human approves or dismisses" pattern in the product; surfacing it explicitly as a human-oversight pattern (maybe a brief "human oversight in soda-core" page) would register.

**To be clear**: this doesn't mean soda-core is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

A Brussels-based data-contracts engine that can cite its own Article 10 and Article 15 posture is the kind of thing EU banks will reach for first when their procurement team hands them the August 2, 2026 checklist. Happy to share the full scan output, open a PR on the docs, or map Soda Checks to the six Articles explicitly if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
