import json

from click.testing import CliRunner

from air_blackbox.cli import main
from air_blackbox.gateway_client import GatewayStatus


class StubGatewayClient:
    def __init__(self, gateway_url, runs_dir=None, scan_path=None):
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir
        self.scan_path = scan_path

    def get_status(self):
        return GatewayStatus(url=self.gateway_url)


def test_comply_json_outputs_structured_machine_readable_result(monkeypatch, tmp_path):
    articles = [
        {
            "number": 9,
            "title": "Risk Management",
            "checks": [
                {
                    "name": "Risk assessment document",
                    "status": "pass",
                    "evidence": "Risk assessment document found",
                    "detection": "hybrid",
                    "fix_hint": "",
                    "tier": "static",
                },
                {
                    "name": "Risk mitigations active",
                    "status": "warn",
                    "evidence": "1/4 mitigations active",
                    "detection": "hybrid",
                    "fix_hint": "Enable guardrails.yaml",
                    "tier": "runtime",
                },
            ],
        },
        {
            "number": 10,
            "title": "Data Governance",
            "checks": [
                {
                    "name": "Data vault",
                    "status": "fail",
                    "evidence": "No vault configured.",
                    "detection": "auto",
                    "fix_hint": "Set VAULT_ENDPOINT",
                    "tier": "runtime",
                }
            ],
        },
    ]

    monkeypatch.setattr("air_blackbox.gateway_client.GatewayClient", StubGatewayClient)
    monkeypatch.setattr(
        "air_blackbox.compliance.engine.run_all_checks",
        lambda _status, _scan: (articles, [], "air-langchain-trust"),
    )

    result = CliRunner().invoke(main, ["comply", "--scan", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["version"] == "1.12.0"
    assert payload["checks_total"] == 3
    assert payload["checks_passed"] == 1
    assert payload["checks_warned"] == 1
    assert payload["checks_failed"] == 1
    assert payload["articles"]["article_9"] == {"passed": 1, "warned": 1, "failed": 0}
    assert payload["articles"]["article_10"] == {"passed": 0, "warned": 0, "failed": 1}
    assert payload["findings"][0]["source"] == "rules"
    assert "AIR Blackbox" not in result.output
