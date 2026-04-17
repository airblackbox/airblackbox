# Email to spaCy (Explosion AI)

**To**: ines@explosion.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for spaCy (874 files scanned)

---

Hey Ines,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran spaCy through the scanner and wanted to share what I found. Since Explosion is based in Berlin and spaCy is embedded in production pipelines at large EU enterprises (including several banks and public-sector deployments I've seen in the wild), Article 9 through 15 obligations under the EU AI Act land directly on the stack spaCy underpins.

**Summary**: 874 Python files scanned, 9/45 checks passing (20%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/8 passing |

Documentation and type-hint coverage is unsurprisingly one of the stronger areas (spaCy has always set the bar there). The biggest gap is Article 14 (Human Oversight), where the scanner found no explicit approval workflows, token scope validation, or agent-action boundaries. That makes sense for a library that ships pipeline components rather than agents, but it is also the area where downstream users most often get flagged during compliance reviews because they inherit whatever patterns the upstream library normalizes.

**To be clear**: this doesn't mean spaCy is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how many EU teams pin spaCy as a core dependency, even a short "AI Act notes" section in the docs (or a compliance badge on the README) could save thousands of downstream teams from answering the same questionnaire cold. Happy to contribute a PR if that would be useful, or just share the full report if you want to eyeball it.

Best,
Jason Shotwell
https://airblackbox.ai
