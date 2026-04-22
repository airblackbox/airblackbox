# GitHub Replies — Scanner v1.3.1 Fix

## Reply to airblackbox/scanner#2 (Julian's type hints bug)

---

Fixed in v1.3.1. All three bugs addressed:

**1. Multi-line signatures** — The checker now joins continuation lines (unmatched parentheses + backslash continuations) into a single string before checking for type annotations. Functions like:

```python
def run(
    self,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Document]:
```

are now correctly detected as fully typed.

**2. Return type on continuation lines** — `-> ReturnType` on a line after a backslash is now detected because the full signature is joined first.

**3. Expanded type recognition** — The old regex only recognized 11 types (`str|int|float|bool|list|dict|List|Dict|Optional|Any|Tuple`). The new pattern recognizes 50+ types from the `typing` module (`Sequence`, `Iterable`, `Callable`, `Union`, `Mapping`, `Protocol`, `TypedDict`, etc.), common stdlib types (`Path`, `UUID`, `datetime`, `Decimal`), and any CamelCase class name (catches custom types like `PipelineConfig`, `Document`, etc.).

**Impact on Haystack scan:**

| Metric | v1.3.0 (old) | v1.3.1 (fixed) |
|--------|-------------|----------------|
| Type annotations | ~29% ❌ | **88%** ✅ |
| Docstrings | ~29% ❌ | **79%** ✅ |
| Overall | 24 pass, 10 warn, 5 fail | **12 pass, 2 warn, 0 fail** |

Thanks for the detailed report — this was a significant accuracy improvement.

---

## Reply to deepset-ai/haystack#10810 (Updated scan results)

---

Hey @julian-risch — thanks again for the bug reports on the scanner. I've fixed all three issues you reported in [airblackbox/scanner#2](https://github.com/airblackbox/scanner/issues/2) and re-scanned Haystack with v1.3.1.

The updated results are much more accurate:

### AIR Blackbox v1.3.1 — Haystack Scan Results

| Article | Check | Status |
|---------|-------|--------|
| Art. 9 — Risk Management | LLM call error handling | ⚠️ WARN (52/127 files) |
| Art. 9 — Risk Management | Fallback/recovery patterns | ✅ PASS (30 files) |
| Art. 10 — Data Governance | Input validation / schema enforcement | ✅ PASS (126/280 files) |
| Art. 10 — Data Governance | PII handling | ✅ PASS (18 files) |
| Art. 11 — Technical Docs | Code documentation (docstrings) | ✅ PASS (79%) |
| Art. 11 — Technical Docs | Type annotations | ✅ PASS (88%) |
| Art. 12 — Record-Keeping | Application logging | ✅ PASS (100/280 files, 36%) |
| Art. 12 — Record-Keeping | Tracing / observability | ✅ PASS (11 files) |
| Art. 14 — Human Oversight | Human-in-the-loop patterns | ✅ PASS (18 files) |
| Art. 14 — Human Oversight | Usage limits / budget controls | ✅ PASS (17 files) |
| Art. 15 — Robustness | Retry / backoff logic | ✅ PASS (19 files) |
| Art. 15 — Robustness | Prompt injection defense | ✅ PASS (7 files) |
| Art. 15 — Robustness | Unsafe input handling | ⚠️ WARN (9 files) |
| Art. 15 — Robustness | LLM output validation | ✅ PASS (15 files) |

**Summary: 12 passing ✅ | 2 warnings ⚠️ | 0 failing ❌**

Key changes from the previous scan:
- **Type annotations** jumped from ~29% to **88%** — the old scanner wasn't handling multi-line signatures or recognizing types beyond a basic whitelist (your bug report in scanner#2)
- **Docstrings** jumped from ~29% to **79%** — same multi-line detection fix
- **Overall**: 0 failures, down from 5

Haystack remains the strongest framework we've tested for EU AI Act technical compliance patterns. The `human_in_the_loop` module, structured tracing via `HAYSTACK_CONTENT_TRACING_ENABLED`, and comprehensive Pydantic validation are standout features.

The remaining two warnings:
1. **LLM call error handling** — 52/127 files with LLM calls have error handling. Some converter and writer modules could benefit from try/except around external calls.
2. **Unsafe input handling** — 9 files where user input may flow into prompts without sanitization (e.g., `llm_evaluator.py`).

Happy to discuss further or run additional scans as the codebase evolves.
