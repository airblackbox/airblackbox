"""
AIR Blackbox Trust Layer skeleton for Pydantic AI.

This is intentionally small for the issue #24 design checkpoint:
capture_run_messages() is useful for message and failure capture, but it
cannot provide transparent attachment by itself. The wrapper below provides
transparent AirTrust().attach(agent) behavior by intercepting public run
methods and delegating all other attributes. OpenTelemetry instrumentation
remains the likely full-adapter mechanism for model/tool lifecycle details.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from air_blackbox.gate.runtime import RuntimeConfig, RuntimeMonitor
from air_blackbox.trust.chain import AuditChain


class AirPydanticAITrust:
    """Trust adapter facade for Pydantic AI Agents."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8080",
        runs_dir: Optional[str] = None,
        detect_pii: bool = True,
        detect_injection: bool = True,
    ):
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection

    def wrap(self, agent) -> "AirPydanticAIAgentWrapper":
        return AirPydanticAIAgentWrapper(
            agent,
            gateway_url=self.gateway_url,
            runs_dir=self.runs_dir,
            detect_pii=self.detect_pii,
            detect_injection=self.detect_injection,
        )


class AirPydanticAIAgentWrapper:
    """Transparent wrapper around a Pydantic AI Agent.

    The skeleton only wraps run_sync() and async run(). All run-specific state
    is kept local to each invocation so concurrent runs cannot share records.
    """

    def __init__(
        self,
        agent,
        gateway_url: str = "http://localhost:8080",
        runs_dir: Optional[str] = None,
        detect_pii: bool = True,
        detect_injection: bool = True,
    ):
        self._agent = agent
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir or os.environ.get("RUNS_DIR", "./runs")
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._chain = AuditChain(runs_dir=self.runs_dir)
        os.makedirs(self.runs_dir, exist_ok=True)

    def run_sync(self, *args, **kwargs):
        """Run the wrapped agent synchronously and write one skeleton event."""
        from pydantic_ai import capture_run_messages

        started = time.time()
        with capture_run_messages() as messages:
            try:
                result = self._agent.run_sync(*args, **kwargs)
            except Exception as exc:
                self._record_run(
                    status="error",
                    args=args,
                    kwargs=kwargs,
                    messages=messages,
                    started=started,
                    error=exc,
                )
                raise

        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            result=result,
        )
        return result

    async def run(self, *args, **kwargs):
        """Run the wrapped agent asynchronously and write one skeleton event."""
        from pydantic_ai import capture_run_messages

        started = time.time()
        with capture_run_messages() as messages:
            try:
                result = await self._agent.run(*args, **kwargs)
            except Exception as exc:
                self._record_run(
                    status="error",
                    args=args,
                    kwargs=kwargs,
                    messages=messages,
                    started=started,
                    error=exc,
                )
                raise

        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            result=result,
        )
        return result

    def _record_run(
        self,
        *,
        status: str,
        args: tuple,
        kwargs: dict,
        messages: list,
        started: float,
        result: Any = None,
        error: Optional[Exception] = None,
    ) -> None:
        record = self._build_record(
            status=status,
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            result=result,
            error=error,
        )
        self._chain.write(record)

    def _build_record(
        self,
        *,
        status: str,
        args: tuple,
        kwargs: dict,
        messages: list,
        started: float,
        result: Any = None,
        error: Optional[Exception] = None,
    ) -> dict:
        user_input = _extract_user_input(args, kwargs)
        output = _result_output(result)
        usage = _result_usage(result)
        run_id = _result_run_id(result) or uuid.uuid4().hex[:16]

        self._check_input(user_input)

        record = {
            "version": "1.0.0",
            "run_id": run_id,
            "timestamp": _utc_timestamp(),
            "type": "pydantic_ai_run",
            "framework": "pydantic_ai",
            "status": status,
            "duration_ms": int((time.time() - started) * 1000),
            "input": _safe_serialize(user_input),
            "messages": _serialize_messages(messages),
        }

        if result is not None:
            record["output"] = _safe_serialize(output)
            record["output_type"] = _type_name(output)
            if usage is not None:
                record["usage"] = _safe_serialize(usage)

        if error is not None:
            record["error"] = {
                "type": type(error).__name__,
                "message": str(error)[:500],
            }

        schema = _output_schema(self._agent, result)
        if schema is not None:
            record["output_schema"] = _safe_serialize(schema)

        return record

    def _check_input(self, user_input: Any) -> None:
        if not (self.detect_pii or self.detect_injection):
            return

        config = RuntimeConfig(
            detect_pii=self.detect_pii,
            detect_injection=self.detect_injection,
            detect_boundary=False,
            detect_token_runaway=False,
            detect_prompt_loop=False,
            detect_error_spiral=False,
        )
        monitor = RuntimeMonitor(config=config, runs_dir=self.runs_dir)
        monitor.check(text=_text_for_monitor(user_input))

    def __getattr__(self, name):
        """Proxy all other attributes to the underlying agent."""
        return getattr(self._agent, name)


def attach_trust(
    agent,
    gateway_url="http://localhost:8080",
    runs_dir=None,
    detect_pii=True,
    detect_injection=True,
):
    """Attach AIR trust layer to a Pydantic AI Agent."""
    trust = AirPydanticAITrust(
        gateway_url=gateway_url,
        runs_dir=runs_dir,
        detect_pii=detect_pii,
        detect_injection=detect_injection,
    )
    wrapper = trust.wrap(agent)
    print(f"[AIR] Pydantic AI trust layer attached. Events -> {wrapper.runs_dir}")
    return wrapper


def _extract_user_input(args: tuple, kwargs: dict) -> Any:
    if args:
        return args[0]
    if "user_prompt" in kwargs:
        return kwargs["user_prompt"]
    return None


def _result_output(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "output", result)


def _result_run_id(result: Any) -> Optional[str]:
    if result is None:
        return None
    run_id = getattr(result, "run_id", None)
    return str(run_id) if run_id else None


def _result_usage(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "usage", None)


def _output_schema(agent: Any, result: Any) -> Any:
    output = _result_output(result)
    output_type = type(output)
    if output is None or output_type in (str, int, float, bool, bytes):
        return None
    if hasattr(agent, "output_json_schema"):
        try:
            return agent.output_json_schema()
        except Exception:
            return None
    if hasattr(output_type, "model_json_schema"):
        try:
            return output_type.model_json_schema()
        except Exception:
            return None
    return None


def _serialize_messages(messages: Any) -> Any:
    if _has_generic_message_values(messages):
        return _safe_serialize(messages)

    try:
        from pydantic_ai.messages import ModelMessagesTypeAdapter

        dumped = ModelMessagesTypeAdapter.dump_json(messages)
        return json.loads(dumped.decode("utf-8"))
    except Exception:
        return _safe_serialize(messages)


def _has_generic_message_values(messages: Any) -> bool:
    if isinstance(messages, dict):
        return True
    if isinstance(messages, (list, tuple)):
        return any(isinstance(message, dict) for message in messages)
    return False


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_serialize(value: Any, *, depth: int = 0) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if depth >= 4:
        return _bounded_repr(value)
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if isinstance(value, dict):
        return {
            str(k): _safe_serialize(v, depth=depth + 1)
            for k, v in value.items()
            if _safe_key(k)
        }
    if isinstance(value, (list, tuple, set)):
        return [_safe_serialize(v, depth=depth + 1) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _safe_serialize(value.model_dump(mode="json"), depth=depth + 1)
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return _safe_serialize(value.dict(), depth=depth + 1)
        except Exception:
            pass
    return {
        "type": _type_name(value),
        "repr": _bounded_repr(value),
    }


def _safe_key(key: Any) -> bool:
    key_text = str(key).lower()
    return not any(
        blocked in key_text
        for blocked in (
            "api_key",
            "authorization",
            "access_token",
            "id_token",
            "password",
            "secret",
        )
    )


def _bounded_repr(value: Any) -> str:
    return str(value)[:500]


def _type_name(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__name__}"


def _text_for_monitor(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(_safe_serialize(value), sort_keys=True)
    except Exception:
        return _bounded_repr(value)
