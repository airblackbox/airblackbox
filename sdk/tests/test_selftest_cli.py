"""`air-blackbox test`, the self-test a new user runs first.

It used to fail 5 of 25 on a clean install: two assertions had gone stale
(the report gained GDPR and US groups; the scanner stopped counting CrewAI
delegation as human oversight) and three gateway tests failed whenever
nothing was listening, which is every fresh install. It also exited 0 no
matter what, so it could not gate anything.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from click.testing import CliRunner

from air_blackbox.cli import main

pytest.importorskip("httpx")


def _run(gateway):
    return CliRunner().invoke(main, ["test", "--gateway", gateway])


def test_clean_install_passes_with_gateway_tests_skipped():
    result = _run("http://127.0.0.1:9")   # nothing listens on the discard port
    assert result.exit_code == 0, result.output
    assert "All Tests Passed" in result.output
    assert "3 skipped" in result.output and "no gateway at" in result.output
    assert "❌" not in result.output


class _BrokenGateway(BaseHTTPRequestHandler):
    """Reachable, but every endpoint errors: that IS a failure, not a skip."""

    def do_GET(self):
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "boom"}).encode())

    def log_message(self, *a):
        pass


def test_broken_gateway_is_a_failure_and_exits_nonzero():
    httpd = HTTPServer(("127.0.0.1", 0), _BrokenGateway)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        result = _run(f"http://127.0.0.1:{httpd.server_port}")
    finally:
        httpd.shutdown()
    assert result.exit_code == 1, result.output
    assert "Tests Failed" in result.output
    assert "Audit endpoint returned 500" in result.output
