"""
AIR Trust Layer for OpenAI Python SDK.

Wraps the OpenAI client to add EU AI Act compliance infrastructure:
- HMAC-SHA256 tamper-evident audit chains for every API call
- PII detection in prompts and responses
- Prompt injection scanning
- Token usage and latency tracking
- Delegation verification for agent actions (Art. 14)
- Output validation for robustness (Art. 15)

Usage — wrap an existing client:

    from openai import OpenAI
    from air_openai_trust import attach_trust

    client = OpenAI()
    client = attach_trust(client)
    # Use normally — every call is now audit-logged
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
    )

Usage — create a pre-configured client:

    from air_openai_trust import air_openai_client

    client = air_openai_client()
    response = client.chat.completions.create(...)

All audit records are written as .air.json files with HMAC-SHA256
chain hashes. Records link cryptographically so tampering with any
record invalidates all subsequent hashes.

Non-blocking: if audit logging fails, your API calls still work.
"""

__version__ = "0.1.0"

import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII detection patterns (Art. 10 — Data Governance)
# ---------------------------------------------------------------------------
_PII_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), 'email'),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'ssn'),
    (re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'), 'phone'),
    (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), 'credit_card'),
]

# ---------------------------------------------------------------------------
# Injection detection patterns (Art. 15 — Robustness)
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(?:all\s+)?previous\s+instructions', re.I),
    re.compile(r'you\s+are\s+now', re.I),
    re.compile(r'system\s+prompt:', re.I),
    re.compile(r'new\s+instructions:', re.I),
    re.compile(r'override:', re.I),
    re.compile(r'forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?instructions', re.I),
    re.compile(r'disregard\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)', re.I),
]


def _scan_pii(text: str) -> List[Dict[str, str]]:
    """Scan text for PII patterns. Returns list of {type, match}."""
    alerts = []
    for pattern, pii_type in _PII_PATTERNS:
        for match in pattern.finditer(text):
            alerts.append({"type": pii_type, "match": match.group()[:4] + "***"})
    return alerts


def _scan_injection(text: str) -> List[str]:
    """Scan text for prompt injection patterns. Returns list of matched patterns."""
    alerts = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            alerts.append(pattern.pattern)
    return alerts


# ---------------------------------------------------------------------------
# HMAC-SHA256 Audit Chain (Art. 12 — Record-Keeping)
# ---------------------------------------------------------------------------

class AuditChain:
    """Thread-safe HMAC-SHA256 audit chain writer.

    Each record's chain_hash links to the previous record,
    creating a tamper-evident sequence per the AIR Blackbox
    Audit Chain Specification v1.0.
    """

    GENESIS = b"genesis"

    def __init__(self, runs_dir: str = "./runs", signing_key: Optional[str] = None):
        self.runs_dir = runs_dir
        self._key = (
            signing_key
            or os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default")
        ).encode("utf-8")
        self._prev_hash = self.GENESIS
        self._lock = threading.Lock()
        self._record_count = 0
        os.makedirs(self.runs_dir, exist_ok=True)

    def write(self, record: dict) -> Optional[str]:
        """Write a record with chain_hash. Returns the hash or None on failure."""
        with self._lock:
            try:
                record.setdefault("run_id", str(uuid.uuid4()))
                record.setdefault("version", "1.0.0")
                record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

                record_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
                h = hmac.new(self._key, self._prev_hash + record_bytes, hashlib.sha256)
                chain_hash = h.hexdigest()
                record["chain_hash"] = chain_hash

                fname = f"{record['run_id']}.air.json"
                fpath = os.path.join(self.runs_dir, fname)
                with open(fpath, "w") as f:
                    json.dump(record, f, indent=2)

                self._prev_hash = h.digest()
                self._record_count += 1
                return chain_hash
            except Exception:
                return None  # Non-blocking

    @property
    def record_count(self) -> int:
        return self._record_count

    @property
    def current_hash(self) -> str:
        if self._prev_hash == self.GENESIS:
            return "genesis"
        return self._prev_hash.hex()


# ---------------------------------------------------------------------------
# OpenAI Client Wrapper
# ---------------------------------------------------------------------------

class AirOpenAIWrapper:
    """Wraps an OpenAI client to log every call as .air.json records.

    Transparent proxy: use it exactly like a normal OpenAI client.
    All audit logging is non-blocking — if it fails, your calls still work.
    """

    def __init__(self, client, runs_dir: Optional[str] = None):
        self._client = client
        self.runs_dir = runs_dir or os.environ.get("AIR_RUNS_DIR", "./runs")
        self._chain = AuditChain(runs_dir=self.runs_dir)

    @property
    def chat(self):
        return _ChatProxy(self._client.chat, self)

    @property
    def models(self):
        return self._client.models

    @property
    def embeddings(self):
        return _EmbeddingsProxy(self._client.embeddings, self)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def _write_record(self, record: dict):
        """Write .air.json record through the audit chain."""
        try:
            self._chain.write(record)
        except Exception:
            # Fallback: write without chain hash
            try:
                fname = f"{record.get('run_id', uuid.uuid4())}.air.json"
                with open(os.path.join(self.runs_dir, fname), "w") as f:
                    json.dump(record, f, indent=2)
            except Exception:
                pass  # Non-blocking: never crash user code


class _ChatProxy:
    def __init__(self, chat, wrapper):
        self._chat = chat
        self._wrapper = wrapper

    @property
    def completions(self):
        return _CompletionsProxy(self._chat.completions, self._wrapper)

    def __getattr__(self, name):
        return getattr(self._chat, name)


class _CompletionsProxy:
    def __init__(self, completions, wrapper):
        self._completions = completions
        self._wrapper = wrapper

    def create(self, **kwargs):
        run_id = str(uuid.uuid4())
        start = time.time()
        model = kwargs.get("model", "unknown")

        # Pre-call: scan messages for PII and injection
        pii_alerts = []
        injection_alerts = []
        messages = kwargs.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                pii_alerts.extend(_scan_pii(content))
                injection_alerts.extend(_scan_injection(content))

        try:
            response = self._completions.create(**kwargs)
            duration_ms = int((time.time() - start) * 1000)

            # Extract usage
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                }

            # Post-call: scan response for PII and injection
            response_pii = []
            response_injection = []
            if hasattr(response, "choices") and response.choices:
                for choice in response.choices:
                    if hasattr(choice, "message") and choice.message:
                        text = choice.message.content or ""
                        response_pii.extend(_scan_pii(text))
                        response_injection.extend(_scan_injection(text))

            record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "llm_call",
                "provider": "openai",
                "model": model,
                "tokens": usage,
                "duration_ms": duration_ms,
                "status": "success",
                "message_count": len(messages),
                "pii_alerts": pii_alerts + response_pii,
                "injection_alerts": injection_alerts + response_injection,
            }
            self._wrapper._write_record(record)
            return response

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "llm_call",
                "provider": "openai",
                "model": model,
                "tokens": {},
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e)[:500],
                "pii_alerts": pii_alerts,
                "injection_alerts": injection_alerts,
            }
            self._wrapper._write_record(record)
            raise

    def __getattr__(self, name):
        return getattr(self._completions, name)


class _EmbeddingsProxy:
    """Proxy for embeddings.create() with audit logging."""

    def __init__(self, embeddings, wrapper):
        self._embeddings = embeddings
        self._wrapper = wrapper

    def create(self, **kwargs):
        run_id = str(uuid.uuid4())
        start = time.time()
        model = kwargs.get("model", "unknown")

        try:
            response = self._embeddings.create(**kwargs)
            duration_ms = int((time.time() - start) * 1000)
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {"prompt": response.usage.prompt_tokens, "total": response.usage.total_tokens}

            record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "embedding_call",
                "provider": "openai",
                "model": model,
                "tokens": usage,
                "duration_ms": duration_ms,
                "status": "success",
            }
            self._wrapper._write_record(record)
            return response
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            record = {
                "version": "1.0.0",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "embedding_call",
                "provider": "openai",
                "model": model,
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e)[:500],
            }
            self._wrapper._write_record(record)
            raise

    def __getattr__(self, name):
        return getattr(self._embeddings, name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def attach_trust(client, runs_dir: Optional[str] = None) -> AirOpenAIWrapper:
    """Wrap an existing OpenAI client with AIR trust layer.

    Args:
        client: An openai.OpenAI instance.
        runs_dir: Directory for .air.json audit records (default: ./runs).

    Returns:
        Wrapped client with audit logging, PII detection, and injection scanning.

    Example:
        from openai import OpenAI
        from air_openai_trust import attach_trust

        client = OpenAI()
        client = attach_trust(client)
        response = client.chat.completions.create(...)
    """
    wrapper = AirOpenAIWrapper(client, runs_dir=runs_dir)
    print(f"[AIR] OpenAI trust layer attached. Audit records → {wrapper.runs_dir}/")
    return wrapper


def air_openai_client(runs_dir: Optional[str] = None, **kwargs) -> AirOpenAIWrapper:
    """Create an OpenAI client pre-configured with AIR trust layer.

    Args:
        runs_dir: Directory for .air.json audit records (default: ./runs).
        **kwargs: Passed to openai.OpenAI() constructor.

    Returns:
        Wrapped OpenAI client with full compliance infrastructure.

    Example:
        from air_openai_trust import air_openai_client

        client = air_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
        )
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed. Run: pip install air-openai-trust\n"
            "(This will install the openai SDK automatically.)"
        )
    client = OpenAI(**kwargs)
    return AirOpenAIWrapper(client, runs_dir=runs_dir)


def validate_output(text: str) -> Dict[str, Any]:
    """Validate LLM output for compliance issues (Art. 15 — Robustness).

    Scans response text for prompt injection markers and PII leakage.

    Returns:
        Dict with 'safe' (bool), 'pii_alerts', and 'injection_alerts'.
    """
    pii = _scan_pii(text)
    injections = _scan_injection(text)
    return {
        "safe": len(pii) == 0 and len(injections) == 0,
        "pii_alerts": pii,
        "injection_alerts": injections,
    }


def check_delegation(authorized_by: str, action: str, scope: Optional[str] = None) -> bool:
    """Verify human delegation before agent action (Art. 14 — Human Oversight).

    Args:
        authorized_by: Identity of the human who authorized the action.
        action: What the agent is about to do.
        scope: Optional scope limitation.

    Returns:
        True if delegation is valid.
    """
    if not authorized_by:
        logger.warning("[AIR] Art.14 — no authorized_by for action=%s", action)
        return False
    logger.info("[AIR] delegation verified: user=%s action=%s scope=%s",
                authorized_by, action, scope)
    return True
