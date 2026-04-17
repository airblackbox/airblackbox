# Mistral AI - Full Organization Scan Report

**Date**: April 3, 2026
**Scanner**: AIR Blackbox v1.8.0
**Organization**: github.com/mistralai
**HQ**: Paris, France (EU Tier 1 - directly subject to EU AI Act)

## Executive Summary

Scanned **6 repos**, **1,545 Python files** total across Mistral AI's open-source ecosystem.

| Repo | Stars | Python Files | Passing | Warnings | Failing | Score |
|------|-------|-------------|---------|----------|---------|-------|
| mistral-inference | 14K+ | 14 | 4/44 | 26 | 14 | **9%** |
| client-python | 719 | 948 | 13/44 | 19 | 12 | **30%** |
| mistral-common | 875 | 90 | 4/45 | 27 | 14 | **9%** |
| mistral-finetune | 3.1K | 38 | 6/44 | 25 | 13 | **14%** |
| mistral-vibe | 3.8K | 443 | 13/45 | 19 | 13 | **29%** |
| mistral-evals | 85 | 12 | 6/44 | 25 | 13 | **14%** |
| **COMBINED** | **~22.6K** | **1,545** | - | - | - | **~18% avg** |

## Per-Repo Breakdown

### 1. mistral-inference (14 files, 9%)

The official inference library for Mistral models. Smallest repo but highest visibility.

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 0/4 |
| Art. 10 (Data Governance) | Input validation, PII | 1/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 2/5 |
| Art. 12 (Record-Keeping) | Logging, audit trails | 1/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 0/9 |
| Art. 15 (Security) | Injection defense, validation | 0/7 |

**Highlights**: 100% type annotation coverage (69/69 functions). Input validation via Pydantic in 5/14 files.
**Gaps**: Zero passing in Articles 9, 14, and 15. No error handling on LLM calls in generate.py.

---

### 2. client-python (948 files, 30%)

The Python SDK for the Mistral API. Largest codebase by file count (auto-generated).

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 1/4 |
| Art. 10 (Data Governance) | Input validation, PII | 2/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 2/5 |
| Art. 12 (Record-Keeping) | Logging, audit trails | 2/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 2/9 |
| Art. 15 (Security) | Injection defense, validation | 3/7 |

**Highlights**: Fallback patterns in 88 files. Tracing in 60 files (9 production-grade). Injection defense in 13 files. Output validation in 36 files. Retry/backoff in 74 files. Input validation in 751/948 files (Pydantic-heavy).
**Gaps**: Only 4% docstring coverage (106/2,531 functions). 46% type hints. Only 8 of 43 LLM-calling files have error handling.

---

### 3. mistral-common (90 files, 9%)

Pre-processing library for Mistral models (tokenization, input formatting).

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 1/4 |
| Art. 10 (Data Governance) | Input validation, PII | 2/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 2/5 |
| Art. 12 (Record-Keeping) | Logging, audit trails | 0/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 0/9 |
| Art. 15 (Security) | Injection defense, validation | 0/7 |

**Highlights**: 100% type annotation coverage (283/283 functions). Pydantic validation in 36/90 files.
**Gaps**: Zero passing in Articles 12, 14, and 15. Only 3% docstring coverage (11/390 functions). No retry logic, no injection defense.

---

### 4. mistral-finetune (38 files, 14%)

LoRA-based fine-tuning toolkit for Mistral models.

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 2/4 |
| Art. 10 (Data Governance) | Input validation, PII | 2/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 3/5 |
| Art. 12 (Record-Keeping) | 2/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 0/9 |
| Art. 15 (Security) | Injection defense, validation | 1/7 |

**Highlights**: No direct LLM API calls (training library). 79% type hints. 32% logging coverage. Tracing in 3 files. Retry/backoff in 2 files.
**Gaps**: Only 8% docstrings. Zero passing in Article 14 (Human Oversight).

---

### 5. mistral-vibe (443 files, 29%)

Minimal CLI coding agent by Mistral. Their newest and most "agentic" repo.

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 1/4 |
| Art. 10 (Data Governance) | Input validation, PII | 2/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 2/5 |
| Art. 12 (Record-Keeping) | Logging, audit trails | 2/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 2/9 |
| Art. 15 (Security) | Injection defense, validation | 3/7 |

**Highlights**: 100% type annotations (916/916 functions). Agent action boundaries in 22 files. Agent identity binding detected. Tracing in 30 files. Audit logging in 16 files. Injection defense in 1 file. Retry logic in 14 files. Data retention/TTL patterns in 12 files.
**Gaps**: Only 7% docstrings. PII-aware variable names in 10 files but no detection/redaction. No token expiry.

---

### 6. mistral-evals (12 files, 14%)

Model evaluation framework. Smallest but important for compliance.

| Article | What It Checks | Passing |
|---------|---------------|---------|
| Art. 9 (Risk Management) | Error handling, fallbacks | 2/4 |
| Art. 10 (Data Governance) | Input validation, PII | 2/5 |
| Art. 11 (Documentation) | Docstrings, type hints | 2/5 |
| Art. 12 (Record-Keeping) | Logging, audit trails | 0/6 |
| Art. 14 (Human Oversight) | Approval, rate limiting | 0/9 |
| Art. 15 (Security) | Injection defense, validation | 1/7 |

**Highlights**: 75% type hints. 31% docstrings (best ratio in Mistral org). Fallback patterns in 3 files. All LLM calls have error handling.
**Gaps**: Zero passing in Articles 12 and 14. No logging framework detected.

---

## Cross-Repo Analysis

### Strongest Patterns Across Mistral

1. **Type annotations**: Consistently excellent. Three repos hit 100% (inference, common, vibe). Average across org is ~80%+.
2. **Input validation**: Pydantic usage is strong, especially in client-python (751/948 files).
3. **Fallback patterns**: Present in inference, client-python, vibe, finetune, and evals.
4. **Retry/backoff**: Client-python has 74 files with retry logic.

### Biggest Gaps Across Mistral

1. **Article 14 (Human Oversight)**: Weakest article across ALL repos. No human-in-the-loop patterns, no budget enforcement, no kill switches. Only vibe has agent identity binding and action boundaries.
2. **Docstrings**: Consistently low. Best is evals at 31%, worst is mistral-common at 3%.
3. **Article 12 (Record-Keeping)**: No tamper-evident audit chains anywhere. Vibe has the best logging (action-level audit in 16 files) but no structured audit chain.
4. **PII handling**: PII-aware variable names found in vibe (10 files) but no detection/redaction library in any repo.
5. **GDPR**: Zero GDPR patterns across inference, common, finetune, and evals. Minimal in client-python and vibe.

### Framework Detection

| Repo | Frameworks Detected |
|------|-------------------|
| mistral-inference | (none - custom inference) |
| client-python | (none - is the SDK) |
| mistral-common | OpenAI (compatibility layer) |
| mistral-finetune | (none - training library) |
| mistral-vibe | (none - custom agent) |
| mistral-evals | OpenAI |

### Where Trust Layers Would Help Most

- **mistral-vibe**: As a coding agent, this is the highest-risk repo for EU AI Act compliance. Adding `air_blackbox.attach("openai")` would add runtime audit chains to agent actions.
- **client-python**: As the SDK used by every Mistral API consumer, adding compliance hooks here would propagate to all downstream users.

## Recommendations for the Outreach Email

The original email targeted only mistral-inference (14 files, 9%). The full org scan tells a richer story:

1. **Lead with the full picture**: 1,545 Python files across 6 repos, ~18% average compliance
2. **Highlight the type annotation excellence**: 3 repos at 100% shows Mistral cares about code quality
3. **Focus on mistral-vibe**: Their coding agent is the highest-risk product and has the most compliance-relevant patterns already (action boundaries, identity binding, audit logging)
4. **Article 14 is the universal gap**: Zero or near-zero across all repos. This is the article EU regulators will focus on for agentic systems
5. **Docstrings are the quick win**: Raising docstring coverage from 3-8% to 50%+ would significantly improve Article 11 scores

## Updated Email Recommendation

Consider revising the email to Arthur Mensch to reference the full org scan rather than just mistral-inference. The broader picture is more compelling and shows deeper due diligence.
