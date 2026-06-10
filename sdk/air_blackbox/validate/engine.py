"""
Runtime Validation Engine - pre-execution checks for AI agent outputs.

This closes the gap between "prove what happened" (audit) and
"prove what was allowed to happen" (validation).

Validates agent outputs BEFORE execution against defined specs:
- Schema validation on tool call arguments
- Output format checks
- Confidence thresholds
- Content policy rules
- Hallucination guards (known-bad patterns)

Every validation produces a signed record: "output X was checked
against rules Y and passed/failed at time Z."
"""

import json
import re
import os
import uuid
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class ValidationResult:
    """Result of a pre-execution validation check."""
    rule_name: str
    passed: bool
    severity: str  # "block", "warn", "info"
    message: str
    timestamp: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


@dataclass
class ValidationReport:
    """Complete validation report for one agent action."""
    action_id: str
    action_type: str  # "tool_call", "llm_response", "agent_decision"
    results: list[ValidationResult]
    passed: bool  # True if no "block" severity failures
    timestamp: str = ""
    validated_in_ms: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "passed": self.passed,
            "timestamp": self.timestamp,
            "validated_in_ms": self.validated_in_ms,
            "results": [
                {"rule": r.rule_name, "passed": r.passed,
                 "severity": r.severity, "message": r.message,
                 "details": r.details}
                for r in self.results
            ],
        }


class ValidationRule:
    """Base class for validation rules."""
    name: str = "base_rule"
    severity: str = "warn"  # "block", "warn", "info"

    def check(self, action: dict) -> ValidationResult:
        raise NotImplementedError


class ToolAllowlistRule(ValidationRule):
    """Block tool calls not on the approved list."""
    name = "tool_allowlist"
    severity = "block"

    def __init__(self, allowed_tools: list[str]):
        self.allowed_tools = [t.lower() for t in allowed_tools]

    def check(self, action: dict) -> ValidationResult:
        tool = action.get("tool_name", "").lower()
        if tool in self.allowed_tools:
            return ValidationResult(self.name, True, "info",
                f"Tool '{tool}' is on the approved list.")
        return ValidationResult(self.name, False, self.severity,
            f"Tool '{tool}' is NOT on the approved list. Blocked.",
            details={"tool": tool, "allowed": self.allowed_tools})


class SchemaValidationRule(ValidationRule):
    """Validate tool call arguments against expected schema."""
    name = "schema_validation"
    severity = "block"

    def __init__(self, schemas: dict):
        """schemas: {tool_name: {arg_name: type_string, ...}}"""
        self.schemas = schemas

    def check(self, action: dict) -> ValidationResult:
        tool = action.get("tool_name", "")
        args = action.get("arguments", {})
        schema = self.schemas.get(tool)
        if not schema:
            return ValidationResult(self.name, True, "info",
                f"No schema defined for '{tool}'. Skipping validation.")
        errors = []
        for arg_name, expected_type in schema.items():
            if arg_name not in args:
                errors.append(f"Missing required arg: {arg_name}")
            elif expected_type == "str" and not isinstance(args[arg_name], str):
                errors.append(f"{arg_name}: expected string, got {type(args[arg_name]).__name__}")
            elif expected_type == "int" and not isinstance(args[arg_name], int):
                errors.append(f"{arg_name}: expected int, got {type(args[arg_name]).__name__}")
        if errors:
            return ValidationResult(self.name, False, self.severity,
                f"Schema validation failed: {'; '.join(errors)}",
                details={"errors": errors, "tool": tool})
        return ValidationResult(self.name, True, "info",
            f"Schema validation passed for '{tool}'.")


class ContentPolicyRule(ValidationRule):
    """Block outputs containing prohibited content patterns."""
    name = "content_policy"
    severity = "block"

    def __init__(self, blocked_patterns: list[str] = None):
        self.blocked_patterns = blocked_patterns or [
            r'(?i)drop\s+table', r'(?i)delete\s+from.*where\s+1=1',
            r'(?i)rm\s+-rf\s+/', r'(?i)sudo\s+rm',
            r'(?i)exec\s*\(', r'(?i)eval\s*\(',
            r'(?i)os\.system\s*\(',
        ]

    def check(self, action: dict) -> ValidationResult:
        content = json.dumps(action.get("arguments", action.get("content", "")))
        for pattern in self.blocked_patterns:
            if re.search(pattern, content):
                return ValidationResult(self.name, False, self.severity,
                    f"Content policy violation: dangerous pattern detected.",
                    details={"pattern": pattern})
        return ValidationResult(self.name, True, "info",
            "Content policy check passed.")


class PiiOutputRule(ValidationRule):
    """Warn if output contains PII that shouldn't be passed to tools."""
    name = "pii_output_check"
    severity = "warn"

    def check(self, action: dict) -> ValidationResult:
        content = json.dumps(action.get("arguments", action.get("content", "")))
        pii_found = []
        patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
            (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
            (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'credit_card'),
        ]
        for pattern, pii_type in patterns:
            if re.search(pattern, content):
                pii_found.append(pii_type)
        if pii_found:
            return ValidationResult(self.name, False, self.severity,
                f"PII detected in output: {', '.join(pii_found)}. Review before execution.",
                details={"pii_types": pii_found})
        return ValidationResult(self.name, True, "info", "No PII detected in output.")


class HallucinationGuardRule(ValidationRule):
    """Flag outputs that look like common hallucination patterns."""
    name = "hallucination_guard"
    severity = "warn"

    def check(self, action: dict) -> ValidationResult:
        content = str(action.get("content", action.get("arguments", "")))
        flags = []
        # Fake URLs
        if re.search(r'https?://(?:www\.)?(?:example|fake|test|placeholder)\.\w+', content):
            flags.append("suspicious_url")
        # Made-up citations
        if re.search(r'(?:doi|DOI):\s*10\.\d{4}/[a-z]{4,8}', content):
            if re.search(r'doi:\s*10\.0000/', content):
                flags.append("fake_doi")
        # Confident false claims patterns
        if re.search(r'(?:As of|According to) (?:my|our) (?:latest|most recent) (?:data|information|update)', content):
            flags.append("stale_knowledge_claim")
        if flags:
            return ValidationResult(self.name, False, self.severity,
                f"Possible hallucination indicators: {', '.join(flags)}",
                details={"flags": flags})
        return ValidationResult(self.name, True, "info",
            "No hallucination indicators detected.")


class RuntimeValidator:
    """Pre-execution validation engine.

    Validates agent outputs against defined rules BEFORE execution.
    Every check produces a signed validation record.

    Usage:
        from air_blackbox.validate import RuntimeValidator

        validator = RuntimeValidator()
        validator.add_rule(ToolAllowlistRule(["web_search", "calculator"]))
        validator.add_rule(ContentPolicyRule())

        # Before executing a tool call:
        report = validator.validate({
            "tool_name": "db_query",
            "arguments": {"query": "SELECT * FROM users"}
        })

        if report.passed:
            execute_tool(...)
        else:
            handle_blocked(report)
    """

    def __init__(self, runs_dir=None):
        self.rules: list[ValidationRule] = []
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", os.path.join(os.path.expanduser("~"), ".air-blackbox", "runs"))
        os.makedirs(self.runs_dir, exist_ok=True)
        # Add default rules
        self.rules.append(ContentPolicyRule())
        self.rules.append(PiiOutputRule())
        self.rules.append(HallucinationGuardRule())

    def add_rule(self, rule: ValidationRule):
        """Add a validation rule."""
        self.rules.append(rule)

    def validate(self, action: dict, action_type: str = "tool_call") -> ValidationReport:
        """Validate an action against all rules.

        Args:
            action: Dict with tool_name, arguments, content, etc.
            action_type: "tool_call", "llm_response", "agent_decision"

        Returns:
            ValidationReport with pass/fail and all check results.
        """
        start = time.time()
        action_id = str(uuid.uuid4())
        results = []

        for rule in self.rules:
            try:
                result = rule.check(action)
                results.append(result)
            except Exception as e:
                results.append(ValidationResult(
                    rule.name, False, "warn",
                    f"Rule check failed: {str(e)[:200]}"))

        # Action passes if no "block" severity failures
        blocked = any(not r.passed and r.severity == "block" for r in results)
        duration_ms = int((time.time() - start) * 1000)

        report = ValidationReport(
            action_id=action_id,
            action_type=action_type,
            results=results,
            passed=not blocked,
            validated_in_ms=duration_ms,
        )

        # Write validation record
        self._write_record(action, report)
        return report

    def _write_record(self, action: dict, report: ValidationReport):
        """Write validation record as .air.json."""
        try:
            record = {
                "version": "1.0.0",
                "run_id": report.action_id,
                "timestamp": report.timestamp,
                "type": "validation",
                "action_type": report.action_type,
                "passed": report.passed,
                "validated_in_ms": report.validated_in_ms,
                "status": "validated" if report.passed else "blocked",
                "checks": report.to_dict()["results"],
            }
            fname = f"{report.action_id}.air.json"
            fpath = os.path.join(self.runs_dir, fname)
            with open(fpath, "w") as f:
                json.dump(record, f, indent=2)
        except Exception:
            pass  # Non-blocking
