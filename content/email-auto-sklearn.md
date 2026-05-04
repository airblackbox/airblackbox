# Email to auto-sklearn

**To**: feurerm@informatik.uni-freiburg.de
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for auto-sklearn (381 files scanned)

---

Hey Matthias,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran auto-sklearn through the scanner and wanted to share what I found. auto-sklearn is one of the most-cited AutoML libraries in Europe, and it shows up underneath a surprising amount of regulated tabular ML inside German banks, insurers, healthcare, and energy. The EU AI Act is going to bite hardest in exactly those places: anything that touches credit scoring, fraud, claims, triage, or critical infrastructure forecasting hits Annex III. When that downstream model was selected and fit by auto-sklearn, the deployer's Article 9 to Article 15 evidence collection inherits whatever auto-sklearn does or doesn't expose at the API surface. Coming from the Hutter group at Freiburg, you sit at the upstream end of a lot of those pipelines.

**Summary**: 381 Python files scanned, 13/57 checks passing (22%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The strongest result is Article 15 at 4/10, which is largely the determinism story: auto-sklearn passes on RNG seed determinism, deterministic algorithm flags, hardware abstraction, and output validation, all of which matter when an EU bank or insurer has to defend reproducibility. Article 12 (3/9) is also working in your favor with logging infrastructure in place. The lowest-scoring article is Article 11 at 1/5, and that's the one that costs downstream EU teams the most: docstring coverage on public functions sits below the threshold and there's no model card / system card alongside the README. Article 11 is the article that every EU deployer hits first when assembling Technical Documentation evidence, and right now they have to handcraft it for each auto-sklearn-selected pipeline. Article 14 (1/9) is the second leverage point: there are no built-in budget controls, approval gates, or execution bounding on the search loop, which becomes a real concern when AutoML is run inside an automated MLOps pipeline that an EU operator is supposed to be able to halt.

**To be clear**: this doesn't mean auto-sklearn is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Two upstream changes would shift the score noticeably and unblock a lot of regulated EU AutoML deployers: (1) a `MODEL_CARD.md` template that auto-sklearn can populate from the selected pipeline (intended use, limitations, performance metrics, known failure modes), and (2) optional `time_budget` / `max_iter` enforcement plus a structured `audit_log.jsonl` written next to the fitted estimator. Both are small but they let downstream Article 11 (Technical Documentation) and Article 12 (Record-Keeping) evidence inherit from auto-sklearn rather than being recreated by every regulated team. Happy to share the full per-check report, or talk through what an "Article 9 to 15 ready" AutoML distribution might look like for the German enterprise users sitting on top of your work.

Best,
Jason Shotwell
https://airblackbox.ai
