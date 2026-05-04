# Email to Zama (Concrete-ML)

**To**: rand.hindi@zama.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Zama Concrete-ML (196 files scanned)

---

Hey Rand,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the zama-ai/concrete-ml repo through the scanner and wanted to share what I found. Concrete-ML occupies an unusual position in the EU AI Act conversation: FHE is one of the few primitives that genuinely changes the risk surface of an Annex III high-risk system, because the controller never sees the plaintext data the model is operating on. That makes the SDK's own technical posture (how it's configured, logged, and fall-back-handled by the deploying enterprise) the thing that ends up inside customer Article 11 technical documentation.

**Summary**: 196 Python files scanned, 16/58 checks passing (28%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

The good news first: Article 11 at 3/5 and Article 15 at 3/11 are both above what I see on most ML-framework repos in this pipeline. Concrete-ML's documentation surface and the patterns around error handling, output validation, and protocol boundaries are all visible to static analysis, which is unusual for a research-adjacent codebase of this size and exactly what enterprise reviewers want to see when they're evaluating a cryptography library.

The biggest lever is Article 14, currently 1/9. For a library used to deploy ML models against encrypted user data in production, human-oversight patterns (approval workflows around model deployment, client-side rate limiting, explicit fall-back paths when a circuit fails to evaluate, audit trails on parameter selection) are the exact controls a high-risk-systems audit will ask about. A `concrete_ml.compliance` submodule that exposes a deployment-checklist API (model card emission, parameter-set provenance, signed-circuit verification, optional human-in-the-loop gates around inference output) would move that 1/9 closer to 5/9 and give every Zama enterprise prospect a built-in answer for the Article 14 portion of their conformity assessment.

**To be clear**: this doesn't mean Concrete-ML is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

FHE is one of the very few stories where "this control is enforced cryptographically, not procedurally" shortens a conformity assessment substantially. If Concrete-ML ships with a documented Articles 9, 10, and 14 posture mapped to specific SDK primitives, Zama becomes the obvious choice for any EU enterprise that wants to deploy a high-risk model without building the compliance argument from scratch. Happy to share the full scan output if useful.

Best,
Jason Shotwell
https://airblackbox.ai
