# Email to Mindee (doctr)

**To**: jonathan@mindee.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for doctr (212 files scanned)

---

Hey Jonathan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran doctr through the scanner and wanted to share what I found. docTR sits at the front of a lot of EU document workflows (finance, insurance, public sector onboarding), and under the August 2, 2026 EU AI Act enforcement deadline those downstream customers are going to be mapping their conformity assessments back to every model and library in the OCR pipeline. Because doctr is the Python library people actually import (not just the Mindee API), it's in the scope of their Article 11 technical documentation whether you want it to be or not.

**Summary**: 212 Python files scanned, 12/58 checks passing (21%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/11 passing |

The strong side: Art. 11 came in at 3/5, which is the highest the scanner typically sees for a vision library. Docstring coverage, type hints, and the published README passed cleanly. Art. 12 also looked better than average on structured logging. The framework abstraction (PyTorch and TensorFlow backends) is documented enough that the static checks for hardware abstraction and determinism flags picked up cleanly.

The two gaps that will matter most to your users are Art. 10 (1/5) and Art. 15 (1/11). On Art. 10, the scanner didn't find PII detection or redaction patterns, and didn't find a DATA_GOVERNANCE.md. For a library that reads IDs, invoices, and contracts, a short doc that explicitly says "docTR extracts text, it does not detect or classify PII, downstream users must handle that" would answer the number one question every DPO is about to ask. On Art. 15, the gaps are mostly around adversarial robustness evidence and structured output validation on the recognition predictor outputs, which is the kind of thing a short MODEL_CARD.md per pretrained checkpoint could cover.

**To be clear**: this doesn't mean doctr is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Mindee is one of the Paris AI companies whose library is already embedded in regulated EU pipelines, so whatever doctr documents effectively sets the OCR baseline for Article 11. A small docs pass on data governance plus per-checkpoint model cards would let every downstream enterprise cite doctr directly in their own conformity assessments. Happy to share the full scan output or open a PR if that would help.

Best,
Jason Shotwell
https://airblackbox.ai
