"""
AIR Blackbox Trust Layer for OpenAI SDK.

Wraps the OpenAI client to log every call as .air.json records.

Usage:
    from air_blackbox.trust.openai_agents import air_openai_client
    client = air_openai_client()
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[...])

Or via AirTrust:
    from air_blackbox import AirTrust
    trust = AirTrust()
    trust.attach(openai_client)  # Auto-detects OpenAI
"""

import json
import os
import time
import uuid
import re
from datetime import datetime
from typing import Optional


class AirOpenAIWrapper:
    """Wraps an OpenAI client to log calls as .air.json records.

    Non-blocking: if logging fails, the API call still succeeds.
    """

    def __init__(self, client, gateway_url="http://localhost:8080", runs_dir=None):
        self._client = client
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        os.makedirs(self.runs_dir, exist_ok=True)
        # Redirect to gateway if running
        if hasattr(client, "base_url") and gateway_url != "none":
            client.base_url = f"{gateway_url}/v1"

    @property
    def chat(self):
        return _ChatProxy(self._client.chat, self)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def _write_record(self, record: dict):
        try:
            fname = f"{record['run_id']}.air.json"
            with open(os.path.join(self.runs_dir, fname), "w") as f:
                json.dump(record, f, indent=2)
        except Exception:
            pass  # Non-blocking


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
        try:
            response = self._completions.create(**kwargs)
            duration_ms = int((time.time() - start) * 1000)
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {"prompt": response.usage.prompt_tokens,
                         "completion": response.usage.completion_tokens,
                         "total": response.usage.total_tokens}
            record = {
                "version": "1.0.0", "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model": model, "provider": "openai", "type": "llm_call",
                "tokens": usage, "duration_ms": duration_ms, "status": "success",
            }
            self._wrapper._write_record(record)
            return response
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            record = {
                "version": "1.0.0", "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "model": model, "provider": "openai", "type": "llm_call",
                "tokens": {}, "duration_ms": duration_ms,
                "status": "error", "error": str(e)[:500],
            }
            self._wrapper._write_record(record)
            raise

    def __getattr__(self, name):
        return getattr(self._completions, name)


def attach_trust(client, gateway_url="http://localhost:8080"):
    """Wrap an OpenAI client with AIR trust layer."""
    wrapper = AirOpenAIWrapper(client, gateway_url=gateway_url)
    print(f"[AIR] OpenAI trust layer attached. Events → {wrapper.runs_dir}")
    return wrapper


def air_openai_client(gateway_url="http://localhost:8080", **kwargs):
    """Create an OpenAI client pre-configured with AIR trust layer."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed. Run: pip install air-blackbox[openai]")
    client = OpenAI(**kwargs)
    return AirOpenAIWrapper(client, gateway_url=gateway_url)
