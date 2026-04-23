# Email to Taipy (Avaiga)

**To**: vincent@taipy.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Taipy (1103 files scanned)

---

Hey Vincent,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Taipy through the scanner and wanted to share what I found. Taipy is one of the few Python-first app builders that EU data-science teams can ship end-to-end on their own infrastructure, which puts it inside a lot of regulated workflows (energy, finance, manufacturing). Under the August 2, 2026 EU AI Act enforcement deadline, the teams building Taipy apps are going to need to map their application code back to Articles 9 through 15, and the framework patterns will set the defaults. The good news: Taipy already picks up a lot of what the scanner looks for.

**Summary**: 1,103 Python files scanned, 21/58 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 3/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 5/11 passing |

The strong side: Art. 12 (5/9) and Art. 14 (3/9) are both above where the scanner usually lands for open-source Python frameworks. Structured logging, scenario tracking, and the job/submission model give you a real audit trail surface. Art. 14 picking up 3 passes is notable, because most frameworks we scan come in at 0 there, and Taipy's scenario-and-job approval patterns are doing real work. Art. 15 at 5/11 also looks good, with retry/backoff and the schema layer passing cleanly.

The biggest gap is Art. 10 (1/5). The scanner didn't find PII detection, masking, or a DATA_GOVERNANCE.md, which matters because Taipy data nodes touch customer data directly. A short governance doc that describes how data nodes persist, expire, and isolate per-user data would answer a lot of questions regulated enterprises are about to ask. Similar story on Art. 11: a lightweight model card template for Taipy scenarios that use ML models would let your users inherit documentation instead of writing it from scratch.

**To be clear**: this doesn't mean Taipy is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Taipy sits in an unusual spot: it's the framework French and EU industrial teams are already picking over Streamlit and Dash specifically because it's local-first and Python-native, and that's exactly the profile Article 11 wants. A small pass on data governance and a scenario-level model card would let your users cite Taipy directly in their conformity assessments. Happy to share the full scan output or open a PR against the docs if useful.

Best,
Jason Shotwell
https://airblackbox.ai
