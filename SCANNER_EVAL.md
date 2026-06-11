# Scanner Evaluation

Precision and recall of the AIR Blackbox code scanner, measured against a labeled corpus of code samples with known ground truth. This turns the check count from a claim into a measured instrument.

## Method

Each fixture is a small code sample labeled for one check: positive means the practice genuinely is present, negative means it is absent. Negative fixtures are realistic code that lacks the specific practice (often with real LLM calls present), so this measures discrimination, not empty-vs-nonempty. A positive prediction is the scanner returning status `pass` for that check.

Corpus: **72 fixtures** (36 positive, 36 negative) across **12 checks**.

Reproduce: `PYTHONPATH=sdk python3 eval/scanner/run_eval.py`

## Results

**Overall on this corpus: precision 1.00, recall 1.00, F1 1.00, accuracy 100%** (72/72). This measures discrimination on realistic labeled samples; it is not a claim of accuracy on arbitrary production code.

| Check | Article | TP | FP | FN | TN | Precision | Recall | F1 |
|-------|--------:|---:|---:|---:|---:|----------:|-------:|---:|
| Application logging | 12 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Fallback/recovery patterns | 9 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Human-in-the-loop patterns | 14 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Input validation / schema enforcement | 10 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| LLM call error handling | 9 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| LLM output validation | 15 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| PII handling in code | 10 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Prompt injection defense | 15 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Retry / backoff logic | 15 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Tracing / observability | 12 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Type annotations | 11 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| Usage limits / budget controls | 14 | 3 | 0 | 0 | 3 | 1.00 | 1.00 | 1.00 |
| **Overall** | | 36 | 0 | 0 | 36 | **1.00** | **1.00** | **1.00** |

## What this eval caught

On first run the scanner missed NVIDIA NeMo Guardrails: the detector pattern was `nemo_guardrails` (underscore) but the library is imported as `nemoguardrails`. That false negative was invisible until the corpus measured it, and the fix (`nemo_?guardrails`) is the kind of gap an eval exists to surface. The headline value of this harness is not the score, it is that regressions and missed libraries now show up as numbers.


## Honest limitations

- The corpus is a starting instrument, not exhaustive. It covers the code-pattern checks, not the static file-existence checks (which are deterministic) or the runtime checks (which need a live gateway).
- These are heuristic detectors. High recall with imperfect precision means the scanner errs toward surfacing a control for human review rather than silently passing. The scanner is a starting point to identify potential gaps, not a certified compliance test.

