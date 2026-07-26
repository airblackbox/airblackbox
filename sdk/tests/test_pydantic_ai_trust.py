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

    def __init__(self, *, output=None, fail=False, delay=0.0):
        self.name = "fake-agent"
        self.output = output
        self.fail = fail
        self.delay = delay

    def run_sync(self, user_prompt, **kwargs):
        messages = _current_messages.get()
        if messages is not None:
            messages.append({"role": "user", "content": user_prompt})
        if self.fail:
            raise ValueError("provider failed with safe test error")
        return FakeRunResult(
            output=self.output if self.output is not None else f"sync:{user_prompt}",
            run_id=f"sync-{user_prompt}",
            usage={"total_tokens": 3},
        )

    async def run(self, user_prompt, **kwargs):
        messages = _current_messages.get()
        if messages is not None:
            messages.append({"role": "user", "content": user_prompt})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise ValueError("async provider failed")
        return FakeRunResult(
            output=self.output if self.output is not None else f"async:{user_prompt}",
            run_id=f"async-{user_prompt}",
            usage={"total_tokens": 4},
        )

    def output_json_schema(self):
        if isinstance(self.output, BaseModel):
            return type(self.output).model_json_schema()
        return None

    def normal_attribute(self):
        return "delegated"


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

        asyncio.run(scenario())

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


if __name__ == "__main__":
    unittest.main()
