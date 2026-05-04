# Email to sktime (Alan Turing Institute)

**To**: fkiraly@turing.ac.uk
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for sktime (1,577 files scanned)

---

Hey Franz,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran sktime/sktime through the scanner and wanted to share what I found. Time-series ML lives in some of the most heavily regulated corners of the EU AI Act footprint: forecasting headcount, energy demand, hospital admissions, fraud risk, and anything that informs employment, critical-infrastructure, or essential-service decisions in the EU lands inside Annex III high-risk territory. sktime is the library a lot of those teams reach for first, which makes its own posture an outsized input into the audit story their compliance functions have to produce for the August 2026 deadline.

**Summary**: 1,577 Python files scanned, 16/58 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

The good news first: sktime's documentation surface is one of the strongest the scanner has seen on a research-derived codebase. Public estimator APIs, type-hinted protocol classes, and the way `BaseForecaster` exposes contract metadata are all things a compliance reviewer can read directly - that's a real Article 11 lead over almost every other ML framework in this pipeline. Article 15 at 3/11 also reflects the scikit-learn-lineage discipline around input validation and output shape contracts.

The biggest lever is Article 9, currently 1/5. For a forecasting toolbox whose users will spend the next year being asked "show us how this model handles regime changes, missing data, and silent drift in production," there's no first-class place in the API to declare risk-tier metadata or attach a fallback-forecaster pattern. A small `sktime.compliance` namespace that (a) lets a forecaster carry an `eu_ai_act_risk` tag and an `on_failure` policy that flows through into pickled artifacts, and (b) ships a documented "fallback forecaster" mixin (return-last-value, return-seasonal-naive, abstain) would push Article 9 from 1/5 toward 4/5 and give every sktime user a built-in Article 9 evidence template. The same idea on Article 14 (a `predict_with_review` flow with an explicit prediction-interval threshold for human escalation) covers most of the human-oversight gap.

**To be clear**: this doesn't mean sktime is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Time-series is one of the few corners of ML where "this is my fallback path, this is my regime-change detector, this is my abstain policy" maps almost one-for-one onto the EU AI Act's Article 9 language. If sktime ships an opinionated reference pattern for that before August 2026, it becomes the obvious forecasting library for any EU enterprise that wants to short-circuit the conformity assessment for forecasting workloads. Happy to share the full scan output, or compare notes on what a `sktime.compliance` module could look like, if any of this is useful.

Best,
Jason Shotwell
https://airblackbox.ai
