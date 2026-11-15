"""A CLI on one machine against an AIR server on another.

The fake server below answers the way the Go gateway does (pkg/proxy): every
endpoint but /health needs the X-Gateway-Key header, /v1/audit has
chain_valid and chain_length at the top level, and /v1/records serves the
newest records with the runtime features. All data is fictional.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from click.testing import CliRunner

import air_blackbox.gateway_client as gc
from air_blackbox.compliance import deep_scan as ds
from air_blackbox.gateway_client import GatewayClient

KEY = "gw-test-key"

RECORDS = [
    {"run_id": f"run-{i}", "model": "air-compliance", "provider": "ollama", "status": "success",
     "timestamp": f"2026-11-15T10:00:0{i}Z", "tokens": {"prompt": 10, "completion": 5, "total": 15},
     "chain_seq": i + 1, "chain_hash": f"{i:064x}"}
    for i in range(3)
]

COMPLETION = ("### Article 12 - Record-Keeping\n**Status**: PASS\n"
              "Evidence: logging configured in agent.py via audit_log()\n")


class FakeAirServer:
    def __init__(self, records_status=200):
        self.records_status = records_status
        self.requests = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, body):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _authorized(self):
                return self.headers.get("X-Gateway-Key") == KEY

            def do_GET(self):
                server.requests.append(("GET", self.path, dict(self.headers), None))
                if self.path == "/health":
                    return self._send(200, {"status": "ok"})
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized: invalid or missing gateway key"})
                if self.path == "/v1/audit":
                    return self._send(200, {"chain_length": 3, "chain_valid": True,
                                            "chain_broken_at": 0, "compliance": {}})
                if self.path.startswith("/v1/records"):
                    if server.records_status != 200:
                        return self._send(server.records_status, {"error": "not found"})
                    return self._send(200, {"total": 3, "records": list(reversed(RECORDS)),
                                            "features": {"vault": True, "guardrails": True,
                                                         "otel": True, "chain": True}})
                return self._send(404, {"error": "not found"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                server.requests.append(("POST", self.path, dict(self.headers), body))
                if not self._authorized():
                    return self._send(401, {"error": "unauthorized: invalid or missing gateway key"})
                if self.path == "/v1/chat/completions":
                    return self._send(200, {"choices": [{"message": {"role": "assistant",
                                                                      "content": COMPLETION}}]})
                return self._send(404, {"error": "not found"})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def remote(monkeypatch):
    """Treat the fake server as another machine."""
    monkeypatch.setattr(gc, "_LOOPBACK_HOSTS", set())


@pytest.fixture(autouse=True)
def no_ambient_keys(monkeypatch):
    for name in ("AIR_GATEWAY_KEY", "GATEWAY_KEY", "AIR_GATEWAY_URL", "AIR_MODEL_SERVER", "RUNS_DIR"):
        monkeypatch.delenv(name, raising=False)


def _write_local_record(d, run_id="local-1"):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{run_id}.air.json").write_text(json.dumps(
        {"run_id": run_id, "model": "local-model", "provider": "openai", "status": "success",
         "timestamp": "2026-11-01T00:00:00Z", "tokens": {"total": 1}}))


def test_a_remote_server_supplies_its_records_and_features(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with FakeAirServer() as srv:
        status = GatewayClient(gateway_url=srv.url, gateway_key=KEY).get_status()
    assert status.reachable and not status.auth_failed
    assert status.records_source == "server"
    assert status.total_runs == 3
    assert status.models_observed == ["air-compliance"]
    assert status.audit_chain_intact and status.audit_chain_length == 3
    assert status.vault_enabled and status.guardrails_enabled and status.otel_enabled
    assert status.trust_signing_key_set
    assert all(h.get("X-Gateway-Key") == KEY for m, p, h, _ in srv.requests if p != "/health")


def test_the_key_comes_from_the_environment(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIR_GATEWAY_KEY", KEY)
    with FakeAirServer() as srv:
        status = GatewayClient(gateway_url=srv.url).get_status()
    assert status.total_runs == 3 and not status.auth_failed


def test_a_missing_key_is_reported_not_read_as_no_traffic(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with FakeAirServer() as srv:
        status = GatewayClient(gateway_url=srv.url).get_status()
    assert status.auth_failed
    assert status.total_runs == 0


def test_a_server_without_the_records_endpoint_falls_back_to_disk(remote, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_local_record(tmp_path / "runs")
    with FakeAirServer(records_status=404) as srv:
        status = GatewayClient(gateway_url=srv.url, gateway_key=KEY).get_status()
    assert status.records_source == ""
    assert status.total_runs == 1 and status.models_observed == ["local-model"]
    # The audit chain still comes from the server, in the shape it serves.
    assert status.audit_chain_intact and status.audit_chain_length == 3


def test_a_gateway_on_this_machine_is_read_from_disk_first(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_local_record(tmp_path / "runs")
    with FakeAirServer() as srv:
        status = GatewayClient(gateway_url=srv.url, gateway_key=KEY).get_status()
        assert status.total_runs == 1 and status.records_source == ""
        # With nothing on disk, the API fills in.
        (tmp_path / "runs" / "local-1.air.json").unlink()
        status = GatewayClient(gateway_url=srv.url, gateway_key=KEY).get_status()
    assert status.total_runs == 3 and status.records_source == "server"


def test_an_explicit_runs_dir_is_always_the_disk(remote, tmp_path):
    _write_local_record(tmp_path / "elsewhere")
    with FakeAirServer() as srv:
        status = GatewayClient(gateway_url=srv.url, runs_dir=str(tmp_path / "elsewhere"),
                               gateway_key=KEY).get_status()
    assert status.total_runs == 1
    assert not any(p.startswith("/v1/records") for _, p, _, _ in srv.requests)


def _no_ollama(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError(f"ollama must not run with a model server: {args}")
    monkeypatch.setattr(ds.subprocess, "run", refuse)


def test_the_deep_scan_runs_on_the_servers_model(monkeypatch):
    _no_ollama(monkeypatch)
    with FakeAirServer() as srv:
        result = ds.deep_scan("import logging\n" * 10, model_server=srv.url, gateway_key=KEY,
                              total_files=1, rule_context="Article 12: 1 PASS")
    assert result["error"] is None
    assert [(f["article"], f["status"]) for f in result["findings"]] == [(12, "pass")]
    (method, path, headers, body), = [r for r in srv.requests if r[0] == "POST"]
    assert path == "/v1/chat/completions"
    assert headers.get("X-Gateway-Key") == KEY
    assert body["model"] == "air-compliance" and body["stream"] is False
    assert body["temperature"] == ds.MODEL_TEMPERATURE and body["top_p"] == ds.MODEL_TOP_P
    assert "### Instruction:" in body["messages"][0]["content"]


def test_a_refused_key_on_the_model_server_says_which_key(monkeypatch):
    _no_ollama(monkeypatch)
    with FakeAirServer() as srv:
        result = ds.deep_scan("import logging\n" * 10, model_server=srv.url, gateway_key="wrong")
    assert result["findings"] == []
    assert "AIR_GATEWAY_KEY" in result["error"]


def test_an_unreachable_model_server_is_an_error_not_a_crash(monkeypatch):
    _no_ollama(monkeypatch)
    result = ds.deep_scan("import logging\n" * 10, model_server="http://127.0.0.1:9", gateway_key=KEY)
    assert result["findings"] == [] and "Could not reach the model server" in result["error"]
    result = ds.deep_scan("x = 1\n" * 20, model_server="ftp://example.invalid")
    assert "http(s) URL" in result["error"]


def test_comply_points_at_the_server_with_three_variables(remote, tmp_path, monkeypatch):
    """What a teammate does: set AIR_GATEWAY_URL, AIR_MODEL_SERVER and
    AIR_GATEWAY_KEY, then run comply with no other flags."""
    from air_blackbox.cli import main

    _no_ollama(monkeypatch)
    project = tmp_path / "project"
    project.mkdir()
    (project / "agent.py").write_text(
        "import logging\nlogger = logging.getLogger(__name__)\n\n"
        "def run(prompt):\n    logger.info('called with %d chars', len(prompt))\n    return prompt\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AIR_BLACKBOX_TELEMETRY", "off")
    with FakeAirServer() as srv:
        monkeypatch.setenv("AIR_GATEWAY_URL", srv.url)
        monkeypatch.setenv("AIR_MODEL_SERVER", srv.url)
        monkeypatch.setenv("AIR_GATEWAY_KEY", KEY)
        result = CliRunner().invoke(main, ["comply", "--scan", str(project), "--no-save",
                                           "--format", "json"])
    assert result.exit_code == 0, result.output
    assert "3 logged events from the gateway's records" in result.output
    assert any(m == "POST" for m, _, _, _ in srv.requests), "the deep scan never reached the server"
    articles, _ = json.JSONDecoder().raw_decode(result.output[result.output.index("\n[") + 1:])
    checks = {c["name"]: c["status"] for a in articles for c in a.get("checks", [])}
    assert checks["Automatic event logging"] == "pass"
    assert checks["Data vault (controlled storage)"] == "pass"
