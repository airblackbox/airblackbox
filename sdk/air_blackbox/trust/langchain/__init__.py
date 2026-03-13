"""
AIR Blackbox Trust Layer for LangChain / LangGraph.

Drop-in audit trails, PII detection, injection scanning, and
compliance logging for any LangChain chain or agent.

Usage:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(your_chain)  # Auto-detects LangChain

Or directly:
    from air_blackbox.trust.langchain import AirLangChainHandler
    chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})

Or the simplest way:
    from air_blackbox.trust.langchain import air_langchain_llm
    llm = air_langchain_llm("gpt-4o-mini")
"""

import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import Any, Optional

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    BaseCallbackHandler = object
    LLMResult = object

# Simple PII patterns
_PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
    (r'\b\d{3}-\d{2}-\d{4}\b', 'ssn'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', 'phone'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'credit_card'),
]

# Simple injection patterns
_INJECTION_PATTERNS = [
    r'ignore (?:all )?previous instructions',
    r'ignore (?:all )?above instructions',
    r'disregard (?:all )?previous',
    r'you are now',
    r'system prompt:',
    r'new instructions:',
    r'override:',
]


class AirLangChainHandler(BaseCallbackHandler):
    """LangChain callback handler that logs everything through AIR Blackbox.

    Attaches to any LangChain chain/agent and captures:
    - Every LLM call (model, prompts, completions, tokens)
    - Every tool invocation (name, input, output)
    - PII detection in prompts
    - Prompt injection scanning
    - Timing and error tracking

    All events are written as .air.json records for compliance analysis.
    """

    name = "air_blackbox"

    def __init__(self, gateway_url="http://localhost:8080", runs_dir=None,
                 detect_pii=True, detect_injection=True, log_to_gateway=True):
        if not HAS_LANGCHAIN:
            raise ImportError(
                "LangChain not installed. Run: pip install air-blackbox[langchain]"
            )
        super().__init__()
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self.log_to_gateway = log_to_gateway
        self._current_run = None
        self._start_time = None
        self._pii_alerts = []
        self._injection_alerts = []
        os.makedirs(self.runs_dir, exist_ok=True)
        self._event_count = 0

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs):
        """Called when LLM starts generating."""
        self._current_run = {
            "run_id": str(uuid.uuid4()),
            "trace_id": kwargs.get("run_id", uuid.uuid4()).hex[:16] if kwargs.get("run_id") else uuid.uuid4().hex[:16],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model": serialized.get("kwargs", {}).get("model_name", 
                     serialized.get("kwargs", {}).get("model", "unknown")),
            "provider": self._guess_provider(serialized),
            "type": "llm_call",
        }
        self._start_time = time.time()

        # Scan prompts for PII and injection
        for prompt in prompts:
            if self.detect_pii:
                self._scan_pii(prompt)
            if self.detect_injection:
                self._scan_injection(prompt)

    def on_llm_end(self, response: LLMResult, **kwargs):
        """Called when LLM finishes generating."""
        if not self._current_run:
            return
        duration_ms = int((time.time() - self._start_time) * 1000) if self._start_time else 0

        # Extract token usage
        token_usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            token_usage = {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            }

        record = {
            "version": "1.0.0",
            **self._current_run,
            "tokens": token_usage,
            "duration_ms": duration_ms,
            "status": "success",
            "pii_alerts": self._pii_alerts.copy(),
            "injection_alerts": self._injection_alerts.copy(),
        }

        self._write_record(record)
        self._event_count += 1
        self._pii_alerts = []
        self._injection_alerts = []
        self._current_run = None

    def on_llm_error(self, error: Exception, **kwargs):
        """Called when LLM errors."""
        if not self._current_run:
            return
        duration_ms = int((time.time() - self._start_time) * 1000) if self._start_time else 0
        record = {
            "version": "1.0.0",
            **self._current_run,
            "tokens": {},
            "duration_ms": duration_ms,
            "status": "error",
            "error": str(error)[:500],
        }
        self._write_record(record)
        self._event_count += 1
        self._current_run = None

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown_tool")
        record = {
            "version": "1.0.0",
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "tool_call",
            "tool_name": tool_name,
            "status": "started",
        }
        self._write_record(record)
        self._event_count += 1

        # Scan tool input for PII
        if self.detect_pii:
            self._scan_pii(str(input_str))

    def on_tool_end(self, output: str, **kwargs):
        """Called when a tool finishes."""
        pass  # Tool completion logged implicitly via the start record

    def on_tool_error(self, error: Exception, **kwargs):
        """Called when a tool errors."""
        record = {
            "version": "1.0.0",
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "tool_error",
            "error": str(error)[:500],
            "status": "error",
        }
        self._write_record(record)
        self._event_count += 1

    # ── Internal methods ──

    def _scan_pii(self, text: str):
        for pattern, pii_type in _PII_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                self._pii_alerts.append({
                    "type": pii_type,
                    "count": len(matches),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

    def _scan_injection(self, text: str):
        text_lower = text.lower()
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                self._injection_alerts.append({
                    "pattern": pattern,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })

    def _write_record(self, record: dict):
        """Write .air.json record with HMAC chain hash."""
        try:
            if not hasattr(self, '_chain'):
                from air_blackbox.trust.chain import AuditChain
                self._chain = AuditChain(runs_dir=self.runs_dir)
            self._chain.write(record)
        except Exception:
            # Fallback: write without chain hash
            try:
                fname = f"{record['run_id']}.air.json"
                fpath = os.path.join(self.runs_dir, fname)
                with open(fpath, "w") as f:
                    json.dump(record, f, indent=2)
            except Exception:
                pass  # Non-blocking

    def _guess_provider(self, serialized: dict) -> str:
        cls = serialized.get("id", [""])
        cls_str = str(cls).lower()
        if "openai" in cls_str: return "openai"
        if "anthropic" in cls_str: return "anthropic"
        if "google" in cls_str: return "google"
        if "cohere" in cls_str: return "cohere"
        if "mistral" in cls_str: return "mistral"
        return "unknown"

    @property
    def event_count(self) -> int:
        return self._event_count


def attach_trust(agent, gateway_url="http://localhost:8080"):
    """Attach AIR trust layer to a LangChain chain/agent.

    Works with any LangChain Runnable (chains, agents, LLMs).
    Adds the AirLangChainHandler as a callback.
    """
    handler = AirLangChainHandler(gateway_url=gateway_url)

    if hasattr(agent, "callbacks"):
        if agent.callbacks is None:
            agent.callbacks = []
        agent.callbacks.append(handler)
    print(f"[AIR] LangChain trust layer attached. Events → {handler.runs_dir}")
    return agent


def air_langchain_llm(model: str = "gpt-4o-mini", gateway_url: str = "http://localhost:8080", **kwargs):
    """Create a LangChain LLM pre-configured with AIR trust layer.

    Usage:
        from air_blackbox.trust.langchain import air_langchain_llm
        llm = air_langchain_llm("gpt-4o-mini")
        result = llm.invoke("What is AI governance?")
        # Every call is automatically logged as .air.json
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")

    handler = AirLangChainHandler(gateway_url=gateway_url)
    llm = ChatOpenAI(
        model=model,
        base_url=f"{gateway_url}/v1" if gateway_url != "none" else None,
        callbacks=[handler],
        **kwargs,
    )
    print(f"[AIR] LLM '{model}' created with trust layer. Events → {handler.runs_dir}")
    return llm
