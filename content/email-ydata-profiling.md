# Email to YData (ydata-profiling)

**To**: goncalo.ribeiro@ydata.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for ydata-profiling (285 files scanned)

---

Hey Goncalo,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran ydata-profiling through the scanner and wanted to share what I found. ydata-profiling is the default Python EDA + data quality pass that sits in front of an enormous number of EU ML pipelines, especially in regulated industries: banks doing credit modeling, insurers profiling actuarial data, healthcare teams preparing tabular cohorts. Article 10 (Data Governance) is the article EU deployers struggle with most, and the report your library generates is exactly the kind of artifact they hand to a DPO or to a notified body as Article 10 evidence. With YData now inside KPMG, that "Article 10 evidence pack" angle gets even more interesting because KPMG advisory engagements terminate in conformity assessments and audit defense.

**Summary**: 285 Python files scanned, 16/57 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 2/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The strongest result is Article 12 at 4/9: ydata-profiling has clean Python logging infrastructure, real tracing patterns, and an action-level audit trail. Article 15 (4/10) also benefits from solid output validation and the determinism checks (RNG seeding, deterministic algorithm flags, hardware abstraction). The most counterintuitive finding is Article 10 at 1/5: a library whose entire purpose is data quality and profiling currently shows no PII detection / redaction patterns inside the code path itself, no data governance markdown, and no built-in vault integration. That's a high-leverage gap because Article 10 is exactly the article ydata-profiling is best positioned to own upstream for every EU enterprise user. The other notable signal is Article 14 (0/9): the scanner doesn't find approval gates, kill switches, agent identity binding, or token expiry, which becomes a problem only if profiling reports start being consumed by autonomous downstream agents (which is increasingly common in KPMG-style advisory tooling).

**To be clear**: this doesn't mean ydata-profiling is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Two upstream changes would shift the score and turn every ydata-profiling report into a cleaner Article 10 evidence artifact: (1) a `DATA_GOVERNANCE.md` shipped alongside the README explaining intended use, sensitive-column handling, and retention assumptions, and (2) optional PII-aware scanning (presidio or scrubadub plug-in) so the report itself flags `email`, `national_id`, `iban`, etc. and surfaces it in the HTML. Both are small but they let downstream Article 10 evidence collection inherit from your library by default. Happy to share the full per-check report, or - given the KPMG combination - talk through what an "Article 9 to 15 ready" YData distribution might look like inside KPMG's regulated-industry advisory motions.

Best,
Jason Shotwell
https://airblackbox.ai
