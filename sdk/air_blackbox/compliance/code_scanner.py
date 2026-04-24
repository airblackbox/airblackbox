"""
Code-level scanner — reads Python files and detects compliance-relevant patterns.

This module makes every project get a DIFFERENT score by actually reading
the Python source code and checking for real patterns.
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
    file_contents = {}
    for fp in py_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                file_contents[fp] = f.read()
        except Exception:
            continue
    findings = []
    findings.extend(_check_error_handling(file_contents, scan_path))
    findings.extend(_check_fallback_patterns(file_contents, scan_path))
    findings.extend(_check_input_validation(file_contents, scan_path))
    findings.extend(_check_pii_handling(file_contents, scan_path))
    findings.extend(_check_docstrings(file_contents, scan_path))
    findings.extend(_check_type_hints(file_contents, scan_path))
    findings.extend(_check_logging(file_contents, scan_path))
    findings.extend(_check_tracing(file_contents, scan_path))
    findings.extend(_check_human_in_loop(file_contents, scan_path))
    findings.extend(_check_rate_limiting(file_contents, scan_path))
    findings.extend(_check_retry_logic(file_contents, scan_path))
    findings.extend(_check_injection_defense(file_contents, scan_path))
    findings.extend(_check_output_validation(file_contents, scan_path))

    # === OAuth & Delegation (Articles 12 + 14) ===
    findings.extend(_check_oauth_delegation(file_contents, scan_path))
    findings.extend(_check_token_scope_validation(file_contents, scan_path))
    findings.extend(_check_token_expiry_revocation(file_contents, scan_path))
    findings.extend(_check_action_audit_trail(file_contents, scan_path))
    findings.extend(_check_action_boundaries(file_contents, scan_path))

    return findings


def _find_python_files(scan_path: str) -> List[str]:
    # Support single-file scanning (e.g., --scan ./agent.py)
    if os.path.isfile(scan_path) and scan_path.endswith(".py"):
        return [os.path.abspath(scan_path)]

    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", ".env", ".tox", ".mypy_cache", ".pytest_cache",
        "dist", "build", "egg-info", ".eggs", "site-packages",
        # Learned from LlamaIndex: community packs are being deleted and not maintained
        "deprecated", "archived",
    }
    py_files = []
    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith(".egg-info")]
        for fname in files:
            if fname.endswith(".py"):
                py_files.append(os.path.join(root, fname))
    return py_files


def _is_test_file(filepath: str) -> bool:
    """Return True if filepath is a test file (test dirs, test_*.py, conftest.py).
    These are excluded from docstring/type-hint coverage to match the web scanner
    which only processes source files via GitHub API.
    """
    parts = filepath.replace("\\", "/").split("/")
    # Check if any directory in the path is a test directory
    test_dirs = {"tests", "test", "testing", "test_utils"}
    for part in parts:
        if part.lower() in test_dirs:
            return True
    # Check filename patterns
    basename = os.path.basename(filepath)
    if basename.startswith("test_") or basename.endswith("_test.py"):
        return True
    if basename in ("conftest.py",):
        return True
    return False


def _source_files_only(file_contents: dict) -> dict:
    """Filter file_contents to exclude test files."""
    return {fp: content for fp, content in file_contents.items()
            if not _is_test_file(fp)}


def _rel(filepath: str, scan_path: str) -> str:
    return os.path.relpath(filepath, scan_path)


def _check_error_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    llm_call_patterns = [
        r'\.chat\.completions\.create\(', r'\.completions\.create\(',
        r'\.invoke\(', r'\.run\(', r'\.generate\(', r'\.predict\(',
        r'\.agenerate\(', r'\.ainvoke\(', r'ChatOpenAI\(', r'OpenAI\(',
        r'Anthropic\(',
    ]
    combined = "|".join(llm_call_patterns)
    # Framework-level error handling patterns (pipelines, workflows, etc.)
    # Learned from Haystack: frameworks often handle errors at pipeline level, not per-file
    framework_error_patterns = [
        r'Pipeline.*error', r'pipeline.*except', r'PipelineError',
        r'ComponentError', r'NodeError', r'StepError',
        r'on_error', r'error_handler', r'error_callback',
        r'handle_error', r'error_policy', r'retry_policy',
    ]
    framework_combined = "|".join(framework_error_patterns)
    files_with_llm_calls = []
    files_with_error_handling = []
    for fp, content in file_contents.items():
        if re.search(combined, content):
            files_with_llm_calls.append(fp)
            if re.search(r'\btry\b.*?\bexcept\b', content, re.DOTALL) or re.search(framework_combined, content, re.IGNORECASE):
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
    patterns = [r'fallback', r'retry', r'backoff', r'with_fallbacks', r'with_retry', r'tenacity', r'max_retries', r'default_response']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=9, name="Fallback/recovery patterns", status="pass", evidence=f"Fallback patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=9, name="Fallback/recovery patterns", status="warn", evidence="No fallback or retry patterns detected",
        fix_hint="Add fallback logic for LLM failures (retry, default response, alternative model)")]


def _check_input_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Strong patterns: always indicate input validation
    strong_patterns = [
        r'field_validator', r'validate_input', r'input_schema',
        r'json_schema', r'InputGuard', r'jsonschema\.validate',
    ]
    # Weak patterns: only count if LLM calls are also present in same file
    # (a BaseModel for a DB schema is NOT AI input validation)
    weak_patterns = [
        r'pydantic', r'BaseModel', r'validator', r'TypedDict',
        r'dataclass', r'Field\(',
    ]
    llm_patterns = [
        r'\.chat\.completions\.create\(', r'\.invoke\(', r'\.generate\(',
        r'ChatOpenAI\(', r'OpenAI\(', r'Anthropic\(', r'\.kickoff\(',
    ]
    llm_combined = "|".join(llm_patterns)
    strong_combined = "|".join(strong_patterns)
    weak_combined = "|".join(weak_patterns)

    hits = []
    for fp, content in file_contents.items():
        if re.search(strong_combined, content):
            hits.append(fp)
        elif re.search(weak_combined, content) and re.search(llm_combined, content):
            hits.append(fp)

    total = len(file_contents)
    if hits:
        return [CodeFinding(article=10, name="Input validation / schema enforcement", status="pass",
            evidence=f"Input validation found in {len(hits)}/{total} Python files (Pydantic, dataclass, or similar)")]
    return [CodeFinding(article=10, name="Input validation / schema enforcement", status="warn",
        evidence="No structured input validation detected (Pydantic, dataclass, TypedDict)",
        fix_hint="Use Pydantic models or dataclasses to validate inputs before LLM calls")]


def _check_pii_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Strong signals: actual PII detection/redaction libraries or explicit PII-handling code
    strong_patterns = [
        r'presidio', r'scrubadub', r'detect_pii', r'pii_detect',
        r'redact_pii', r'mask_pii', r'anonymize_pii', r'strip_pii',
        r'PiiDetect', r'PiiRedact', r'PiiFilter',
        r'mask_(?:email|ssn|phone|name|address)',
        r'gdpr_complian', r'data_protection_officer',
    ]
    # Moderate signals: awareness of PII concept (variable names, comments)
    moderate_patterns = [
        r'\bpii\b',  # Word boundary so "api" doesn't match
        r'redact(?:ed|ion|_data)', r'anonymiz(?:e|ed|ation)',
        r'personal_data', r'sensitive_data', r'private_data',
        r'data_classification', r'data_retention',
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [fp for fp, content in file_contents.items() if re.search(strong_combined, content, re.IGNORECASE)]
    moderate_hits = [fp for fp, content in file_contents.items()
                     if re.search(moderate_combined, content, re.IGNORECASE) and fp not in strong_hits]
    if strong_hits:
        return [CodeFinding(article=10, name="PII handling in code", status="pass",
            evidence=f"PII detection/redaction found in {len(strong_hits)} file(s) (library-grade)")]
    if moderate_hits and len(moderate_hits) >= 3:
        return [CodeFinding(article=10, name="PII handling in code", status="warn",
            evidence=f"PII-aware variable names or references in {len(moderate_hits)} file(s), but no detection/redaction library",
            fix_hint="Add actual PII detection (e.g., presidio, scrubadub) instead of just naming patterns")]
    return [CodeFinding(article=10, name="PII handling in code", status="warn",
        evidence="No PII detection, redaction, or masking patterns found in code",
        fix_hint="Add PII detection before sending data to LLM providers (e.g., presidio, scrubadub)")]


def _check_docstrings(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check docstring coverage, handling multi-line function signatures.
    Fixed in v1.3.1: joins multi-line signatures before searching for docstrings.
    """
    # Exclude test files — they tank docstring coverage with bare test_* functions
    source_files = _source_files_only(file_contents)
    total_defs = 0
    documented_defs = 0
    for fp, content in source_files.items():
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                if stripped.startswith("def _"):
                    i += 1
                    continue
                total_defs += 1
                # Skip past multi-line signature to find the docstring
                j = i + 1
                if stripped.startswith("def "):
                    # Join multi-line signatures (unbalanced parens or trailing backslash)
                    full_sig = stripped
                    while j < len(lines) and (
                        full_sig.rstrip().endswith("\\") or
                        full_sig.count("(") > full_sig.count(")")
                    ):
                        next_line = lines[j].strip()
                        if full_sig.rstrip().endswith("\\"):
                            full_sig = full_sig.rstrip()[:-1]
                        full_sig += " " + next_line
                        j += 1
                # Now look for docstring after the signature ends
                for k in range(j, min(j + 4, len(lines))):
                    next_line = lines[k].strip()
                    if next_line == "":
                        continue
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        documented_defs += 1
                    break
                i = j
            else:
                i += 1
    if total_defs == 0:
        return [CodeFinding(article=11, name="Code documentation (docstrings)", status="pass", evidence="No public functions/classes found to document")]
    pct = (documented_defs / total_defs * 100) if total_defs > 0 else 0
    if pct >= 60: status = "pass"
    elif pct >= 30: status = "warn"
    else: status = "fail"
    return [CodeFinding(article=11, name="Code documentation (docstrings)", status=status,
        evidence=f"{documented_defs}/{total_defs} public functions/classes have docstrings ({pct:.0f}%)",
        fix_hint="Add docstrings to public functions and classes explaining purpose and parameters")]


def _check_type_hints(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if functions use type hints (handles multi-line signatures).
    Fixed in v1.2.3: github.com/airblackbox/scanner/issues/2
    """
    TYPE_PATTERN = re.compile(
        r':\s*('
        r'str|int|float|bool|bytes|complex|object|type|None'
        r'|list|dict|set|tuple|frozenset'
        r'|List|Dict|Set|Tuple|FrozenSet'
        r'|Optional|Union|Any|Type|Callable|Coroutine'
        r'|Sequence|Iterable|Iterator|Generator|AsyncGenerator'
        r'|Mapping|MutableMapping|MutableSequence|MutableSet'
        r'|Literal|Annotated|TypeVar|TypeAlias|ClassVar|Final'
        r'|Protocol|NamedTuple|TypedDict'
        r'|Path|PurePath|UUID|Pattern|Match'
        r'|datetime|date|time|timedelta|Decimal'
        r'|[A-Z][a-zA-Z0-9_]*'
        r')'
    )
    # Exclude test files — test functions rarely have type hints
    source_files = _source_files_only(file_contents)
    total_defs = 0
    typed_defs = 0
    for fp, content in source_files.items():
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith("def ") and not stripped.startswith("def _"):
                full_sig = stripped
                j = i + 1
                while j < len(lines) and (
                    full_sig.rstrip().endswith("\\") or
                    full_sig.count("(") > full_sig.count(")")
                ):
                    next_line = lines[j].strip()
                    if full_sig.rstrip().endswith("\\"):
                        full_sig = full_sig.rstrip()[:-1]
                    full_sig += " " + next_line
                    j += 1
                total_defs += 1
                if "->" in full_sig or TYPE_PATTERN.search(full_sig):
                    typed_defs += 1
                i = j
            else:
                i += 1
    if total_defs == 0:
        return []
    pct = (typed_defs / total_defs * 100) if total_defs > 0 else 0
    if pct >= 50: status = "pass"
    elif pct >= 20: status = "warn"
    else: status = "fail"
    return [CodeFinding(article=11, name="Type annotations", status=status,
        evidence=f"{typed_defs}/{total_defs} public functions have type hints ({pct:.0f}%)",
        fix_hint="Add type hints to function signatures for better documentation and tooling")]


def _check_logging(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Require actual logger usage, not just `import logging`
    patterns = [r'logging\.getLogger', r'logging\.basicConfig',
        r'logging\.(?:debug|info|warning|error|critical)\(',
        r'structlog', r'loguru', r'logger\.(?:debug|info|warning|error)\(']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content)]
    total = len(file_contents)
    if not hits:
        return [CodeFinding(article=12, name="Application logging", status="fail",
            evidence="No logging framework detected (logging, structlog, loguru)",
            fix_hint="Add import logging and log key decisions, errors, and LLM interactions")]
    pct = len(hits) / total * 100 if total > 0 else 0
    return [CodeFinding(article=12, name="Application logging", status="pass" if pct >= 20 else "warn",
        evidence=f"Logging found in {len(hits)}/{total} files ({pct:.0f}%)")]


def _check_tracing(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Core tracing patterns — instrumentation is the modern standard
    # (learned from LlamaIndex: callback_manager is deprecated in favor of instrumentation module)
    # Learned from Haystack (Julian Risch): HAYSTACK_CONTENT_TRACING_ENABLED + logging_tracer.py
    # is real production audit capability, stronger than basic debug logging
    patterns = [
        r'opentelemetry', r'otel', r'trace_id', r'span_id', r'run_id',
        r'request_id', r'correlation_id', r'langsmith', r'langfuse',
        r'helicone', r'arize', r'wandb', r'mlflow',
        r'instrumentation', r'instrument_module', r'dispatcher',
        r'event_handler', r'event_bus', r'event_emitter',
        r'TracerProvider', r'tracer\.start_span', r'tracing_enabled',
        r'CONTENT_TRACING_ENABLED', r'logging_tracer',
        r'callbacks',  # kept for backward compat detection but lower signal
    ]
    # Production-grade tracing patterns (stronger signal)
    production_tracing = [
        r'CONTENT_TRACING_ENABLED', r'logging_tracer',
        r'opentelemetry', r'TracerProvider', r'langsmith', r'langfuse',
    ]
    combined = "|".join(patterns)
    prod_combined = "|".join(production_tracing)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    prod_hits = [fp for fp, content in file_contents.items() if re.search(prod_combined, content, re.IGNORECASE)]
    if hits:
        evidence = f"Tracing patterns found in {len(hits)} file(s)"
        if prod_hits:
            evidence += f" (includes {len(prod_hits)} with production-grade tracing)"
        return [CodeFinding(article=12, name="Tracing / observability", status="pass", evidence=evidence)]
    return [CodeFinding(article=12, name="Tracing / observability", status="warn",
        evidence="No tracing or observability integration detected",
        fix_hint="Add OpenTelemetry, LangSmith, or similar to track AI decisions")]


def _check_human_in_loop(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Core HITL patterns that always indicate human oversight
    patterns = [
        r'human_in_the_loop', r'human_approval', r'require_approval',
        r'approval_gate', r'require_confirmation', r'confirmation_gate',
        r'ask_human', r'human_input',
        r'HumanApprovalCallbackHandler', r'human_feedback',
        r'manual_review', r'approval_required', r'allow_human',
        r'human_oversight',
        r'confirmation_strategy', r'confirmation_polic',  # Haystack HITL
        r'interrupt_before', r'interrupt_after',  # LangGraph HITL
        r'air_gate', r'GateClient',  # AIR Blackbox gate
    ]
    # Removed: r'allow_delegation' -- in CrewAI this is agent-to-agent
    # delegation, NOT human oversight. False positive reported by
    # community (github.com/deepset-ai/haystack/issues/10810).
    # Removed: r'confirm.*action' -- too generic, matches JS confirm()
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]

    # Context-aware check: allow_delegation only counts if NOT in a
    # CrewAI Agent/Task constructor (where it means agent-to-agent)
    if not hits:
        crewai_patterns = r'(?:Agent|Task|Crew)\s*\('
        for fp, content in file_contents.items():
            if re.search(r'allow_delegation', content, re.IGNORECASE):
                if not re.search(crewai_patterns, content):
                    # allow_delegation in non-CrewAI context = real HITL
                    hits.append(fp)

    if hits:
        return [CodeFinding(article=14, name="Human-in-the-loop patterns", status="pass", evidence=f"Human oversight patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Human-in-the-loop patterns", status="warn",
        evidence="No human approval gates or confirmation patterns detected",
        fix_hint="Add human approval gates for high-risk actions (e.g., sending emails, modifying data)")]


def _check_rate_limiting(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Strong: actual budget/cost enforcement that a human can control
    strong_patterns = [
        r'rate_limit(?:er|ing)', r'RPMController', r'max_rpm',
        r'cost_limit', r'budget_limit', r'spend_limit',
        r'token_budget', r'usage_quota', r'quota_exceeded',
        r'throttle_agent', r'agent_budget',
    ]
    # Weak: config params that exist in every LLM wrapper (not human oversight)
    weak_patterns = [
        r'max_tokens', r'max_iterations', r'max_steps',
        r'max_retries', r'cooldown',
    ]
    strong_combined = "|".join(strong_patterns)
    weak_combined = "|".join(weak_patterns)
    strong_hits = [fp for fp, content in file_contents.items() if re.search(strong_combined, content, re.IGNORECASE)]
    weak_hits = [fp for fp, content in file_contents.items() if re.search(weak_combined, content, re.IGNORECASE)]
    if strong_hits:
        return [CodeFinding(article=14, name="Usage limits / budget controls", status="pass",
            evidence=f"Active rate limiting or budget controls found in {len(strong_hits)} file(s)")]
    if weak_hits and len(weak_hits) >= 5:
        return [CodeFinding(article=14, name="Usage limits / budget controls", status="warn",
            evidence=f"Basic execution limits (max_tokens, max_iterations) in {len(weak_hits)} file(s), but no explicit budget enforcement",
            fix_hint="Add explicit budget limits (cost_limit, usage_quota) that a human operator can configure")]
    return [CodeFinding(article=14, name="Usage limits / budget controls", status="warn",
        evidence="No rate limiting or token budget controls detected",
        fix_hint="Set cost_limit, usage_quota, or RPM limits to prevent runaway agents")]


def _check_retry_logic(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'retry', r'backoff', r'tenacity', r'max_retries', r'exponential_backoff', r'with_retry', r'Retry\(']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=15, name="Retry / backoff logic", status="pass", evidence=f"Retry/backoff patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=15, name="Retry / backoff logic", status="warn",
        evidence="No retry or backoff patterns detected for API calls",
        fix_hint="Add retry logic with exponential backoff for LLM API calls")]


def _check_injection_defense(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check for prompt injection defense patterns.

    Tightened in v1.4.1: 'sanitize' alone matches sanitize_filename, sanitize_url, etc.
    Now requires sanitize to be in a prompt/input/llm context, or uses specific security patterns.
    """
    # Strong: explicit security libraries/patterns
    strong_patterns = [
        r'prompt.?injection', r'sql.?injection',
        r'inject.*(?:attack|detect|prevent|filter)',
        r'escape_prompt', r'content_filter', r'moderation',
        r'prompt_guard', r'nemo_guardrails', r'rebuff', r'lakera',
        r'system_prompt.*?boundary',
        r'hallucination_guardrail', r'llm_guardrail',  # CrewAI built-in
        r'output_guardrail', r'input_guardrail',  # Guardrail patterns
        r'trust_policy', r'verify_trust', r'min_trust_score',
        r'jailbreak_detect', r'safety_check.*(?:prompt|input|llm)',
    ]
    # Moderate: guardrail/sanitize in AI-specific context (not just sanitize_filename)
    moderate_patterns = [
        r'(?:prompt|input|llm|agent).*sanitiz',
        r'sanitiz.*(?:prompt|input|query)',
        r'(?:Guardrail|GuardRail)(?:Component|Service|Check)',
        r'guardrails_config', r'guardrail_check',
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [fp for fp, content in file_contents.items() if re.search(strong_combined, content, re.IGNORECASE)]
    moderate_hits = [fp for fp, content in file_contents.items()
                     if re.search(moderate_combined, content, re.IGNORECASE) and fp not in strong_hits]
    hits = strong_hits + moderate_hits
    # Build danger patterns dynamically to avoid self-matching
    _fstr_pat = r'f".*\{.*' + "inp" + r"ut" + r'.*\}.*"'
    _fmt_pat = r'\.' + "form" + r"at\(.*" + "inp" + r"ut"
    _msg_pat = r'user_message.*=.*' + "inp" + r"ut\("
    danger_patterns = [_fstr_pat, _fmt_pat, _msg_pat]
    danger_combined = "|".join(danger_patterns)
    danger_hits = [fp for fp, content in file_contents.items() if re.search(danger_combined, content)]
    findings = []
    if hits:
        findings.append(CodeFinding(article=15, name="Prompt injection defense", status="pass", evidence=f"Injection defense patterns found in {len(hits)} file(s)"))
    else:
        findings.append(CodeFinding(article=15, name="Prompt injection defense", status="warn",
            evidence="No prompt injection defense patterns detected",
            fix_hint="Add input sanitization or use guardrails to detect prompt injection attempts"))
    if danger_hits:
        findings.append(CodeFinding(article=15, name="Unsafe input handling", status="warn",
            evidence=f"Possible raw user input in prompts in {len(danger_hits)} file(s): {', '.join(_rel(f, scan_path) for f in danger_hits[:3])}",
            fix_hint="Validate and sanitize user input before injecting into LLM prompts"))
    return findings


def _check_output_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    # Learned from CrewAI: output_pydantic enforces structured LLM responses at the task level
    patterns = [
        r'output_parser', r'OutputParser', r'PydanticOutputParser',
        r'JsonOutputParser', r'parse_output', r'validate_output',
        r'response_model', r'structured_output', r'output_schema',
        r'response_format', r'output_pydantic', r'output_json',  # CrewAI task-level
        r'expected_output',  # CrewAI task output spec
    ]
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content)]
    if hits:
        return [CodeFinding(article=15, name="LLM output validation", status="pass", evidence=f"Output parsing/validation found in {len(hits)} file(s)")]
    return [CodeFinding(article=15, name="LLM output validation", status="warn",
        evidence="No structured output validation detected",
        fix_hint="Use output parsers (Pydantic, JSON schema) to validate LLM responses before acting on them")]


# ─────────────────────────────────────────────
# Article 12 + 14 — OAuth & Delegation Tracking
# ─────────────────────────────────────────────

def _check_oauth_delegation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if agent actions are bound to the user who authorized them.

    Tightened in v1.4.1: bare 'user_id' is too common (every web app has it).
    Now requires delegation-specific patterns or user_id in agent/LLM context.
    """
    # Strong: explicit delegation/authorization binding
    strong_patterns = [
        r'authorized_by', r'delegated_by', r'on_behalf_of', r'acting_as',
        r'delegation_token', r'agent_user_binding', r'agent_identity',
        r'Fingerprint', r'agent_fingerprint',  # CrewAI identity
        r'AgentCard',  # CrewAI A2A identity
        r'identity_token', r'auth_context',
    ]
    # Moderate: user identity in agent/AI context (not just web framework user_id)
    moderate_patterns = [
        r'(?:agent|llm|crew|chain|pipeline).*user_id',
        r'user_id.*(?:agent|llm|crew|chain|pipeline)',
        r'memory_store.*user', r'store.*memories.*user',
        r'retrieve_memories.*user', r'add_memories.*user',
        r'user_context.*(?:agent|run|execute)',
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [fp for fp, content in file_contents.items() if re.search(strong_combined, content, re.IGNORECASE)]
    moderate_hits = [fp for fp, content in file_contents.items()
                     if re.search(moderate_combined, content, re.IGNORECASE) and fp not in strong_hits]
    if strong_hits:
        return [CodeFinding(article=14, name="Agent-to-user identity binding",
            status="pass", evidence=f"Delegation/identity binding found in {len(strong_hits)} file(s) (agent identity, delegation tokens)")]
    if moderate_hits:
        return [CodeFinding(article=14, name="Agent-to-user identity binding",
            status="warn", evidence=f"User identity referenced in agent context in {len(moderate_hits)} file(s), but no explicit delegation binding",
            fix_hint="Add explicit delegation tracking (authorized_by, delegation_token) alongside user_id")]
    return [CodeFinding(article=14, name="Agent-to-user identity binding",
        status="warn", evidence="No user identity binding in agent context. Agent actions not tied to authorizing user.",
        fix_hint="Track user_id or auth_context alongside every agent action so you can answer 'who authorized this?'")]


def _check_token_scope_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if OAuth/API tokens are scoped and validated before use.
    Note: confirmation_strategy_context in Haystack is request-scoped resource
    passing for HITL strategies, not permission scoping. We still count it as
    a positive signal because scoped resource passing IS a form of access control.
    """
    scope_patterns = [
        r'token_scope', r'required_scopes', r'check_scope', r'verify_scope',
        r'has_permission', r'permission_check', r'allowed_actions',
        r'action_whitelist', r'scope_validation', r'authorize_action',
        r'confirmation_strategy', r'strategy_context', r'oauth_scope',
        r'granted_permissions', r'check_permission',
    ]
    combined = "|".join(scope_patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Token scope / permission validation",
            status="pass", evidence=f"Scope or permission validation found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Token scope / permission validation",
        status="warn", evidence="No token scope validation detected. Agent may act beyond intended permissions.",
        fix_hint="Validate OAuth scopes or permissions before each agent action to prevent scope creep")]


def _check_token_expiry_revocation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if tokens have expiry/revocation handling or execution time-bounding.

    Tightened in v1.4.1: separated token security (strong) from basic config params (weak).
    max_iterations alone is not a security boundary — it's a config param.
    """
    # Strong: actual token lifecycle management
    strong_patterns = [
        r'token_expir', r'expires_at', r'refresh_token',
        r'token_refresh', r'revoke_token', r'revocation', r'is_expired',
        r'check_expiry', r'token_lifetime',
        r'execution_timeout', r'agent_timeout',
    ]
    # Weak: basic config that limits execution but isn't a security control
    weak_patterns = [
        r'max_agent_steps', r'max_iterations', r'step_limit',
        r'session_timeout', r'expires_in',
    ]
    strong_combined = "|".join(strong_patterns)
    weak_combined = "|".join(weak_patterns)
    strong_hits = [fp for fp, content in file_contents.items() if re.search(strong_combined, content, re.IGNORECASE)]
    weak_hits = [fp for fp, content in file_contents.items() if re.search(weak_combined, content, re.IGNORECASE)]
    if strong_hits:
        return [CodeFinding(article=14, name="Token expiry / execution bounding",
            status="pass", evidence=f"Token expiry or execution timeout found in {len(strong_hits)} file(s)")]
    if weak_hits and len(weak_hits) >= 3:
        return [CodeFinding(article=14, name="Token expiry / execution bounding",
            status="warn", evidence=f"Basic iteration/step limits in {len(weak_hits)} file(s), but no token expiry or revocation",
            fix_hint="Add token expiry (expires_at), refresh logic, and execution timeouts alongside step limits")]
    return [CodeFinding(article=14, name="Token expiry / execution bounding",
        status="fail", evidence="No token expiry or execution bounding detected. Agent may run indefinitely.",
        fix_hint="Implement token expiry, execution_timeout, or revocation so rogue agents can be stopped")]


def _check_action_audit_trail(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if agent ACTIONS (not just LLM calls) are logged with context."""
    # Learned from Haystack: CONTENT_TRACING_ENABLED + logging_tracer = production audit capability
    # Learned from CrewAI: event bus with typed events (agent_events, crew_events, etc.) = audit trail
    action_log_patterns = [
        r'action_log', r'audit_trail', r'audit_log', r'log_action',
        r'record_action', r'action_history', r'event_log',
        r'activity_log', r'action_record', r'decision_log',
        r'agent_action', r'tool_call.*log', r'log.*tool_call',
        r'execution_log', r'operation_log',
        r'CONTENT_TRACING_ENABLED', r'logging_tracer',  # Haystack production tracing
        r'tool_invocation.*log', r'log.*tool_invocation',
        r'agent_events', r'crew_events', r'tool_usage_events',  # CrewAI event bus
        r'llm_events', r'flow_events', r'system_events',  # CrewAI event types
        r'emit_event', r'on_event', r'event_handler',  # Generic event bus patterns
    ]
    combined = "|".join(action_log_patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=12, name="Agent action audit trail",
            status="pass", evidence=f"Action-level audit logging found in {len(hits)} file(s)")]
    return [CodeFinding(article=12, name="Agent action audit trail",
        status="warn", evidence="No action-level audit trail detected. Agent actions (emails, API calls, purchases) are not logged.",
        fix_hint="Log every agent action (not just LLM calls) with user_id, timestamp, action_type, and target")]


def _check_action_boundaries(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if there are limits on what actions an agent can take."""
    # Learned from Haystack: human_in_the_loop/policies.py is the real action boundary system
    # Learned from Haystack: is_allowed in serialization.py is deserialization safety, NOT action boundaries
    boundary_patterns = [
        r'allowed_tools', r'tool_whitelist', r'blocked_tools',
        r'allowed_actions', r'action_filter', r'action_boundary',
        r'can_execute', r'permission_gate',
        r'restricted_actions', r'deny_list', r'allow_list',
        r'tool_filter', r'enabled_tools', r'disabled_tools',
        r'human_in_the_loop.*polic', r'confirmation_polic',
        r'approval_polic', r'tool_allowlist',
        r'action_polic', r'execution_polic',  # Haystack policy patterns
    ]
    combined = "|".join(boundary_patterns)
    # Exclude serialization files — is_allowed in serialization is deserialization safety, not action boundaries
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)
            and 'serializ' not in os.path.basename(fp).lower()]
    if hits:
        return [CodeFinding(article=14, name="Agent action boundaries",
            status="pass", evidence=f"Action boundary controls found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Agent action boundaries",
        status="warn", evidence="No action boundaries detected. Agent has unrestricted tool/action access.",
        fix_hint="Define allowed_tools or action boundaries to limit what the agent can do with delegated auth")]
