"""
AIR Blackbox Trust Layer for Anthropic Claude Agent SDK.

Drop-in audit trails, PII detection, injection scanning, and
risk-based tool gating for Claude Agent SDK sessions.

Usage (hooks — recommended):
    from air_blackbox.trust.claude_agent import air_claude_hooks

    options = ClaudeAgentOptions(
        hooks=air_claude_hooks(),
    )

Usage (permission handler):
    from air_blackbox.trust.claude_agent import air_permission_handler

    options = ClaudeAgentOptions(
        can_use_tool=air_permission_handler(),
    )

Full setup:
    from air_blackbox.trust.claude_agent import air_claude_options

    options = air_claude_options(
        prompt="Analyze this codebase",
        detect_pii=True,
        detect_injection=True,
        risk_gating=True,
    )
"""

import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Optional

# ── PII patterns ──

_PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', 'phone'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'credit_card'),
    (r'\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b', 'iban'),
]

# ── Injection patterns (15 weighted patterns from AIR trust) ──

_INJECTION_PATTERNS = [
    (r'ignore (?:all )?previous instructions', 0.9),
    (r'you are now (?:a |an )?(?:new |different )', 0.9),
    (r'ignore (?:all )?above instructions', 0.85),
    (r'disregard (?:all )?(?:previous|prior|above)', 0.85),
    (r'system prompt:', 0.85),
    (r'new instructions:', 0.8),
    (r'override:', 0.8),
    (r'forget (?:everything|all|your) (?:previous|prior)', 0.75),
    (r'pretend you (?:are|have)', 0.7),
    (r'act as (?:if|though) you', 0.7),
    (r'do not follow', 0.65),
    (r'bypass (?:safety|security|filter)', 0.6),
    (r'jailbreak', 0.6),
    (r'<\|system\|>', 0.5),
    (r'\\x[0-9a-f]{2}', 0.4),
]

# ── Risk classification (matches ConsentGate) ──

_RISK_MAP = {
    'CRITICAL': [
        'Bash', 'bash', 'shell', 'exec', 'execute', 'spawn',
        'rm', 'delete', 'kill', 'terminate',
    ],
    'HIGH': [
        'Write', 'Edit', 'NotebookEdit',
        'sql', 'database', 'send_email', 'deploy', 'git_push',
    ],
    'MEDIUM': [
        'WebFetch', 'WebSearch', 'Agent',
        'http_request', 'api_call', 'fetch',
    ],
    'LOW': [
        'Read', 'Glob', 'Grep',
        'file_read', 'search', 'query', 'list',
    ],
}


def _classify_risk(tool_name: str) -> str:
    """Classify a tool by EU AI Act risk level."""
    name_lower = tool_name.lower()
    for level, keywords in _RISK_MAP.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return level
    return 'MEDIUM'  # Default to medium for unknown tools


def _scan_pii(text: str) -> list[dict]:
    """Scan text for PII patterns. Returns list of alerts."""
    alerts = []
    for pattern, pii_type in _PII_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            alerts.append({
                'type': pii_type,
                'count': len(matches),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            })
    return alerts


def _scan_injection(text: str) -> tuple[list[dict], float]:
    """Scan text for injection patterns. Returns (alerts, confidence)."""
    alerts = []
    max_score = 0.0
    text_lower = text.lower()
    for pattern, weight in _INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            alerts.append({
                'pattern': pattern,
                'weight': weight,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            })
            max_score = max(max_score, weight)
    return alerts, max_score


def _write_record(record: dict, runs_dir: str):
    """Write .air.json audit record to runs directory."""
    try:
        os.makedirs(runs_dir, exist_ok=True)
        fname = f"{record['run_id']}.air.json"
        fpath = os.path.join(runs_dir, fname)
        with open(fpath, 'w') as f:
            json.dump(record, f, indent=2)
    except Exception:
        pass  # Non-blocking: recording failure never breaks the agent


def _extract_text_from_input(tool_input: dict) -> str:
    """Pull scannable text from tool input arguments."""
    parts = []
    for key in ('command', 'content', 'prompt', 'query', 'text',
                'new_string', 'old_string', 'file_path', 'url',
                'pattern', 'input'):
        val = tool_input.get(key, '')
        if isinstance(val, str) and val:
            parts.append(val)
    return ' '.join(parts)


# ── Hook callbacks ──

def _make_pre_tool_hook(
    runs_dir: str = './runs',
    detect_pii: bool = True,
    detect_injection: bool = True,
    injection_block_threshold: float = 0.8,
):
    """Create a PreToolUse hook that scans inputs and logs audit records."""

    async def pre_tool_hook(input_data, tool_use_id, context):
        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})
        session_id = input_data.get('session_id', '')

        # Classify risk
        risk_level = _classify_risk(tool_name)

        # Scan input text
        scannable = _extract_text_from_input(tool_input)
        pii_alerts = []
        injection_alerts = []
        injection_score = 0.0

        if detect_pii and scannable:
            pii_alerts = _scan_pii(scannable)

        if detect_injection and scannable:
            injection_alerts, injection_score = _scan_injection(scannable)

        # Write pre-tool audit record
        record = {
            'version': '1.0.0',
            'run_id': str(uuid.uuid4()),
            'trace_id': (tool_use_id or uuid.uuid4().hex)[:16],
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': 'pre_tool_call',
            'tool_name': tool_name,
            'risk_level': risk_level,
            'pii_alerts': pii_alerts,
            'injection_alerts': injection_alerts,
            'injection_score': injection_score,
            'status': 'scanned',
            'framework': 'claude_agent_sdk',
        }
        _write_record(record, runs_dir)

        # Block if injection detected above threshold
        if injection_alerts and injection_score >= injection_block_threshold:
            block_record = {
                **record,
                'run_id': str(uuid.uuid4()),
                'type': 'injection_blocked',
                'status': 'blocked',
            }
            _write_record(block_record, runs_dir)
            return {
                'systemMessage': (
                    f'[AIR] Prompt injection detected (confidence: {injection_score:.0%}). '
                    f'Tool call to {tool_name} blocked for safety.'
                ),
                'hookSpecificOutput': {
                    'hookEventName': input_data['hook_event_name'],
                    'permissionDecision': 'deny',
                    'permissionDecisionReason': (
                        f'AIR Blackbox: injection detected ({injection_score:.0%} confidence)'
                    ),
                },
            }

        # Log PII warning but don't block
        if pii_alerts:
            return {
                'systemMessage': (
                    f'[AIR] PII detected in {tool_name} input: '
                    f'{", ".join(a["type"] for a in pii_alerts)}. '
                    f'Consider redacting before sending.'
                ),
            }

        return {}

    return pre_tool_hook


def _make_post_tool_hook(runs_dir: str = './runs'):
    """Create a PostToolUse hook that logs every tool result."""

    async def post_tool_hook(input_data, tool_use_id, context):
        tool_name = input_data.get('tool_name', 'unknown')
        session_id = input_data.get('session_id', '')

        record = {
            'version': '1.0.0',
            'run_id': str(uuid.uuid4()),
            'trace_id': (tool_use_id or uuid.uuid4().hex)[:16],
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': 'tool_call',
            'tool_name': tool_name,
            'risk_level': _classify_risk(tool_name),
            'status': 'success',
            'framework': 'claude_agent_sdk',
        }
        _write_record(record, runs_dir)
        return {}

    return post_tool_hook


def _make_post_tool_failure_hook(runs_dir: str = './runs'):
    """Create a PostToolUseFailure hook that logs tool errors."""

    async def post_tool_failure_hook(input_data, tool_use_id, context):
        tool_name = input_data.get('tool_name', 'unknown')
        session_id = input_data.get('session_id', '')

        record = {
            'version': '1.0.0',
            'run_id': str(uuid.uuid4()),
            'trace_id': (tool_use_id or uuid.uuid4().hex)[:16],
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': 'tool_error',
            'tool_name': tool_name,
            'risk_level': _classify_risk(tool_name),
            'status': 'error',
            'framework': 'claude_agent_sdk',
        }
        _write_record(record, runs_dir)
        return {}

    return post_tool_failure_hook


def _make_stop_hook(runs_dir: str = './runs'):
    """Create a Stop hook that writes session summary record."""

    async def stop_hook(input_data, tool_use_id, context):
        session_id = input_data.get('session_id', '')

        record = {
            'version': '1.0.0',
            'run_id': str(uuid.uuid4()),
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': 'session_end',
            'status': 'completed',
            'framework': 'claude_agent_sdk',
        }
        _write_record(record, runs_dir)
        return {}

    return stop_hook


# ── Public API ──

def air_claude_hooks(
    runs_dir: str = './runs',
    detect_pii: bool = True,
    detect_injection: bool = True,
    injection_block_threshold: float = 0.8,
) -> dict:
    """Get AIR Blackbox hooks for ClaudeAgentOptions.

    Returns a hooks dict ready to pass to ClaudeAgentOptions(hooks=...).
    Hooks cover: PreToolUse (scan + gate), PostToolUse (audit log),
    PostToolUseFailure (error log), and Stop (session summary).

    Args:
        runs_dir: Directory for .air.json audit records. Default: ./runs
        detect_pii: Scan tool inputs for PII (email, SSN, etc.)
        detect_injection: Scan tool inputs for prompt injection patterns
        injection_block_threshold: Block tool calls above this injection
            confidence score (0.0 - 1.0). Default: 0.8

    Returns:
        Dict of hook event name → list of HookMatcher-compatible dicts.
        Pass directly to ClaudeAgentOptions(hooks=...).

    Example:
        from claude_agent_sdk import ClaudeAgentOptions
        from air_blackbox.trust.claude_agent import air_claude_hooks

        options = ClaudeAgentOptions(
            hooks=air_claude_hooks(runs_dir="./audit"),
        )
    """
    try:
        from claude_agent_sdk import HookMatcher
    except ImportError:
        # If SDK not installed, return plain dicts — still usable
        # when the caller constructs HookMatcher themselves
        raise ImportError(
            "claude-agent-sdk not installed. "
            "Run: pip install claude-agent-sdk"
        )

    pre_hook = _make_pre_tool_hook(
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
        injection_block_threshold=injection_block_threshold,
    )
    post_hook = _make_post_tool_hook(runs_dir=runs_dir)
    fail_hook = _make_post_tool_failure_hook(runs_dir=runs_dir)
    stop_hook = _make_stop_hook(runs_dir=runs_dir)

    return {
        'PreToolUse': [
            HookMatcher(hooks=[pre_hook]),  # Runs on ALL tools
        ],
        'PostToolUse': [
            HookMatcher(hooks=[post_hook]),
        ],
        'PostToolUseFailure': [
            HookMatcher(hooks=[fail_hook]),
        ],
        'Stop': [
            HookMatcher(hooks=[stop_hook]),
        ],
    }


def air_permission_handler(
    runs_dir: str = './runs',
    block_critical: bool = False,
    require_approval_high: bool = False,
):
    """Create a can_use_tool permission handler with risk classification.

    Returns an async function suitable for ClaudeAgentOptions(can_use_tool=...).

    Risk levels (from ConsentGate):
        CRITICAL: Bash, exec, delete, spawn → block or require approval
        HIGH: Write, Edit, database, deploy → log + optional approval
        MEDIUM: WebFetch, API calls → log
        LOW: Read, Grep, Glob → auto-allow

    Args:
        runs_dir: Directory for .air.json audit records.
        block_critical: If True, deny CRITICAL-risk tool calls entirely.
        require_approval_high: If True, return 'ask' for HIGH-risk tools.

    Example:
        from claude_agent_sdk import ClaudeAgentOptions
        from air_blackbox.trust.claude_agent import air_permission_handler

        options = ClaudeAgentOptions(
            can_use_tool=air_permission_handler(block_critical=True),
        )
    """
    try:
        from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny
    except ImportError:
        raise ImportError(
            "claude-agent-sdk not installed. "
            "Run: pip install claude-agent-sdk"
        )

    async def handler(tool_name, input_data, context):
        risk = _classify_risk(tool_name)

        # Write permission decision record
        record = {
            'version': '1.0.0',
            'run_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'type': 'permission_decision',
            'tool_name': tool_name,
            'risk_level': risk,
            'framework': 'claude_agent_sdk',
        }

        if risk == 'CRITICAL' and block_critical:
            record['status'] = 'denied'
            _write_record(record, runs_dir)
            return PermissionResultDeny(
                message=f'AIR Blackbox: {tool_name} blocked (CRITICAL risk)',
                interrupt=False,
            )

        if risk == 'HIGH' and require_approval_high:
            record['status'] = 'approval_required'
            _write_record(record, runs_dir)
            # Return deny with a message — the user will see why
            return PermissionResultDeny(
                message=f'AIR Blackbox: {tool_name} requires approval (HIGH risk)',
                interrupt=False,
            )

        record['status'] = 'allowed'
        _write_record(record, runs_dir)
        return PermissionResultAllow(updated_input=input_data)

    return handler


def air_claude_options(
    runs_dir: str = './runs',
    detect_pii: bool = True,
    detect_injection: bool = True,
    injection_block_threshold: float = 0.8,
    block_critical: bool = False,
    require_approval_high: bool = False,
    **kwargs,
):
    """Create ClaudeAgentOptions pre-configured with AIR Blackbox trust layer.

    Combines hooks (audit trails + scanning) with permission handler
    (risk-based gating) into a single options object.

    Args:
        runs_dir: Directory for .air.json audit records.
        detect_pii: Scan tool inputs for PII.
        detect_injection: Scan for prompt injection patterns.
        injection_block_threshold: Block above this score (0-1).
        block_critical: Deny CRITICAL-risk tools entirely.
        require_approval_high: Require approval for HIGH-risk tools.
        **kwargs: Additional ClaudeAgentOptions parameters.

    Returns:
        ClaudeAgentOptions with trust layer fully configured.

    Example:
        from air_blackbox.trust.claude_agent import air_claude_options

        options = air_claude_options(
            prompt="Analyze this codebase",
            detect_pii=True,
            risk_gating=True,
        )
        async with ClaudeSDKClient(options=options) as client:
            await client.query("Scan for vulnerabilities")
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions
    except ImportError:
        raise ImportError(
            "claude-agent-sdk not installed. "
            "Run: pip install claude-agent-sdk"
        )

    hooks = air_claude_hooks(
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
        injection_block_threshold=injection_block_threshold,
    )

    perm_handler = air_permission_handler(
        runs_dir=runs_dir,
        block_critical=block_critical,
        require_approval_high=require_approval_high,
    )

    return ClaudeAgentOptions(
        hooks=hooks,
        can_use_tool=perm_handler,
        **kwargs,
    )


def attach_trust(agent_options, gateway_url="http://localhost:8080"):
    """Attach AIR trust layer to ClaudeAgentOptions.

    This is the standard attach_trust() interface used by AirTrust.attach()
    for framework auto-detection.

    Args:
        agent_options: A ClaudeAgentOptions instance or dict.
        gateway_url: AIR gateway URL (for future gateway integration).

    Returns:
        Modified ClaudeAgentOptions with trust layer hooks added.
    """
    hooks = air_claude_hooks()

    # If it's a ClaudeAgentOptions instance, merge hooks
    if hasattr(agent_options, 'hooks'):
        if agent_options.hooks is None:
            agent_options.hooks = hooks
        else:
            # Merge: add AIR hooks to existing hooks
            for event, matchers in hooks.items():
                existing = agent_options.hooks.get(event, [])
                agent_options.hooks[event] = existing + matchers

    print(f"[AIR] Claude Agent SDK trust layer attached. Events → ./runs")
    return agent_options
