"""Input validation and data verification.

Provides validation utilities for ensuring data integrity,
input safety, and compliance with validation requirements.
"""

from air_blackbox.validate.engine import (
    RuntimeValidator,
    ValidationResult,
    ValidationReport,
    ToolAllowlistRule,
    SchemaValidationRule,
    ContentPolicyRule,
    PiiOutputRule,
    HallucinationGuardRule,
)

__all__ = [
    "RuntimeValidator",
    "ValidationResult",
    "ValidationReport",
    "ToolAllowlistRule",
    "SchemaValidationRule",
    "ContentPolicyRule",
    "PiiOutputRule",
    "HallucinationGuardRule",
    "validate_action",
]


def validate_action(action_type: str, tool_name: str, risk_level: str = None) -> dict:
    """Validate an agent action before execution (Article 14 compliance).

    Runs content policy, PII, and hallucination checks against the action.
    Returns approval status and any policy violations.

    Args:
        action_type: 'tool_call', 'file_write', 'api_call', 'shell_exec', etc.
        tool_name: name of the tool/function being called
        risk_level: optional override ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
    """
    from air_blackbox.trust.chain import RiskClassification

    # Build action dict for validator
    action = {
        "action_type": action_type,
        "tool_name": tool_name,
        "arguments": {},
    }

    # Classify risk if not provided
    if not risk_level:
        from air_blackbox_mcp.scanner import classify_risk as _classify
        classification = _classify(tool_name)
        risk_level = classification.get("risk_level", "MEDIUM")

    requires_approval = risk_level in ("CRITICAL", "HIGH")

    # Run validation engine
    validator = RuntimeValidator()
    report = validator.validate(action, action_type=action_type)

    return {
        "tool_name": tool_name,
        "action_type": action_type,
        "risk_level": risk_level,
        "requires_human_approval": requires_approval,
        "validation_passed": report.passed,
        "checks": report.to_dict()["results"],
        "recommendation": (
            "BLOCK: Requires human approval before execution."
            if requires_approval and not report.passed
            else "APPROVED: Action within policy bounds."
            if report.passed
            else "WARN: Policy violations detected. Review before execution."
        ),
    }
