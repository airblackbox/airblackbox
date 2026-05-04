# Email to MOSTLY AI

**To**: tobias.hann@mostly.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for MOSTLY AI Synthetic Data SDK (124 files scanned)

---

Hey Tobias,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the mostly-ai/mostlyai SDK through the scanner and wanted to share what I found. MOSTLY AI's pitch is fundamentally an Article 10 pitch: give your AI teams data they can train on without violating GDPR or the EU AI Act's data governance obligations. That positioning makes the SDK itself one of the most interesting things to scan in the European synthetic-data ecosystem, because the Article 10 posture of the tool that produces compliant training data is exactly what enterprise auditors will look at first.

**Summary**: 124 Python files scanned, 13/57 checks passing (23%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/10 passing |

The good news first: Article 12 at 3/9 reflects real structured-logging surface across the engine layer, and Article 15 at 3/10 picks up output validation around the Generator and Synthetic Dataset resources. Both are meaningful for a tool that customers will embed in regulated data pipelines.

The biggest lever is Article 10, which is also the article MOSTLY AI's value proposition is built around. The scanner currently shows 1/5 there: no consent management patterns, no data minimization patterns visible to static analysis, no right-to-erasure implementation, no records-of-processing-activities pattern, and no explicit cross-border transfer safeguards in the connector layer. Each of those has a one-paragraph answer in the existing product (the synthetic-data approach is itself the data minimization story; the connector model is the records-of-processing surface), so the gap is more about making the answer machine-readable than about doing engineering work. A DATA_GOVERNANCE.md that maps the SDK's Generator, Connector, and Synthetic Dataset primitives to specific Article 10 obligations, plus a `lineage_metadata` field on Connectors that records the legal basis under which source data was accessed, would push that 1/5 to 4/5 and give every enterprise customer a copy-pastable answer for their own Article 11 technical documentation.

**To be clear**: this doesn't mean MOSTLY AI is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

If the SDK ships with a documented Article 10 posture out of the box, MOSTLY AI becomes the only synthetic-data tool an enterprise data-governance team can drop into a regulated pipeline without rebuilding the compliance argument from scratch. Happy to share the full scan output if useful.

Best,
Jason Shotwell
https://airblackbox.ai
