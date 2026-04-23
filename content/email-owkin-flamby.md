# Email to Owkin (FLamby)

**To**: thomas@owkin.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for FLamby (148 files scanned)

---

Hey Thomas,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran FLamby through the scanner and wanted to share what I found. FLamby is the benchmark a lot of healthcare AI teams are citing when they talk about cross-silo federated learning, which means any EU pharma, hospital, or medical device group fine-tuning on it inherits FLamby's patterns when the August 2, 2026 EU AI Act deadline hits. That makes the repo a high-leverage place to set norms.

**Summary**: 148 Python files scanned, 6/57 checks passing (11%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 0/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 1/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/10 passing |

The context matters: FLamby is a research benchmark, not a production system, so a low static score is expected. The NeurIPS 2022 paper and fed_isic2019 / fed_ixi / fed_kits19 READMEs do a great job of explaining the datasets. Most of what the scanner flagged is the infrastructure around those datasets.

The two gaps that matter most for healthcare AI teams adopting FLamby: Art. 10 data governance (no PII detection, redaction, or masking patterns in code, and no data governance doc) and Art. 9 risk management (no risk classification, no risk assessment doc, and only 1/11 files with LLM calls have error handling). Because EU hospitals running federated trials will be in the "high-risk" bucket under Annex III, a short DATA_GOVERNANCE.md and a minimal risk-classification section in the README would shield every downstream user from having to write those docs themselves.

**To be clear**: this doesn't mean FLamby is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Happy to open a PR with a DATA_GOVERNANCE.md template and a risk-classification section if that's useful. Owkin is one of the few French AI companies in a position to set the template for federated health AI compliance, and FLamby is the natural place to do it.

Best,
Jason Shotwell
https://airblackbox.ai
