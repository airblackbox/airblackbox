import asyncio
import contextlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from contextvars import ContextVar
from unittest.mock import patch

from pydantic import BaseModel


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import yaml  # noqa: F401
except ImportError:
    yaml_stub = types.ModuleType("yaml")
    yaml_stub.safe_load = lambda content: {}
    yaml_stub.dump = lambda data, **kwargs: json.dumps(data)
    sys.modules["yaml"] = yaml_stub

_current_messages = ContextVar("current_pydantic_ai_messages", default=None)


class FakeRunResult:
    def __init__(self, output, run_id="run_1", usage=None):
        self.output = output
        self.run_id = run_id
        self.usage = usage or {"requests": 1}


class FakeStructuredOutput(BaseModel):
    name: str


class FakeAgent:
    __module__ = "pydantic_ai.agent"

    def __init__(self, *, output=None, fail=False, delay=0.0, stream_fail=False):
        self.name = "fake-agent"
        self.output = output
        self.fail = fail
        self.delay = delay
        self.stream_fail = stream_fail
        self.instrument = None

    def run_sync(self, user_prompt, **kwargs):
        with self._span("agent run", {"gen_ai.agent.name": self.name}):
            with self._span(
                "model request",
                {
                    "gen_ai.provider.name": "test",
                    "gen_ai.request.model": "fake-model",
                    "gen_ai.usage.input_tokens": 1,
                    "authorization": "Bearer should-not-persist",
                },
            ):
                messages = _current_messages.get()
                if messages is not None:
                    messages.append({"role": "user", "content": user_prompt})
                if self.fail:
                    raise ValueError("provider failed with safe test error")
            with self._span(
                "tool execute search",
                {
                    "gen_ai.tool.name": "search",
                    "tool.query": user_prompt,
                    "tool.api_key": "hidden",
                },
            ):
                pass
            return FakeRunResult(
                output=self.output
                if self.output is not None
                else f"sync:{user_prompt}",
                run_id=f"sync-{user_prompt}",
                usage={"total_tokens": 3},
            )

    async def run(self, user_prompt, **kwargs):
        with self._span("agent run", {"gen_ai.agent.name": self.name}):
            messages = _current_messages.get()
            if messages is not None:
                messages.append({"role": "user", "content": user_prompt})
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.fail:
                raise ValueError("async provider failed")
            return FakeRunResult(
                output=self.output
                if self.output is not None
                else f"async:{user_prompt}",
                run_id=f"async-{user_prompt}",
                usage={"total_tokens": 4},
            )

    def run_stream(self, user_prompt, **kwargs):
        return FakeAsyncStreamContext(self, user_prompt)

    def run_stream_sync(self, user_prompt, **kwargs):
        return FakeSyncStreamContext(self, user_prompt)

    def output_json_schema(self):
        if isinstance(self.output, BaseModel):
            return type(self.output).model_json_schema()
        return None

    def normal_attribute(self):
        return "delegated"

    @contextlib.contextmanager
    def _span(self, name, attributes=None):
        tracer = getattr(
            getattr(self.instrument, "tracer", None), "start_as_current_span", None
        )
        if tracer is None:
            yield
            return
        with self.instrument.tracer.start_as_current_span(
            name, attributes=attributes or {}
        ):
            yield


class FakeInstrumentationSettings:
    def __init__(
        self,
        *,
        tracer_provider=None,
        include_content=True,
        include_model_request_parameters=True,
        **kwargs,
    ):
        self.tracer_provider = tracer_provider
        self.include_content = include_content
        self.include_model_request_parameters = include_model_request_parameters
        self.tracer = tracer_provider.get_tracer("pydantic-ai-test")


class FakeAsyncStreamContext:
    def __init__(self, agent, user_prompt):
        self.agent = agent
        self.user_prompt = user_prompt
        self.result = FakeStreamResult(f"stream:{user_prompt}", f"stream-{user_prompt}")
        self._span_cm = None

    async def __aenter__(self):
        self._span_cm = self.agent._span("stream model request")
        self._span_cm.__enter__()
        messages = _current_messages.get()
        if messages is not None:
            messages.append({"role": "user", "content": self.user_prompt})
        if self.agent.stream_fail:
            raise RuntimeError("stream failed")
        return self.result

    async def __aexit__(self, exc_type, exc, tb):
        if self._span_cm is not None:
            self._span_cm.__exit__(exc_type, exc, tb)


class FakeSyncStreamContext:
    def __init__(self, agent, user_prompt):
        self.agent = agent
        self.user_prompt = user_prompt
        self.result = FakeSyncStreamResult(
            f"sync-stream:{user_prompt}", f"sync-stream-{user_prompt}"
        )
        self._span_cm = None

    def __enter__(self):
        self._span_cm = self.agent._span("stream sync model request")
        self._span_cm.__enter__()
        messages = _current_messages.get()
        if messages is not None:
            messages.append({"role": "user", "content": self.user_prompt})
        if self.agent.stream_fail:
            raise RuntimeError("sync stream failed")
        return self.result

    def __exit__(self, exc_type, exc, tb):
        if self._span_cm is not None:
            self._span_cm.__exit__(exc_type, exc, tb)


class FakeStreamResult:
    def __init__(self, output, run_id):
        self.output = output
        self.run_id = run_id
        self.usage = {"total_tokens": 5, "requests": 1}

    async def get_output(self):
        return self.output

    def stream_output(self):
        yield self.output


class FakeSyncStreamResult(FakeStreamResult):
    def get_output(self):
        return self.output


@contextlib.contextmanager
def fake_capture_run_messages():
    messages = []
    token = _current_messages.set(messages)
    try:
        yield messages
    finally:
        _current_messages.reset(token)


class PydanticAIFakeModuleMixin:
    def setUp(self):
        self._old_modules = {
            name: sys.modules.get(name) for name in ("pydantic_ai", "pydantic_ai.agent")
        }

        fake_root = types.ModuleType("pydantic_ai")
        fake_root.Agent = FakeAgent
        fake_root.InstrumentationSettings = FakeInstrumentationSettings
        fake_root.capture_run_messages = fake_capture_run_messages

        fake_agent_module = types.ModuleType("pydantic_ai.agent")
        fake_agent_module.Agent = FakeAgent

        sys.modules["pydantic_ai"] = fake_root
        sys.modules["pydantic_ai.agent"] = fake_agent_module

    def tearDown(self):
        for name, module in self._old_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def _read_one_record(runs_dir):
    files = [f for f in os.listdir(runs_dir) if f.endswith(".air.json")]
    assert len(files) == 1
    with open(os.path.join(runs_dir, files[0])) as f:
        return json.load(f)


def _read_records(runs_dir):
    records = []
    for name in os.listdir(runs_dir):
        if name.endswith(".air.json"):
            with open(os.path.join(runs_dir, name)) as f:
                records.append(json.load(f))
    return records


def _verify_chain(runs_dir, expected_records):
    from air_blackbox.replay.engine import ReplayEngine

    engine = ReplayEngine(runs_dir=runs_dir)
    loaded = engine.load()
    verification = engine.verify_chain()

    assert loaded == expected_records
    assert verification.intact
    assert verification.total_records == expected_records
    assert verification.verified_records == expected_records
    assert verification.records_with_hash == expected_records
    return verification


try:
    from opentelemetry.sdk.trace import SpanProcessor
except ImportError:  # pragma: no cover
    SpanProcessor = object


class RecordingSpanProcessor(SpanProcessor):
    def __init__(self):
        self.spans = []

    def on_start(self, span, parent_context=None):
        return None

    def _on_ending(self, span):
        return None

    def on_end(self, span):
        self.spans.append(span)

    def shutdown(self):
        return None

    def force_flush(self, timeout_millis=30000):
        return True


def _air_processor_count(provider):
    active = getattr(provider, "_active_span_processor", None)
    processors = getattr(active, "_span_processors", ())
    return sum(
        1
        for processor in processors
        if getattr(processor, "is_air_blackbox_pydantic_ai", False)
    )


class TestPydanticAITrustSkeleton(PydanticAIFakeModuleMixin, unittest.TestCase):
    def test_air_trust_detects_pydantic_ai_agent(self):
        from air_blackbox import AirTrust

        assert AirTrust()._detect_framework(FakeAgent()) == "pydantic_ai"

    def test_attach_returns_transparent_wrapper(self):
        from air_blackbox import AirTrust
        from air_blackbox.trust.pydantic_ai import AirPydanticAIAgentWrapper

        wrapped = AirTrust(gateway_url="none").attach(FakeAgent())

        assert isinstance(wrapped, AirPydanticAIAgentWrapper)
        assert wrapped.name == "fake-agent"
        assert wrapped.normal_attribute() == "delegated"

    def test_run_sync_returns_result_and_records_success(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(FakeAgent(), gateway_url="none", runs_dir=runs_dir)
            result = wrapped.run_sync("hello")

            assert result.output == "sync:hello"

            record = _read_one_record(runs_dir)
            assert record["type"] == "pydantic_ai_run"
            assert record["framework"] == "pydantic_ai"
            assert record["status"] == "success"
            assert record["input"] == "hello"
            assert record["output"] == "sync:hello"
            assert record["run_id"] == "sync-hello"
            assert record["usage"] == {"total_tokens": 3}
            assert record["messages"] == [{"role": "user", "content": "hello"}]
            assert record["otel"]["span_count"] >= 1

    def test_async_run_returns_result_and_records_success(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        async def scenario():
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                result = await wrapped.run("hello")
                assert result.output == "async:hello"

                record = _read_one_record(runs_dir)
                assert record["status"] == "success"
                assert record["run_id"] == "async-hello"
                assert record["output"] == "async:hello"

        asyncio.run(scenario())

    def test_failed_run_records_error_and_reraises(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(
                FakeAgent(fail=True), gateway_url="none", runs_dir=runs_dir
            )
            with self.assertRaisesRegex(ValueError, "provider failed"):
                wrapped.run_sync("boom")

            record = _read_one_record(runs_dir)
            assert record["status"] == "error"
            assert record["error"]["type"] == "ValueError"
            assert record["messages"] == [{"role": "user", "content": "boom"}]

    def test_structured_output_records_output_type_and_schema(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        output = FakeStructuredOutput(name="Ada")
        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(
                FakeAgent(output=output), gateway_url="none", runs_dir=runs_dir
            )
            result = wrapped.run_sync("structured")

            assert result.output == output

            record = _read_one_record(runs_dir)
            assert record["output"] == {"name": "Ada"}
            assert record["output_type"].endswith(".FakeStructuredOutput")
            assert record["output_schema"]["title"] == "FakeStructuredOutput"

    def test_runtime_monitor_check_is_invoked(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            with patch("air_blackbox.trust.pydantic_ai.RuntimeMonitor") as monitor_cls:
                monitor_cls.return_value.check.return_value = None
                wrapped = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                wrapped.run_sync("Contact john@example.com")

                monitor_cls.return_value.check.assert_called_once_with(
                    text="Contact john@example.com"
                )

    def test_concurrent_async_runs_do_not_mix_records(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        async def scenario():
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped = attach_trust(
                    FakeAgent(delay=0.01), gateway_url="none", runs_dir=runs_dir
                )
                results = await asyncio.gather(
                    wrapped.run("one"),
                    wrapped.run("two"),
                )

                assert [r.output for r in results] == ["async:one", "async:two"]

                records = []
                for name in os.listdir(runs_dir):
                    if name.endswith(".air.json"):
                        with open(os.path.join(runs_dir, name)) as f:
                            records.append(json.load(f))

                by_input = {record["input"]: record for record in records}
                assert set(by_input) == {"one", "two"}
                assert by_input["one"]["run_id"] == "async-one"
                assert by_input["two"]["run_id"] == "async-two"
                assert by_input["one"]["messages"][0]["content"] == "one"
                assert by_input["two"]["messages"][0]["content"] == "two"
                assert (
                    by_input["one"]["correlation_id"]
                    != by_input["two"]["correlation_id"]
                )

        asyncio.run(scenario())

    def test_async_stream_records_once_on_completion(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        async def scenario():
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                async with wrapped.run_stream("hello") as stream:
                    assert await stream.get_output() == "stream:hello"

                record = _read_one_record(runs_dir)
                assert record["status"] == "success"
                assert record["streaming"] == {
                    "enabled": True,
                    "completed": True,
                    "interrupted": False,
                }
                assert record["output"] == "stream:hello"

        asyncio.run(scenario())

    def test_async_stream_failure_records_error_and_reraises(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        async def scenario():
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped = attach_trust(
                    FakeAgent(stream_fail=True), gateway_url="none", runs_dir=runs_dir
                )
                with self.assertRaisesRegex(RuntimeError, "stream failed"):
                    async with wrapped.run_stream("boom"):
                        pass

                record = _read_one_record(runs_dir)
                assert record["status"] == "error"
                assert record["streaming"]["interrupted"]

        asyncio.run(scenario())

    def test_sync_stream_records_once_on_completion(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(FakeAgent(), gateway_url="none", runs_dir=runs_dir)
            with wrapped.run_stream_sync("hello") as stream:
                assert stream.get_output() == "sync-stream:hello"

            record = _read_one_record(runs_dir)
            assert record["status"] == "success"
            assert record["streaming"]["completed"]
            assert record["output"] == "sync-stream:hello"

    def test_span_attributes_are_secret_filtered(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(FakeAgent(), gateway_url="none", runs_dir=runs_dir)
            wrapped.run_sync("hello")

            record = _read_one_record(runs_dir)
            serialized = json.dumps(record["otel"])
            assert "should-not-persist" not in serialized
            assert "hidden" not in serialized

    def test_existing_otel_provider_is_preserved(self):
        from opentelemetry.sdk.trace import TracerProvider
        from air_blackbox.trust.pydantic_ai import attach_trust

        provider = TracerProvider()
        existing_processor = RecordingSpanProcessor()
        provider.add_span_processor(existing_processor)

        with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
            with tempfile.TemporaryDirectory() as runs_dir:
                before_id = id(provider)
                wrapped = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                assert id(provider) == before_id
                assert wrapped._otel["provider"] is provider
                assert not wrapped._otel["isolated"]

                wrapped.run_sync("hello")

                assert existing_processor.spans
                record = _read_one_record(runs_dir)
                assert record["otel"]["span_count"] >= 1
                assert _air_processor_count(provider) == 1

    def test_isolated_provider_fallback_does_not_replace_global_provider(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        class ImmutableProvider:
            pass

        immutable = ImmutableProvider()
        with patch("opentelemetry.trace.get_tracer_provider", return_value=immutable):
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                assert wrapped._otel["isolated"]
                assert wrapped._otel["provider"] is not immutable

                wrapped.run_sync("hello")

                record = _read_one_record(runs_dir)
                assert record["otel"]["span_count"] >= 1

    def test_duplicate_otel_processor_is_not_added_for_same_provider(self):
        from opentelemetry.sdk.trace import TracerProvider
        from air_blackbox.trust.pydantic_ai import attach_trust

        provider = TracerProvider()
        with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
            with tempfile.TemporaryDirectory() as runs_dir:
                wrapped_one = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                wrapped_one.run_sync("one")

                wrapped_two = attach_trust(
                    FakeAgent(), gateway_url="none", runs_dir=runs_dir
                )
                wrapped_two.run_sync("two")

                assert _air_processor_count(provider) == 1
                _verify_chain(runs_dir, expected_records=2)

    def test_shared_runs_dir_multiple_wrappers_resume_chain(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped_one = attach_trust(
                FakeAgent(), gateway_url="none", runs_dir=runs_dir
            )
            wrapped_one.run_sync("first")

            wrapped_two = attach_trust(
                FakeAgent(), gateway_url="none", runs_dir=runs_dir
            )
            wrapped_two.run_sync("second")

            verification = _verify_chain(runs_dir, expected_records=2)
            assert verification.intact

    def test_shared_runs_dir_restart_style_wrapper_resume_chain(self):
        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(FakeAgent(), gateway_url="none", runs_dir=runs_dir)
            wrapped.run_sync("before-restart")

            del wrapped

            restarted = attach_trust(FakeAgent(), gateway_url="none", runs_dir=runs_dir)
            restarted.run_sync("after-restart")

            verification = _verify_chain(runs_dir, expected_records=2)
            assert verification.intact

    def test_air_blackbox_import_does_not_import_pydantic_ai(self):
        self.tearDown()
        sys.modules.pop("air_blackbox", None)
        sys.modules.pop("pydantic_ai", None)

        module = importlib.import_module("air_blackbox")

        assert module.AirTrust is not None
        assert "pydantic_ai" not in sys.modules
        self.setUp()


class TestPydanticAIRealTestModel(unittest.TestCase):
    def test_real_pydantic_ai_test_model_run_sync(self):
        try:
            from pydantic_ai import Agent
        except ImportError:
            self.skipTest("pydantic-ai is not installed")

        try:
            from pydantic_ai.models.test import TestModel
        except ImportError:
            self.skipTest("pydantic-ai TestModel utility is not installed")

        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            agent = Agent(TestModel())
            wrapped = attach_trust(agent, gateway_url="none", runs_dir=runs_dir)
            result = wrapped.run_sync("hello")

            assert result is not None
            record = _read_one_record(runs_dir)
            assert record["framework"] == "pydantic_ai"
            assert record["status"] == "success"

    def test_shared_runs_dir_multiple_wrappers_resume_chain(self):
        try:
            from pydantic_ai import Agent
        except ImportError:
            self.skipTest("pydantic-ai is not installed")

        try:
            from pydantic_ai.models.test import TestModel
        except ImportError:
            self.skipTest("pydantic-ai TestModel utility is not installed")

        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            agent_one = Agent(TestModel())
            agent_two = Agent(TestModel())

            wrapped_one = attach_trust(agent_one, gateway_url="none", runs_dir=runs_dir)
            wrapped_one.run_sync("first")

            wrapped_two = attach_trust(agent_two, gateway_url="none", runs_dir=runs_dir)
            wrapped_two.run_sync("second")

            verification = _verify_chain(runs_dir, expected_records=2)
            assert verification.intact

    def test_shared_runs_dir_restart_style_wrapper_resume_chain(self):
        try:
            from pydantic_ai import Agent
        except ImportError:
            self.skipTest("pydantic-ai is not installed")

        try:
            from pydantic_ai.models.test import TestModel
        except ImportError:
            self.skipTest("pydantic-ai TestModel utility is not installed")

        from air_blackbox.trust.pydantic_ai import attach_trust

        with tempfile.TemporaryDirectory() as runs_dir:
            wrapped = attach_trust(
                Agent(TestModel()), gateway_url="none", runs_dir=runs_dir
            )
            wrapped.run_sync("before restart")

            del wrapped

            restarted = attach_trust(
                Agent(TestModel()), gateway_url="none", runs_dir=runs_dir
            )
            restarted.run_sync("after restart")

            verification = _verify_chain(runs_dir, expected_records=2)
            assert verification.intact


if __name__ == "__main__":
    unittest.main()
