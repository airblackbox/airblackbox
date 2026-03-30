"""
AIR Blackbox — Lightweight anonymous telemetry.

Sends a single anonymous event per scan so we can understand
real usage patterns. No code, no file paths, no project names.

Opt out: set AIR_BLACKBOX_TELEMETRY=off in your environment.

What gets sent:
    - Random anonymous session ID (generated once, stored locally)
    - Command name (e.g., "comply", "discover")
    - Number of Python files scanned
    - Number of checks passing/failing/warning
    - Python version and OS
    - air-blackbox version
    - Timestamp

What NEVER gets sent:
    - Source code or file contents
    - File paths or project names
    - IP addresses (not logged server-side)
    - Any personally identifiable information
"""

import os
import sys
import uuid
import json
import platform
import threading
from pathlib import Path


# Telemetry endpoint — a simple Vercel serverless function
TELEMETRY_URL = "https://airblackbox.ai/api/telemetry"

# Local config file for anonymous ID
_CONFIG_DIR = Path.home() / ".air-blackbox"
_CONFIG_FILE = _CONFIG_DIR / "telemetry.json"


def _is_enabled() -> bool:
    """Check if telemetry is enabled. Opt out with AIR_BLACKBOX_TELEMETRY=off."""
    env = os.environ.get("AIR_BLACKBOX_TELEMETRY", "").lower()
    if env in ("off", "false", "0", "no", "disable", "disabled"):
        return False
    # Also check for CI environments — don't count CI runs
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return False
    return True


def _get_anonymous_id() -> str:
    """Get or create a stable anonymous ID for this machine."""
    try:
        if _CONFIG_FILE.exists():
            data = json.loads(_CONFIG_FILE.read_text())
            if "anonymous_id" in data:
                return data["anonymous_id"]
    except Exception:
        pass

    # Generate new ID
    anon_id = str(uuid.uuid4())
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps({
            "anonymous_id": anon_id,
            "created": __import__("datetime").datetime.utcnow().isoformat(),
            "note": "Anonymous telemetry ID for AIR Blackbox. "
                    "Set AIR_BLACKBOX_TELEMETRY=off to disable."
        }, indent=2))
    except Exception:
        pass  # If we can't write, use ephemeral ID

    return anon_id


def send_event(
    command: str,
    python_files: int = 0,
    checks_passing: int = 0,
    checks_warning: int = 0,
    checks_failing: int = 0,
    total_checks: int = 0,
    version: str = "unknown",
    extra: dict = None,
):
    """Send an anonymous telemetry event. Non-blocking, fire-and-forget."""
    if not _is_enabled():
        return

    event = {
        "anonymous_id": _get_anonymous_id(),
        "command": command,
        "python_files": python_files,
        "checks_passing": checks_passing,
        "checks_warning": checks_warning,
        "checks_failing": checks_failing,
        "total_checks": total_checks,
        "version": version,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os": platform.system(),
        "os_version": platform.release(),
        "arch": platform.machine(),
    }

    if extra:
        event.update(extra)

    # Fire and forget in a background thread — never block the CLI
    def _send():
        try:
            import httpx
            httpx.post(
                TELEMETRY_URL,
                json=event,
                timeout=3.0,
                follow_redirects=True,
            )
        except Exception:
            pass  # Silently fail — telemetry should never break the tool

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
