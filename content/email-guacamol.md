# Email to GuacaMol (BenevolentAI)

**To**: nathan.brown@benevolent.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for GuacaMol (35 files scanned)

> **NOTE FOR JASON**: Contact confidence is **medium**. BenevolentAI went through CEO turnover in April 2026 (Möller out, Mulvany back as executive chairman). Nathan Brown is the original GuacaMol author and Head of Cheminformatics at BenevolentAI; the email pattern `firstname.lastname@benevolent.com` is inferred. If this bounces, fall back to `press@benevolent.com` or reach out via Nathan's LinkedIn first.

---

Hey Nathan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran GuacaMol through the scanner and wanted to share what I found. GuacaMol became the reference benchmark for de novo molecular generation and still gets cited by every team standing up a generative chemistry pipeline. As EU pharma and biotech teams start to build AI Act conformity evidence around their drug-discovery stacks, the benchmarks and baselines they used during model development fall directly into Article 9 (risk management) and Article 15 (accuracy and robustness) scope. A scan on the upstream package seemed useful to share.

**Summary**: 35 Python files scanned, 10/57 checks passing (18%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 0/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/10 passing |

The strong side is Art. 12 at 3/9 (there's enough logging infrastructure that the scanner picked it up) and Art. 11 at 2/5 (README plus partial type-hint coverage). Art. 15 at 3/10 registers deterministic algorithm flags because GuacaMol is largely cheminformatics math rather than a framework runtime.

The biggest gap is Art. 9 at 0/5. The scanner didn't find a risk-assessment document, a risk-classification mapping, or structured error handling around the scoring functions. Given GuacaMol's role as a benchmark that downstream pharma compliance teams will cite during conformity assessments, a short RISK_ASSESSMENT.md explaining the benchmark's intended use, out-of-scope uses, and known limitations would move this from 0/5 to closer to 4/5. Article 9 is explicit that high-risk systems need documented risk-management processes, and a one-pager at the benchmark level makes that possible for everyone using GuacaMol downstream.

Art. 10 at 0/5 is the other one. The ChEMBL-derived datasets are already well-documented in the paper; surfacing a DATA_GOVERNANCE.md in the repo that describes the data lineage, the filtering rules, and the intended scope would convert that.

**To be clear**: this doesn't mean GuacaMol is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

With EMA and national regulators starting to ask about AI governance in drug-discovery submissions, a GuacaMol that can point to its own Article 9 and Article 10 posture gives every team using the benchmark a cleaner line into their own conformity work. Happy to share the full scan output or open a small PR with a RISK_ASSESSMENT.md and DATA_GOVERNANCE.md if that's useful.

Best,
Jason Shotwell
https://airblackbox.ai
