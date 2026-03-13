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
    return os.path.relpath(filepath, scan_path)


def _check_error_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
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
    patterns = [r'fallback', r'retry', r'backoff', r'with_fallbacks', r'with_retry', r'tenacity', r'max_retries', r'default_response']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=9, name="Fallback/recovery patterns", status="pass", evidence=f"Fallback patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=9, name="Fallback/recovery patterns", status="warn", evidence="No fallback or retry patterns detected",
        fix_hint="Add fallback logic for LLM failures (retry, default response, alternative model)")]


def _check_input_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'pydantic', r'BaseModel', r'validator', r'field_validator', r'validate_input', r'input_schema', r'json_schema', r'TypedDict', r'dataclass', r'InputGuard', r'sanitize']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content)]
    total = len(file_contents)
    if hits:
        return [CodeFinding(article=10, name="Input validation / schema enforcement", status="pass",
            evidence=f"Input validation found in {len(hits)}/{total} Python files (Pydantic, dataclass, or similar)")]
    return [CodeFinding(article=10, name="Input validation / schema enforcement", status="warn",
        evidence="No structured input validation detected (Pydantic, dataclass, TypedDict)",
        fix_hint="Use Pydantic models or dataclasses to validate inputs before LLM calls")]


def _check_pii_handling(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'pii', r'redact', r'mask_(?:data|pii|email|ssn|name)', r'anonymize', r'tokenize_pii', r'presidio', r'scrub', r'private_data', r'private_info', r'sensitive_data', r'sensitive_field', r'data_protection', r'gdpr', r'personal_data']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=10, name="PII handling in code", status="pass", evidence=f"PII-aware patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=10, name="PII handling in code", status="warn",
        evidence="No PII detection, redaction, or masking patterns found in code",
        fix_hint="Consider adding PII detection before sending data to LLM providers")]


def _check_docstrings(file_contents: dict, scan_path: str) -> List[CodeFinding]:
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
        return [CodeFinding(article=11, name="Code documentation (docstrings)", status="pass", evidence="No public functions/classes found to document")]
    pct = (documented_defs / total_defs * 100) if total_defs > 0 else 0
    if pct >= 60: status = "pass"
    elif pct >= 30: status = "warn"
    else: status = "fail"
    return [CodeFinding(article=11, name="Code documentation (docstrings)", status=status,
        evidence=f"{documented_defs}/{total_defs} public functions/classes have docstrings ({pct:.0f}%)",
        fix_hint="Add docstrings to public functions and classes explaining purpose and parameters")]


def _check_type_hints(file_contents: dict, scan_path: str) -> List[CodeFinding]:
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
    return [CodeFinding(article=11, name="Type annotations", status=status,
        evidence=f"{typed_defs}/{total_defs} public functions have type hints ({pct:.0f}%)",
        fix_hint="Add type hints to function signatures for better documentation and tooling")]


def _check_logging(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'import logging', r'from logging', r'getLogger', r'structlog', r'loguru', r'logger\.', r'logging\.']
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
    patterns = [r'opentelemetry', r'otel', r'trace_id', r'span_id', r'run_id', r'request_id', r'correlation_id', r'langsmith', r'langfuse', r'helicone', r'arize', r'wandb', r'mlflow', r'callbacks']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=12, name="Tracing / observability", status="pass", evidence=f"Tracing patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=12, name="Tracing / observability", status="warn",
        evidence="No tracing or observability integration detected",
        fix_hint="Add OpenTelemetry, LangSmith, or similar to track AI decisions")]


def _check_human_in_loop(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'human_in_the_loop', r'human_approval', r'require_approval', r'approval_gate', r'require_confirmation', r'confirmation_gate', r'confirm.*action', r'ask_human', r'human_input', r'HumanApprovalCallbackHandler', r'human_feedback', r'manual_review', r'approval_required', r'allow_human', r'human_oversight']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Human-in-the-loop patterns", status="pass", evidence=f"Human oversight patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Human-in-the-loop patterns", status="warn",
        evidence="No human approval gates or confirmation patterns detected",
        fix_hint="Add human approval gates for high-risk actions (e.g., sending emails, modifying data)")]


def _check_rate_limiting(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    patterns = [r'rate_limit', r'max_tokens', r'max_iterations', r'max_steps', r'budget', r'token_limit', r'cost_limit', r'max_retries', r'max_calls', r'throttle', r'cooldown', r'max_rpm']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Usage limits / budget controls", status="pass", evidence=f"Rate limiting or budget controls found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Usage limits / budget controls", status="warn",
        evidence="No rate limiting or token budget controls detected",
        fix_hint="Set max_tokens, max_iterations, or budget limits to prevent runaway agents")]


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
    patterns = [r'prompt.?injection', r'sql.?injection', r'inject.*(?:attack|detect|prevent|filter)', r'sanitize', r'escape_prompt', r'guardrail', r'content_filter', r'moderation', r'safety_check', r'prompt_guard', r'nemo_guardrails', r'rebuff', r'lakera', r'system_prompt.*?boundary']
    combined = "|".join(patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    danger_patterns = [r'f".*\{.*input.*\}.*"', r'\.format\(.*input', r'user_message.*=.*input\(']
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
    patterns = [r'output_parser', r'OutputParser', r'PydanticOutputParser', r'JsonOutputParser', r'parse_output', r'validate_output', r'response_model', r'structured_output', r'output_schema', r'response_format']
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
    """Check if agent actions are bound to the user who authorized them."""
    identity_binding_patterns = [
        r'user_id', r'user_email', r'authorized_by', r'delegated_by',
        r'on_behalf_of', r'acting_as', r'user_context', r'auth_context',
        r'identity_token', r'delegation_token', r'agent_user_binding',
        r'x-user-id', r'X-User-Id', r'user_identity',
        r'memory_store.*user', r'store.*memories.*user',
    ]
    combined = "|".join(identity_binding_patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Agent-to-user identity binding",
            status="pass", evidence=f"User identity binding found in {len(hits)} file(s) (user_id, memory store, or delegation tracking)")]
    return [CodeFinding(article=14, name="Agent-to-user identity binding",
        status="warn", evidence="No user identity binding detected. Agent actions are not tied to the authorizing user.",
        fix_hint="Track user_id or auth_context alongside every agent action so you can answer 'who authorized this?'")]


def _check_token_scope_validation(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if OAuth/API tokens are scoped and validated before use."""
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
    """Check if tokens have expiry/revocation handling or execution time-bounding."""
    expiry_patterns = [
        r'token_expir', r'expires_at', r'expires_in', r'refresh_token',
        r'token_refresh', r'revoke_token', r'revocation', r'is_expired',
        r'check_expiry', r'token_lifetime', r'session_timeout',
        r'max_agent_steps', r'max_iterations', r'execution_timeout',
        r'agent_timeout', r'step_limit',
    ]
    combined = "|".join(expiry_patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Token expiry / execution bounding",
            status="pass", evidence=f"Token expiry or execution boundary patterns found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Token expiry / execution bounding",
        status="fail", evidence="No token expiry or execution bounding detected. Agent may run indefinitely.",
        fix_hint="Implement token expiry, max_agent_steps, or execution timeouts so rogue agents can be stopped")]


def _check_action_audit_trail(file_contents: dict, scan_path: str) -> List[CodeFinding]:
    """Check if agent ACTIONS (not just LLM calls) are logged with context."""
    action_log_patterns = [
        r'action_log', r'audit_trail', r'audit_log', r'log_action',
        r'record_action', r'action_history', r'event_log',
        r'activity_log', r'action_record', r'decision_log',
        r'agent_action', r'tool_call.*log', r'log.*tool_call',
        r'execution_log', r'operation_log',
        r'CONTENT_TRACING_ENABLED', r'logging_tracer',
        r'tool_invocation.*log', r'log.*tool_invocation',
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
    boundary_patterns = [
        r'allowed_tools', r'tool_whitelist', r'blocked_tools',
        r'allowed_actions', r'action_filter', r'action_boundary',
        r'can_execute', r'permission_gate',
        r'restricted_actions', r'deny_list', r'allow_list',
        r'tool_filter', r'enabled_tools', r'disabled_tools',
        r'human_in_the_loop.*polic', r'confirmation_polic',
        r'approval_polic', r'tool_allowlist',
    ]
    combined = "|".join(boundary_patterns)
    hits = [fp for fp, content in file_contents.items() if re.search(combined, content, re.IGNORECASE)]
    if hits:
        return [CodeFinding(article=14, name="Agent action boundaries",
            status="pass", evidence=f"Action boundary controls found in {len(hits)} file(s)")]
    return [CodeFinding(article=14, name="Agent action boundaries",
        status="warn", evidence="No action boundaries detected. Agent has unrestricted tool/action access.",
        fix_hint="Define allowed_tools or action boundaries to limit what the agent can do with delegated auth")]
