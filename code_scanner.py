"""
Code-level scanner — reads Python files and detects compliance-relevant patterns.

This module makes every project get a DIFFERENT score by actually reading
the Python source code and checking for real patterns.

The existing engine.py checks files-exist and gateway-running.
This module checks what's actually IN the code.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class CodeFinding:
    """A single thing we found (or didn't find) in the code."""
    article: int
    name: str
    status: str  # "pass", "warn", "fail"
    evidence: str
    detection: str = "auto"
    fix_hint: str = ""
    files: list = field(default_factory=list)


def scan_codebase(scan_path: str) -> List[CodeFinding]:
    """Walk all Python files and check for compliance patterns."""
    py_files = _find_python_files(scan_path)
    if not py_files:
        return [CodeFinding(
            article=0, name="Python files",
            status="warn", evidence=f"No Python files found in {scan_path}",
            fix_hint="Point --scan at a directory containing Python code"
        )]

    # Read all files once
    file_contents = {}
    for fp in py_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                file_contents[fp] = f.read()
        except Exception:
            continue

    findings = []

    # === Article 9: Risk Management ===
    findings.extend(_check_error_handling(file_contents, scan_path))
    findings.extend(_check_fallback_patterns(file_contents, scan_path))

    # === Article 10: Data Governance ===
    findings.extend(_check_input_validation(file_contents, scan_path))
    findings.extend(_check_pii_handling(file_contents, scan_path))

    # === Article 11: Technical Documentation ===
    findings.extend(_check_docstrings(file_contents, scan_path))
    findings.extend(_check_type_hints(file_contents, scan_path))

    # === Article 12: Record-Keeping ===
    findings.extend(_check_logging(file_contents, scan_path))
    findings.extend(_check_tracing(file_contents, scan_path))

    # === Article 14: Human Oversight ===
    findings.extend(_check_human_in_loop(file_contents, scan_path))
    findings.extend(_check_rate_limiting(file_contents, scan_path))

    # === Article 15: Robustness ===
    findings.extend(_check_retry_logic(file_contents, scan_path))
    findings.extend(_check_injection_defense(file_contents, scan_path))
    findings.extend(_check_output_validation(file_contents, scan_path))

    return findings


def _find_python_files(scan_path: str) -> List[str]:
    """Find all .py files, skipping common junk dirs."""
    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
        "dist", "build", "egg-info", ".eggs", "site-packages"
    }
    py_files = []
    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith(".egg-info")]
        for fname in files:
            if fname.endswith(".py"):
                py_files.append(os.path.join(root, fname))
    return py_files


def _rel(filepath: str, scan_path: str) -> str:
    """Make a filepath relative to scan_path for clean display."""
    return os.path.relpath(filepath, scan_path)


# ─────────────────────────────────────────────
# Article 9 — Risk Management
# ─────────────────────────────────────────────

def _check_error_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if AI/LLM calls are wrapped in try/except."""
    llm_call_patterns = [
        r'\.chat\.completions\.create\(', r'\.completions\.create\(',
        r'\.invoke\(', r'\.run\(', r'\.generate\(', r'\.predict\(',
        r'\.agenerate\(', r'\.ainvoke\(', r'ChatOpenAI\(', r'OpenAI\(',
        r'Anthropic\(',
    ]
    combined = "|".join(llm_call_patterns)
    files_with_llm_calls = []
    files_with_error_handling = []

    for fp, content in file_contents.items():
        if re.search(combined, content):
            files_with_llm_calls.append(fp)
            if re.search(r'\btry\b.*?\bexcept\b', content, re.DOTALL):
                files_with_error_handling.append(fp)

    if not files_with_llm_calls:
        return [CodeFinding(article=9, name="LLM call error handling",
            status="pass", evidence="No direct LLM API calls detected in code")]

    covered = len(files_with_error_handling)
    total = len(files_with_llm_calls)
    uncovered = [_rel(f, scan_path) for f in files_with_llm_calls if f not in files_with_error_handling]

    if covered == total:
        return [CodeFinding(article=9, name="LLM call error handling",
            status="pass", evidence=f"All {total} files with LLM calls have try/except blocks")]
    else:
        return [CodeFinding(article=9, name="LLM call error handling",
            status="fail" if covered == 0 else "warn",
            evidence=f"{covered}/{total} files with LLM calls have error handling. Missing: {', '.join(uncovered[:5])}",
            fix_hint="Wrap LLM API calls in try/except to handle failures gracefully")]


def _check_fallback_patterns(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for fallback/retry patterns when LLM calls fail."""
    fallback_patterns = [
        r'fallback', r'retry', r'backoff', r'with_fallbacks',
        r'with_retry', r'tenacity', r'max_retries', r'default_response',
    ]
    combined = "|".join(fallback_patterns)
    files_with_fallbacks = [fp for fp, content in file_contents.items()
                           if re.search(combined, content, re.IGNORECASE)]
    if files_with_fallbacks:
        return [CodeFinding(article=9, name="Fallback/recovery patterns",
            status="pass", evidence=f"Fallback patterns found in {len(files_with_fallbacks)} file(s)")]
    else:
        return [CodeFinding(article=9, name="Fallback/recovery patterns",
            status="warn", evidence="No fallback or retry patterns detected",
            fix_hint="Add fallback logic for LLM failures (retry, default response, alternative model)")]


# ─────────────────────────────────────────────
# Article 10 — Data Governance
# ─────────────────────────────────────────────

def _check_input_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if user inputs are validated before reaching LLM."""
    validation_patterns = [
        r'pydantic', r'BaseModel', r'validator', r'field_validator',
        r'validate_input', r'input_schema', r'json_schema',
        r'TypedDict', r'dataclass', r'InputGuard', r'sanitize',
    ]
    combined = "|".join(validation_patterns)
    files_with_validation = [fp for fp, content in file_contents.items()
                            if re.search(combined, content)]
    total_files = len(file_contents)
    if files_with_validation:
        return [CodeFinding(article=10, name="Input validation / schema enforcement",
            status="pass",
            evidence=f"Input validation found in {len(files_with_validation)}/{total_files} Python files (Pydantic, dataclass, or similar)")]
    else:
        return [CodeFinding(article=10, name="Input validation / schema enforcement",
            status="warn", evidence="No structured input validation detected (Pydantic, dataclass, TypedDict)",
            fix_hint="Use Pydantic models or dataclasses to validate inputs before LLM calls")]


def _check_pii_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for PII detection, redaction, or masking patterns."""
    pii_patterns = [
        r'pii', r'redact', r'mask', r'anonymize', r'tokenize_pii',
        r'presidio', r'scrub', r'private', r'sensitive',
        r'data_protection', r'gdpr', r'personal_data',
    ]
    combined = "|".join(pii_patterns)
    files_with_pii = [fp for fp, content in file_contents.items()
                      if re.search(combined, content, re.IGNORECASE)]
    if files_with_pii:
        return [CodeFinding(article=10, name="PII handling in code",
            status="pass", evidence=f"PII-aware patterns found in {len(files_with_pii)} file(s)")]
    else:
        return [CodeFinding(article=10, name="PII handling in code",
            status="warn", evidence="No PII detection, redaction, or masking patterns found in code",
            fix_hint="Consider adding PII detection before sending data to LLM providers")]


# ─────────────────────────────────────────────
# Article 11 — Technical Documentation
# ─────────────────────────────────────────────

def _check_docstrings(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check what percentage of functions/classes have docstrings."""
    total_defs = 0
    documented_defs = 0
    for fp, content in file_contents.items():
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                if stripped.startswith("def _"):
                    continue
                total_defs += 1
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line == "":
                        continue
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        documented_defs += 1
                    break
    if total_defs == 0:
        return [CodeFinding(article=11, name="Code documentation (docstrings)",
            status="pass", evidence="No public functions/classes found to document")]
    pct = (documented_defs / total_defs * 100) if total_defs > 0 else 0
    if pct >= 60: status = "pass"
    elif pct >= 30: status = "warn"
    else: status = "fail"
    return [CodeFinding(article=11, name="Code documentation (docstrings)",
        status=status,
        evidence=f"{documented_defs}/{total_defs} public functions/classes have docstrings ({pct:.0f}%)",
        fix_hint="Add docstrings to public functions and classes explaining purpose and parameters")]


def _check_type_hints(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if functions use type hints."""
    total_defs = 0
    typed_defs = 0
    for fp, content in file_contents.items():
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("def ") and not stripped.startswith("def _"):
                total_defs += 1
                if "->" in stripped or re.search(r':\s*(str|int|float|bool|list|dict|List|Dict|Optional|Any|Tuple)', stripped):
                    typed_defs += 1
    if total_defs == 0:
        return []
    pct = (typed_defs / total_defs * 100) if total_defs > 0 else 0
    if pct >= 50: status = "pass"
    elif pct >= 20: status = "warn"
    else: status = "fail"
    return [CodeFinding(article=11, name="Type annotations",
        status=status,
        evidence=f"{typed_defs}/{total_defs} public functions have type hints ({pct:.0f}%)",
        fix_hint="Add type hints to function signatures for better documentation and tooling")]


# ─────────────────────────────────────────────
# Article 12 — Record-Keeping
# ─────────────────────────────────────────────

def _check_logging(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if the project uses structured logging."""
    logging_patterns = [
        r'import logging', r'from logging', r'getLogger',
        r'structlog', r'loguru', r'logger\.', r'logging\.',
    ]
    combined = "|".join(logging_patterns)
    files_with_logging = [fp for fp, content in file_contents.items()
                          if re.search(combined, content)]
    total = len(file_contents)
    if not files_with_logging:
        return [CodeFinding(article=12, name="Application logging",
            status="fail", evidence="No logging framework detected (logging, structlog, loguru)",
            fix_hint="Add import logging and log key decisions, errors, and LLM interactions")]
    pct = len(files_with_logging) / total * 100 if total > 0 else 0
    return [CodeFinding(article=12, name="Application logging",
        status="pass" if pct >= 20 else "warn",
        evidence=f"Logging found in {len(files_with_logging)}/{total} files ({pct:.0f}%)")]


def _check_tracing(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for distributed tracing / observability patterns."""
    tracing_patterns = [
        r'opentelemetry', r'otel', r'trace_id', r'span_id',
        r'run_id', r'request_id', r'correlation_id',
        r'langsmith', r'langfuse', r'helicone', r'arize',
        r'wandb', r'mlflow', r'callbacks',
    ]
    combined = "|".join(tracing_patterns)
    files_with_tracing = [fp for fp, content in file_contents.items()
                          if re.search(combined, content, re.IGNORECASE)]
    if files_with_tracing:
        return [CodeFinding(article=12, name="Tracing / observability",
            status="pass", evidence=f"Tracing patterns found in {len(files_with_tracing)} file(s)")]
    else:
        return [CodeFinding(article=12, name="Tracing / observability",
            status="warn", evidence="No tracing or observability integration detected",
            fix_hint="Add OpenTelemetry, LangSmith, or similar to track AI decisions")]


# ─────────────────────────────────────────────
# Article 14 — Human Oversight
# ─────────────────────────────────────────────

def _check_human_in_loop(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for human-in-the-loop / approval gate patterns."""
    hitl_patterns = [
        r'human_in_the_loop', r'human_approval', r'require_approval',
        r'approval_gate', r'confirm', r'ask_human', r'human_input',
        r'HumanApprovalCallbackHandler', r'input\(',
        r'human_feedback', r'manual_review', r'approval_required',
    ]
    combined = "|".join(hitl_patterns)
    files_with_hitl = [fp for fp, content in file_contents.items()
                       if re.search(combined, content, re.IGNORECASE)]
    if files_with_hitl:
        return [CodeFinding(article=14, name="Human-in-the-loop patterns",
            status="pass", evidence=f"Human oversight patterns found in {len(files_with_hitl)} file(s)")]
    else:
        return [CodeFinding(article=14, name="Human-in-the-loop patterns",
            status="warn", evidence="No human approval gates or confirmation patterns detected",
            fix_hint="Add human approval gates for high-risk actions (e.g., sending emails, modifying data)")]


def _check_rate_limiting(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for rate limiting / budget controls on LLM usage."""
    rate_patterns = [
        r'rate_limit', r'max_tokens', r'max_iterations', r'max_steps',
        r'budget', r'token_limit', r'cost_limit', r'max_retries',
        r'max_calls', r'throttle', r'cooldown', r'max_rpm',
    ]
    combined = "|".join(rate_patterns)
    files_with_limits = [fp for fp, content in file_contents.items()
                         if re.search(combined, content, re.IGNORECASE)]
    if files_with_limits:
        return [CodeFinding(article=14, name="Usage limits / budget controls",
            status="pass", evidence=f"Rate limiting or budget controls found in {len(files_with_limits)} file(s)")]
    else:
        return [CodeFinding(article=14, name="Usage limits / budget controls",
            status="warn", evidence="No rate limiting or token budget controls detected",
            fix_hint="Set max_tokens, max_iterations, or budget limits to prevent runaway agents")]


# ─────────────────────────────────────────────
# Article 15 — Robustness & Cybersecurity
# ─────────────────────────────────────────────

def _check_retry_logic(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for retry/backoff patterns for API resilience."""
    retry_patterns = [
        r'retry', r'backoff', r'tenacity', r'max_retries',
        r'exponential_backoff', r'with_retry', r'Retry\(',
    ]
    combined = "|".join(retry_patterns)
    files_with_retry = [fp for fp, content in file_contents.items()
                        if re.search(combined, content, re.IGNORECASE)]
    if files_with_retry:
        return [CodeFinding(article=15, name="Retry / backoff logic",
            status="pass", evidence=f"Retry/backoff patterns found in {len(files_with_retry)} file(s)")]
    else:
        return [CodeFinding(article=15, name="Retry / backoff logic",
            status="warn", evidence="No retry or backoff patterns detected for API calls",
            fix_hint="Add retry logic with exponential backoff for LLM API calls")]


def _check_injection_defense(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for prompt injection defense patterns."""
    injection_patterns = [
        r'injection', r'sanitize', r'escape', r'guardrail',
        r'content_filter', r'moderation', r'safety_check',
        r'prompt_guard', r'nemo_guardrails', r'rebuff',
        r'lakera', r'system_prompt.*?boundary',
    ]
    combined = "|".join(injection_patterns)
    files_with_defense = [fp for fp, content in file_contents.items()
                          if re.search(combined, content, re.IGNORECASE)]
    dangerous_patterns = [
        r'f".*\{.*input.*\}.*"',
        r'\.format\(.*input',
        r'user_message.*=.*input\(',
    ]
    dangerous_combined = "|".join(dangerous_patterns)
    files_with_danger = [fp for fp, content in file_contents.items()
                         if re.search(dangerous_combined, content)]
    findings = []
    if files_with_defense:
        findings.append(CodeFinding(article=15, name="Prompt injection defense",
            status="pass", evidence=f"Injection defense patterns found in {len(files_with_defense)} file(s)"))
    else:
        findings.append(CodeFinding(article=15, name="Prompt injection defense",
            status="warn", evidence="No prompt injection defense patterns detected",
            fix_hint="Add input sanitization or use guardrails to detect prompt injection attempts"))
    if files_with_danger:
        findings.append(CodeFinding(article=15, name="Unsafe input handling",
            status="warn",
            evidence=f"Possible raw user input in prompts in {len(files_with_danger)} file(s): {', '.join(_rel(f, scan_path) for f in files_with_danger[:3])}",
            fix_hint="Validate and sanitize user input before injecting into LLM prompts"))
    return findings


def _check_output_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if LLM outputs are validated before use."""
    output_patterns = [
        r'output_parser', r'OutputParser', r'PydanticOutputParser',
        r'JsonOutputParser', r'parse_output', r'validate_output',
        r'response_model', r'structured_output',
        r'output_schema', r'response_format',
    ]
    combined = "|".join(output_patterns)
    files_with_output = [fp for fp, content in file_contents.items()
                         if re.search(combined, content)]
    if files_with_output:
        return [CodeFinding(article=15, name="LLM output validation",
            status="pass", evidence=f"Output parsing/validation found in {len(files_with_output)} file(s)")]
    else:
        return [CodeFinding(article=15, name="LLM output validation",
            status="warn", evidence="No structured output validation detected",
            fix_hint="Use output parsers (Pydantic, JSON schema) to validate LLM responses before acting on them")]
