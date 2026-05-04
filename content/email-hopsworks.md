# Email to Hopsworks

**To**: jim@hopsworks.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Hopsworks (440 files scanned)

---

Hey Jim,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the hopsworks-api repo through the scanner and wanted to share what I found. Stockholm-based, feature store sitting upstream of every model your enterprise users ship, which means Article 10 (Data Governance) is effectively the article Hopsworks gets graded on by every customer's compliance team. With August 2, 2026 enforcement now three months out, the feature store layer is one of the first stops auditors will make when tracing data lineage for a high-risk system.

**Summary**: 440 Python files scanned, 21/58 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 3/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 6/11 passing |

The good news first: Article 15 at 6/11 is one of the stronger robustness profiles I've scanned in this pipeline. Retry and backoff patterns are well-distributed across 12 files, output parsing/validation shows up across the engine layer, and there's a clean injection-defense pattern in the inference path. Token expiry and execution bounding also pass cleanly, which is rare for SDKs of this size.

The biggest lever is Article 10. For a platform whose core promise is "feature store and lakehouse for AI," the scanner currently flags no data minimization patterns, no consent-management hooks, no right-to-erasure implementation, and EU region config in two files without explicit transfer safeguards. That's a meaningful gap because Hopsworks customers will increasingly be asked to demonstrate that their feature engineering layer enforces those properties by default rather than leaving it to the application team. A DATA_GOVERNANCE.md mapping each Hopsworks API to its Article 10 obligations, plus a dataset-schema-level PII tag the platform respects on writes and reads, would move that dial from 1/5 to 4/5 without changing the architecture.

**To be clear**: this doesn't mean Hopsworks is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Hopsworks sits at the data layer for teams that will need to produce technical documentation (Article 11) and conformity-assessment evidence (Article 17) for their own deployed systems, a publicly visible Article 10 posture on the feature store itself becomes a real selling point for EU enterprise prospects. Happy to share the full scan output, or walk through which checks are easy wins on the Hopsworks side versus things that belong in customer-facing docs.

Best,
Jason Shotwell
https://airblackbox.ai
