"""
RuntimeMonitor - real-time compliance monitoring for AI agents.

Sits alongside the Gate and watches every interaction for:
  1. PII leakage (email, SSN, phone, credit card)
  2. Prompt injection attempts
  3. Boundary violations (unauthorized tool usage)
  4. Cost/token runaway (budget overruns, prompt loops)

Each violation is:
  - Logged as a structured event
  - Written to the HMAC-SHA256 audit chain (Art. 12)
  - Optionally blocks the action (configurable per check)

Usage (standalone):
    from air_blackbox.gate.runtime import RuntimeMonitor

    monitor = RuntimeMonitor(runs_dir="./runs")

    # Check text before sending to LLM
    result = monitor.check(text="Please email john@example.com")
    if result.has_violations:
        print(result.violations)  # [Violation(type='pii', ...)]

Usage (with Gate):
    from air_blackbox.gate import Gate, Covenant
    from air_blackbox.gate.runtime import RuntimeMonitor

    covenant = Covenant.from_yaml("covenant.yaml")
    monitor = RuntimeMonitor(runs_dir="./runs")
    gate = Gate(covenant=covenant)

    # Check input before authorizing
    result = monitor.check(
        text=user_prompt,
        tool_names=["send_email", "read_db"],
        token_count=1500,
    )

    if result.blocked:
        print("Blocked:", result.block_reasons)
    else:
        receipt = gate.authorize("my-agent", "process", payload=user_prompt)
"""

import logging
import os
import re
import time
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from air_blackbox.trust.chain import AuditChain

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Canonical PII and injection patterns
# These are the single source of truth. Trust layers should import from here.
#
# Two formats exported:
#   PII_PATTERNS / INJECTION_PATTERNS         - compiled re for RuntimeMonitor
#   PII_PATTERN_STRINGS / INJECTION_PATTERN_STRINGS - raw strings for trust layers
# ---------------------------------------------------------------------------

# Raw string definitions (single source of truth)
PII_PATTERN_STRINGS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', 'phone'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'credit_card'),
]

INJECTION_PATTERN_STRINGS = [
    r'ignore (?:all )?previous instructions',
    r'ignore (?:all )?above instructions',
    r'disregard (?:all )?previous',
    r'you are now',
    r'system prompt:',
    r'new instructions:',
    r'override:',
    r'forget (?:all )?(?:your )?(?:previous )?instructions',
    r'act as (?:a |an )?(?:different|new)',
    r'bypass (?:all )?(?:safety|security|content)',
]

# Compiled versions for RuntimeMonitor internal use
PII_PATTERNS = [(re.compile(p), t) for p, t in PII_PATTERN_STRINGS]
INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERN_STRINGS]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class ViolationType(str, Enum):
    """Types of runtime violations the monitor can detect."""
    PII = "pii"
    INJECTION = "injection"
    BOUNDARY = "boundary"
    TOKEN_BUDGET = "token_budget"
    PROMPT_LOOP = "prompt_loop"
    TOOL_BLOCKED = "tool_blocked"
    ERROR_SPIRAL = "error_spiral"


class Severity(str, Enum):
    """How serious is this violation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(str, Enum):
    """What to do when a violation is detected."""
    LOG = "log"         # Record it but allow
    WARN = "warn"       # Record + return warning
    BLOCK = "block"     # Record + prevent the action


@dataclass
class Violation:
    """A single runtime violation."""
    type: ViolationType
    severity: Severity
    action: Action
    message: str
    details: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "action": self.action.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class CheckResult:
    """Result of a runtime check. Contains all violations found."""
    violations: list = field(default_factory=list)
    checked_at: str = ""
    check_duration_ms: float = 0.0

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.utcnow().isoformat() + "Z"

    @property
    def has_violations(self) -> bool:
        """Were any violations found?"""
        return len(self.violations) > 0

    @property
    def blocked(self) -> bool:
        """Should this request be blocked?"""
        return any(v.action == Action.BLOCK for v in self.violations)

    @property
    def block_reasons(self) -> list:
        """Why was this request blocked? Returns list of messages."""
        return [v.message for v in self.violations if v.action == Action.BLOCK]

    @property
    def warnings(self) -> list:
        """Non-blocking violations that should be surfaced."""
        return [v for v in self.violations if v.action == Action.WARN]

    @property
    def pii_found(self) -> list:
        """PII types detected (e.g. ['email', 'ssn'])."""
        return [
            v.details.get("pii_type", "unknown")
            for v in self.violations
            if v.type == ViolationType.PII
        ]

    def to_dict(self) -> dict:
        return {
            "violations": [v.to_dict() for v in self.violations],
            "has_violations": self.has_violations,
            "blocked": self.blocked,
            "checked_at": self.checked_at,
            "check_duration_ms": self.check_duration_ms,
        }


# ---------------------------------------------------------------------------
# Runtime monitor configuration
# ---------------------------------------------------------------------------

@dataclass
class RuntimeConfig:
    """Configuration for the RuntimeMonitor.

    All checks are enabled by default. Disable individual checks
    or change their action (log/warn/block) as needed.

    Args:
        detect_pii: Scan for PII patterns (email, SSN, phone, credit card)
        pii_action: What to do when PII is found
        detect_injection: Scan for prompt injection attempts
        injection_action: What to do when injection is detected
        detect_boundary: Check tool usage against allowlist/blocklist
        boundary_action: What to do when boundary is violated
        tool_allowlist: Only these tools are permitted (empty = all allowed)
        tool_blocklist: These tools are never permitted
        detect_token_runaway: Monitor token usage against budget
        token_budget: Max tokens per session (0 = unlimited)
        token_action: What to do when budget is exceeded
        detect_prompt_loop: Detect repeated identical prompts
        loop_threshold: How many identical prompts before flagging
        loop_action: What to do when loop is detected
        detect_error_spiral: Detect repeated errors
        error_threshold: How many errors before flagging
        error_action: What to do when error spiral is detected
    """
    # PII detection
    detect_pii: bool = True
    pii_action: Action = Action.WARN

    # Injection detection
    detect_injection: bool = True
    injection_action: Action = Action.BLOCK

    # Boundary / tool enforcement
    detect_boundary: bool = True
    boundary_action: Action = Action.BLOCK
    tool_allowlist: list = field(default_factory=list)
    tool_blocklist: list = field(default_factory=list)

    # Token budget
    detect_token_runaway: bool = True
    token_budget: int = 0  # 0 = unlimited
    token_action: Action = Action.WARN

    # Prompt loop detection
    detect_prompt_loop: bool = True
    loop_threshold: int = 3
    loop_action: Action = Action.BLOCK

    # Error spiral detection
    detect_error_spiral: bool = True
    error_threshold: int = 5
    error_action: Action = Action.BLOCK


# ---------------------------------------------------------------------------
# The RuntimeMonitor
# ---------------------------------------------------------------------------

class RuntimeMonitor:
    """Real-time compliance monitor for AI agent interactions.

    Watches every interaction for PII, injection, boundary violations,
    and cost/token runaway. Writes all violations to the HMAC-SHA256
    audit chain for tamper-evident compliance evidence.

    The monitor is stateful: it tracks token usage, prompt history,
    and error counts across a session. Call reset() between sessions
    if reusing the same monitor instance.

    Args:
        config: RuntimeConfig with check settings (defaults are sane)
        runs_dir: Where to write audit chain records
        signing_key: HMAC key for the audit chain
        session_id: Identifier for this monitoring session
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        runs_dir: Optional[str] = None,
        signing_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.config = config or RuntimeConfig()
        self._session_id = session_id or ""
        self._runs_dir = runs_dir or os.path.join(
            os.path.expanduser("~"), ".air-blackbox", "runtime"
        )
        os.makedirs(self._runs_dir, exist_ok=True)

        # Audit chain for violation records
        self._chain = AuditChain(
            runs_dir=self._runs_dir,
            signing_key=signing_key,
        )

        # Session state for stateful checks
        self._total_tokens: int = 0
        self._prompt_history: list = []  # Recent prompts for loop detection
        self._error_count: int = 0
        self._violation_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(
        self,
        text: str = "",
        tool_names: Optional[list] = None,
        token_count: int = 0,
        is_error: bool = False,
        metadata: Optional[dict] = None,
    ) -> CheckResult:
        """Run all enabled checks against the input.

        This is the main entry point. Call it before every LLM call
        or tool execution to catch violations in real time.

        Args:
            text: The prompt or response text to scan
            tool_names: Tools being invoked (for boundary checks)
            token_count: Tokens used in this interaction
            is_error: Whether this interaction resulted in an error
            metadata: Extra context to include in violation records

        Returns:
            CheckResult with any violations found
        """
        start = time.monotonic()
        violations = []

        # 1. PII detection
        if self.config.detect_pii and text:
            violations.extend(self._check_pii(text))

        # 2. Injection detection
        if self.config.detect_injection and text:
            violations.extend(self._check_injection(text))

        # 3. Boundary / tool enforcement
        if self.config.detect_boundary and tool_names:
            violations.extend(self._check_boundary(tool_names))

        # 4. Token budget
        if self.config.detect_token_runaway and token_count > 0:
            self._total_tokens += token_count
            violations.extend(self._check_token_budget())

        # 5. Prompt loop detection
        if self.config.detect_prompt_loop and text:
            violations.extend(self._check_prompt_loop(text))

        # 6. Error spiral
        if self.config.detect_error_spiral and is_error:
            self._error_count += 1
            violations.extend(self._check_error_spiral())

        elapsed_ms = (time.monotonic() - start) * 1000

        result = CheckResult(
            violations=violations,
            check_duration_ms=round(elapsed_ms, 2),
        )

        # Write violations to audit chain
        if violations:
            self._violation_count += len(violations)
            self._write_violations(violations, metadata)

        return result

    def record_error(self) -> CheckResult:
        """Record an error for spiral detection without scanning text.

        Call this when a tool call or LLM call fails, to track
        the error count and potentially flag an error spiral.
        """
        return self.check(is_error=True)

    def record_tokens(self, count: int) -> CheckResult:
        """Record token usage without scanning text.

        Call this when you know the token count from an LLM response
        but don't need to scan the text content.
        """
        return self.check(token_count=count)

    def reset(self) -> None:
        """Reset session state. Call between sessions."""
        self._total_tokens = 0
        self._prompt_history = []
        self._error_count = 0
        self._violation_count = 0

    @property
    def session_stats(self) -> dict:
        """Current session statistics."""
        return {
            "session_id": self._session_id,
            "total_tokens": self._total_tokens,
            "error_count": self._error_count,
            "violation_count": self._violation_count,
            "prompt_count": len(self._prompt_history),
            "chain_records": self._chain.record_count,
        }

    # ------------------------------------------------------------------
    # Detection checks
    # ------------------------------------------------------------------

    def _check_pii(self, text: str) -> list:
        """Scan text for PII patterns."""
        violations = []
        for pattern, pii_type in PII_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                violations.append(Violation(
                    type=ViolationType.PII,
                    severity=Severity.HIGH if pii_type in ("ssn", "credit_card") else Severity.MEDIUM,
                    action=self.config.pii_action,
                    message=f"PII detected: {pii_type} ({len(matches)} occurrence(s))",
                    details={
                        "pii_type": pii_type,
                        "count": len(matches),
                        # Never log the actual PII values
                    },
                ))
        return violations

    def _check_injection(self, text: str) -> list:
        """Scan text for prompt injection attempts."""
        violations = []
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(Violation(
                    type=ViolationType.INJECTION,
                    severity=Severity.CRITICAL,
                    action=self.config.injection_action,
                    message=f"Prompt injection detected: '{match.group()}'",
                    details={
                        "matched_pattern": pattern.pattern,
                    },
                ))
                # One injection finding is enough to flag it
                break
        return violations

    def _check_boundary(self, tool_names: list) -> list:
        """Check tool usage against allowlist/blocklist."""
        violations = []

        for tool in tool_names:
            # Blocklist check (always wins)
            if self.config.tool_blocklist and tool in self.config.tool_blocklist:
                violations.append(Violation(
                    type=ViolationType.TOOL_BLOCKED,
                    severity=Severity.HIGH,
                    action=self.config.boundary_action,
                    message=f"Blocked tool: '{tool}' is on the blocklist",
                    details={"tool": tool, "reason": "blocklist"},
                ))
                continue

            # Allowlist check (if set, only listed tools are permitted)
            if self.config.tool_allowlist and tool not in self.config.tool_allowlist:
                violations.append(Violation(
                    type=ViolationType.BOUNDARY,
                    severity=Severity.HIGH,
                    action=self.config.boundary_action,
                    message=f"Unauthorized tool: '{tool}' is not on the allowlist",
                    details={"tool": tool, "reason": "not_in_allowlist"},
                ))

        return violations

    def _check_token_budget(self) -> list:
        """Check if token usage exceeds the budget."""
        if self.config.token_budget <= 0:
            return []

        if self._total_tokens > self.config.token_budget:
            overage = self._total_tokens - self.config.token_budget
            pct = round((self._total_tokens / self.config.token_budget) * 100, 1)
            return [Violation(
                type=ViolationType.TOKEN_BUDGET,
                severity=Severity.HIGH if pct > 150 else Severity.MEDIUM,
                action=self.config.token_action,
                message=f"Token budget exceeded: {self._total_tokens}/{self.config.token_budget} ({pct}%)",
                details={
                    "total_tokens": self._total_tokens,
                    "budget": self.config.token_budget,
                    "overage": overage,
                    "percent": pct,
                },
            )]

        return []

    def _check_prompt_loop(self, text: str) -> list:
        """Detect repeated identical prompts (agent stuck in a loop)."""
        # Keep a rolling window of recent prompts
        self._prompt_history.append(text)

        # Only keep the last N * 2 prompts (enough to detect loops)
        max_history = self.config.loop_threshold * 2
        if len(self._prompt_history) > max_history:
            self._prompt_history = self._prompt_history[-max_history:]

        # Count how many of the last N prompts are identical to this one
        recent = self._prompt_history[-self.config.loop_threshold:]
        identical_count = sum(1 for p in recent if p == text)

        if identical_count >= self.config.loop_threshold:
            return [Violation(
                type=ViolationType.PROMPT_LOOP,
                severity=Severity.HIGH,
                action=self.config.loop_action,
                message=f"Prompt loop detected: same prompt repeated {identical_count} times",
                details={
                    "repeat_count": identical_count,
                    "threshold": self.config.loop_threshold,
                    # Truncated preview, never full prompt
                    "prompt_preview": text[:100] + "..." if len(text) > 100 else text,
                },
            )]

        return []

    def _check_error_spiral(self) -> list:
        """Detect repeated errors (agent failing repeatedly)."""
        if self._error_count >= self.config.error_threshold:
            return [Violation(
                type=ViolationType.ERROR_SPIRAL,
                severity=Severity.CRITICAL,
                action=self.config.error_action,
                message=f"Error spiral: {self._error_count} consecutive errors",
                details={
                    "error_count": self._error_count,
                    "threshold": self.config.error_threshold,
                },
            )]
        return []

    # ------------------------------------------------------------------
    # Audit chain integration
    # ------------------------------------------------------------------

    def _write_violations(self, violations: list, metadata: Optional[dict] = None) -> None:
        """Write violations to the audit chain as compliance evidence."""
        record = {
            "type": "runtime_violation",
            "session_id": self._session_id,
            "violations": [v.to_dict() for v in violations],
            "blocked": any(v.action == Action.BLOCK for v in violations),
            "session_stats": {
                "total_tokens": self._total_tokens,
                "error_count": self._error_count,
                "violation_count": self._violation_count,
            },
        }
        if metadata:
            record["metadata"] = metadata

        try:
            self._chain.write(record)
        except Exception:
            # Non-blocking: chain failure never breaks the agent
            logger.warning("Failed to write violation to audit chain")
