"""
AIR Blackbox Trust Layer skeleton for Pydantic AI.

This is intentionally small for the issue #24 design checkpoint:
capture_run_messages() is useful for message and failure capture, but it
cannot provide transparent attachment by itself. The wrapper below provides
transparent AirTrust().attach(agent) behavior by intercepting public run
methods and delegating all other attributes. OpenTelemetry instrumentation
remains the likely full-adapter mechanism for model/tool lifecycle details.
"""

import dataclasses
import json
import logging
import os
import time
import uuid
import weakref
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

from air_blackbox.gate.runtime import RuntimeConfig, RuntimeMonitor
from air_blackbox.trust.chain import AuditChain

logger = logging.getLogger(__name__)

_current_run_state: ContextVar[Optional["_InvocationState"]] = ContextVar(
    "air_pydantic_ai_invocation_state", default=None
)
_processors_by_provider: "weakref.WeakKeyDictionary[Any, Any]" = (
    weakref.WeakKeyDictionary()
)
_isolated_provider: Any = None
_MAX_STRING = 1000
_MAX_ITEMS = 25
_MAX_DEPTH = 5


class _InvocationState:
    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.spans: list[dict] = []
        self.events: list[dict] = []
        self.streaming = False
        self.stream_completed = False
        self.started = time.time()

    def add_span(self, span: Any) -> None:
        try:
            context = span.get_span_context()
        except Exception:
            context = None

        attrs = _safe_attributes(getattr(span, "attributes", {}) or {})
        record = {
            "name": getattr(span, "name", ""),
            "kind": str(getattr(span, "kind", "")),
            "status": _span_status(span),
            "trace_id": _format_trace_id(getattr(context, "trace_id", None)),
            "span_id": _format_span_id(getattr(context, "span_id", None)),
            "parent_span_id": _format_span_id(
                getattr(getattr(span, "parent", None), "span_id", None)
            ),
            "start_time_unix_nano": getattr(span, "start_time", None),
            "end_time_unix_nano": getattr(span, "end_time", None),
            "duration_ms": _span_duration_ms(span),
            "attributes": attrs,
            "events": _safe_serialize(_span_events(span)),
        }
        self.spans.append(record)


def _span_status(span: Any) -> str:
    status = getattr(span, "status", None)
    code = getattr(status, "status_code", status)
    return str(code) if code is not None else "unknown"


def _span_duration_ms(span: Any) -> Optional[float]:
    start = getattr(span, "start_time", None)
    end = getattr(span, "end_time", None)
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return round((end - start) / 1_000_000, 3)
    return None


def _span_events(span: Any) -> list[dict]:
    events = []
    for event in list(getattr(span, "events", ()) or ())[:_MAX_ITEMS]:
        events.append(
            {
                "name": getattr(event, "name", ""),
                "timestamp_unix_nano": getattr(event, "timestamp", None),
                "attributes": _safe_attributes(getattr(event, "attributes", {}) or {}),
            }
        )
    return events


def _format_trace_id(trace_id: Any) -> Optional[str]:
    if isinstance(trace_id, int) and trace_id:
        return f"{trace_id:032x}"
    return None


def _format_span_id(span_id: Any) -> Optional[str]:
    if isinstance(span_id, int) and span_id:
        return f"{span_id:016x}"
    return None


def _safe_attributes(attributes: Any) -> dict:
    if not isinstance(attributes, dict):
        return {}
    return {
        str(key): _safe_serialize(value)
        for key, value in list(attributes.items())[:_MAX_ITEMS]
        if _safe_key(key)
    }


def _get_or_create_air_processor(provider: Any) -> Optional[Any]:
    if provider is None or not hasattr(provider, "add_span_processor"):
        return None
    try:
        processor = _processors_by_provider.get(provider)
    except TypeError:
        processor = getattr(provider, "_air_blackbox_pydantic_ai_processor", None)
    if processor is not None:
        return processor

    processor = _make_air_span_processor()
    if processor is None:
        return None
    provider.add_span_processor(processor)
    try:
        _processors_by_provider[provider] = processor
    except TypeError:
        setattr(provider, "_air_blackbox_pydantic_ai_processor", processor)
    return processor


def _make_air_span_processor() -> Optional[Any]:
    try:
        from opentelemetry.sdk.trace.export import SpanProcessor
    except ImportError:
        return None

    class AirPydanticAISpanProcessor(SpanProcessor):
        """Collects Pydantic AI OTel spans into the active wrapper invocation."""

        is_air_blackbox_pydantic_ai = True

        def on_start(self, span, parent_context=None):  # noqa: D401
            return None

        def on_end(self, span):
            state = _current_run_state.get()
            if state is not None:
                state.add_span(span)

        def shutdown(self):
            return None

        def force_flush(self, timeout_millis: int = 30000) -> bool:
            return True

    return AirPydanticAISpanProcessor()


def _resolve_otel_instrumentation(agent: Any) -> Optional[dict]:
    """Attach AIR to a mutable provider or pass an isolated provider to Pydantic AI.

    Pydantic AI's public API accepts an InstrumentationSettings object on
    agent.instrument. When the process-global provider is mutable, AIR only adds
    its SpanProcessor and preserves that provider. When the global provider is
    only a proxy/no-op and cannot accept processors, AIR creates a private SDK
    TracerProvider and passes it through InstrumentationSettings; it never calls
    opentelemetry.trace.set_tracer_provider().
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from pydantic_ai import InstrumentationSettings
    except ImportError:
        return None

    global _isolated_provider

    global_provider = trace.get_tracer_provider()
    provider = global_provider
    isolated = False
    if not hasattr(provider, "add_span_processor"):
        if _isolated_provider is None:
            _isolated_provider = TracerProvider()
        provider = _isolated_provider
        isolated = True

    processor = _get_or_create_air_processor(provider)
    if processor is None:
        return None

    previous = getattr(agent, "instrument", None)
    if previous is None or previous is False or previous is True or isolated:
        agent.instrument = InstrumentationSettings(
            tracer_provider=provider,
            include_content=True,
            include_model_request_parameters=False,
        )

    return {
        "provider": provider,
        "processor": processor,
        "isolated": isolated,
        "global_provider_id": id(global_provider),
    }


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
        self.runs_dir: str = runs_dir or os.environ.get("RUNS_DIR") or "./runs"
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
        self.runs_dir: str = runs_dir or os.environ.get("RUNS_DIR") or "./runs"
        self.detect_pii = detect_pii
        self.detect_injection = detect_injection
        self._chain = AuditChain(runs_dir=self.runs_dir, resume=True)
        os.makedirs(self.runs_dir, exist_ok=True)
        self._otel = _resolve_otel_instrumentation(self._agent)

    def run_sync(self, *args, **kwargs):
        """Run the wrapped agent synchronously and write one skeleton event."""
        from pydantic_ai import capture_run_messages

        started = time.time()
        state = _InvocationState(correlation_id=uuid.uuid4().hex)
        token = _current_run_state.set(state)
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
                    state=state,
                    error=exc,
                )
                _current_run_state.reset(token)
                raise

        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            state=state,
            result=result,
        )
        _current_run_state.reset(token)
        return result

    async def run(self, *args, **kwargs):
        """Run the wrapped agent asynchronously and write one skeleton event."""
        from pydantic_ai import capture_run_messages

        started = time.time()
        state = _InvocationState(correlation_id=uuid.uuid4().hex)
        token = _current_run_state.set(state)
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
                    state=state,
                    error=exc,
                )
                _current_run_state.reset(token)
                raise

        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            state=state,
            result=result,
        )
        _current_run_state.reset(token)
        return result

    def run_stream(self, *args, **kwargs):
        """Run the wrapped agent using Pydantic AI's async stream API."""
        if not hasattr(self._agent, "run_stream"):
            raise AttributeError("run_stream")
        return self._run_stream_context(*args, **kwargs)

    @asynccontextmanager
    async def _run_stream_context(self, *args, **kwargs):
        from pydantic_ai import capture_run_messages

        started = time.time()
        state = _InvocationState(correlation_id=uuid.uuid4().hex)
        state.streaming = True
        token = _current_run_state.set(state)
        result = None
        with capture_run_messages() as messages:
            try:
                async with self._agent.run_stream(*args, **kwargs) as stream_result:
                    result = stream_result
                    yield stream_result
                    state.stream_completed = True
            except Exception as exc:
                self._record_run(
                    status="error",
                    args=args,
                    kwargs=kwargs,
                    messages=messages,
                    started=started,
                    state=state,
                    result=result if state.stream_completed else None,
                    error=exc,
                )
                _current_run_state.reset(token)
                raise

        output_result = await _final_stream_result(result, is_async=True)
        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            state=state,
            result=output_result or result,
            stream_result=result,
        )
        _current_run_state.reset(token)

    def run_stream_sync(self, *args, **kwargs):
        """Run the wrapped agent using Pydantic AI's sync stream API."""
        if not hasattr(self._agent, "run_stream_sync"):
            raise AttributeError("run_stream_sync")
        return self._run_stream_sync_context(*args, **kwargs)

    @contextmanager
    def _run_stream_sync_context(self, *args, **kwargs):
        from pydantic_ai import capture_run_messages

        started = time.time()
        state = _InvocationState(correlation_id=uuid.uuid4().hex)
        state.streaming = True
        token = _current_run_state.set(state)
        result = None
        with capture_run_messages() as messages:
            try:
                with self._agent.run_stream_sync(*args, **kwargs) as stream_result:
                    result = stream_result
                    yield stream_result
                    state.stream_completed = True
            except Exception as exc:
                self._record_run(
                    status="error",
                    args=args,
                    kwargs=kwargs,
                    messages=messages,
                    started=started,
                    state=state,
                    result=result if state.stream_completed else None,
                    error=exc,
                )
                _current_run_state.reset(token)
                raise

        output_result = _final_stream_result_sync(result)
        self._record_run(
            status="success",
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            state=state,
            result=output_result or result,
            stream_result=result,
        )
        _current_run_state.reset(token)

    def _record_run(
        self,
        *,
        status: str,
        args: tuple,
        kwargs: dict,
        messages: list,
        started: float,
        state: _InvocationState,
        result: Any = None,
        stream_result: Any = None,
        error: Optional[Exception] = None,
    ) -> None:
        record = self._build_record(
            status=status,
            args=args,
            kwargs=kwargs,
            messages=messages,
            started=started,
            state=state,
            result=result,
            stream_result=stream_result,
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
        state: _InvocationState,
        result: Any = None,
        stream_result: Any = None,
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
            "correlation_id": state.correlation_id,
        }

        if result is not None:
            record["output"] = _safe_serialize(output)
            record["output_type"] = _type_name(output)
            if usage is not None:
                record["usage"] = _safe_serialize(usage)

        metadata = _build_otel_metadata(state)
        if metadata:
            record["otel"] = metadata
            span_usage = metadata.get("usage")
            if span_usage and "usage" not in record:
                record["usage"] = span_usage

        if state.streaming:
            record["streaming"] = {
                "enabled": True,
                "completed": state.stream_completed and error is None,
                "interrupted": error is not None,
            }

        if error is not None:
            record["error"] = {
                "type": type(error).__name__,
                "message": str(error)[:500],
            }

        schema = _output_schema(self._agent, result)
        if schema is not None:
            record["output_validation"] = {
                "expected_type": _expected_output_type(self._agent, result),
                "json_schema": _safe_serialize(schema),
                "pydantic_ai_validation_succeeded": (
                    result is not None and error is None and not state.streaming
                )
                or (
                    stream_result is not None
                    and state.stream_completed
                    and error is None
                ),
                "validation_retry_count": _validation_retry_count(result),
                "final_validated_output": _safe_serialize(_result_output(result)),
                "air_security_checks": {
                    "detect_pii": self.detect_pii,
                    "detect_injection": self.detect_injection,
                },
            }
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
    logger.info("Pydantic AI trust layer attached. Events -> %s", wrapper.runs_dir)
    return wrapper


async def _final_stream_result(result: Any, *, is_async: bool) -> Any:
    if result is None:
        return None
    get_output = getattr(result, "get_output", None)
    if not callable(get_output):
        return result
    output = get_output()
    if is_async and hasattr(output, "__await__"):
        output = await output
    return _StreamFinalResult(
        output=output,
        run_id=_result_run_id(result),
        usage=_result_usage(result),
    )


def _final_stream_result_sync(result: Any) -> Any:
    if result is None:
        return None
    get_output = getattr(result, "get_output", None)
    if not callable(get_output):
        return result
    return _StreamFinalResult(
        output=get_output(),
        run_id=_result_run_id(result),
        usage=_result_usage(result),
    )


@dataclasses.dataclass
class _StreamFinalResult:
    output: Any
    run_id: Optional[str]
    usage: Any


def _build_otel_metadata(state: _InvocationState) -> dict:
    if not state.spans:
        return {}

    trace_ids = sorted({s["trace_id"] for s in state.spans if s.get("trace_id")})
    spans = [_classify_span(span) for span in state.spans]
    usage = _usage_from_spans(spans)
    metadata = {
        "correlation_id": state.correlation_id,
        "trace_ids": trace_ids,
        "span_count": len(spans),
        "spans": spans,
        "model_requests": [s for s in spans if s["category"] == "model_request"],
        "tools": [s for s in spans if s["category"] == "tool"],
        "validations": [s for s in spans if s["category"] == "validation"],
        "errors": [s for s in spans if s["status"].lower().endswith("error")],
    }
    if usage:
        metadata["usage"] = usage
    return metadata


def _classify_span(span: dict) -> dict:
    name = str(span.get("name", "")).lower()
    attrs = span.get("attributes", {})
    category = "agent_run"
    if "tool" in name or any("tool" in key for key in attrs):
        category = "tool"
    if "validation" in name or "validate" in name:
        category = "validation"
    if "request" in name or any(
        key.startswith("gen_ai.request") or key in ("gen_ai.provider.name",)
        for key in attrs
    ):
        category = "model_request"
    if "stream" in name:
        category = "stream"

    return {
        "category": category,
        "name": span.get("name"),
        "status": span.get("status"),
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "duration_ms": span.get("duration_ms"),
        "attributes": attrs,
        "events": span.get("events", []),
    }


def _usage_from_spans(spans: list[dict]) -> dict:
    usage: dict[str, int] = {}
    token_keys = {
        "gen_ai.usage.input_tokens": "input_tokens",
        "gen_ai.usage.output_tokens": "output_tokens",
        "gen_ai.usage.total_tokens": "total_tokens",
        "gen_ai.aggregated_usage.input_tokens": "input_tokens",
        "gen_ai.aggregated_usage.output_tokens": "output_tokens",
        "gen_ai.aggregated_usage.total_tokens": "total_tokens",
    }
    for span in spans:
        attrs = span.get("attributes", {})
        for attr, target in token_keys.items():
            value = attrs.get(attr)
            if isinstance(value, int):
                usage[target] = max(usage.get(target, 0), value)
        if span["category"] == "model_request":
            usage["requests"] = usage.get("requests", 0) + 1
    if "total_tokens" not in usage:
        total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        if total:
            usage["total_tokens"] = total
    return usage


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
    usage = getattr(result, "usage", None)
    if callable(usage):
        try:
            return usage()
        except TypeError:
            return usage
    return usage


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


def _expected_output_type(agent: Any, result: Any) -> Optional[str]:
    output_type = getattr(agent, "output_type", None)
    if output_type is not None:
        return _bounded_repr(output_type)
    output = _result_output(result)
    if output is not None:
        return _type_name(output)
    return None


def _validation_retry_count(result: Any) -> Optional[int]:
    for name in ("validation_retry_count", "output_retries", "output_retries_used"):
        value = getattr(result, name, None)
        if isinstance(value, int):
            return value
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
        if isinstance(value, str):
            return value[:_MAX_STRING]
        return value
    if depth >= _MAX_DEPTH:
        return _bounded_repr(value)
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        try:
            return _safe_serialize(dataclasses.asdict(value), depth=depth + 1)
        except Exception:
            return {"type": _type_name(value), "repr": _bounded_repr(value)}
    if isinstance(value, dict):
        return {
            str(k): _safe_serialize(v, depth=depth + 1)
            for k, v in list(value.items())[:_MAX_ITEMS]
            if _safe_key(k)
        }
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        serialized = [_safe_serialize(v, depth=depth + 1) for v in items[:_MAX_ITEMS]]
        if len(items) > _MAX_ITEMS:
            serialized.append({"truncated": len(items) - _MAX_ITEMS})
        return serialized
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
            "cookie",
            "client",
            "connection",
            "database",
            "tracer",
        )
    )


def _bounded_repr(value: Any) -> str:
    return str(value)[:_MAX_STRING]


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
