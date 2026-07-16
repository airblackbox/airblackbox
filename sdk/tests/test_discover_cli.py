from __future__ import annotations

import json
import inspect
from pathlib import Path

import pytest
from click.testing import CliRunner

from air_blackbox.cli import main
from air_blackbox.gateway_client import GatewayStatus


class FakeGatewayClient:
    status = GatewayStatus(url="http://test")
    error: Exception | None = None

    def __init__(
        self, gateway_url="http://localhost:8080", runs_dir=None, scan_path=None
    ):
        self.gateway_url = gateway_url
        self.runs_dir = runs_dir
        self.scan_path = scan_path

    def get_status(self):
        if self.error:
            raise self.error
        return self.status


@pytest.fixture(autouse=True)
def gateway(monkeypatch):
    FakeGatewayClient.status = GatewayStatus(url="http://test")
    FakeGatewayClient.error = None
    monkeypatch.setattr("air_blackbox.gateway_client.GatewayClient", FakeGatewayClient)


@pytest.fixture
def runner():
    if "mix_stderr" in inspect.signature(CliRunner).parameters:
        return CliRunner(mix_stderr=False)
    return CliRunner()


def _invoke(runner, args):
    return runner.invoke(main, ["discover", *args])


def _json(result):
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _write_package_json(path: Path, deps: dict[str, str]) -> None:
    path.joinpath("package.json").write_text(
        json.dumps({"dependencies": deps}),
        encoding="utf-8",
    )


def test_existing_discover_table_invocation_still_works(runner):
    with runner.isolated_filesystem():
        result = _invoke(runner, [])

    assert result.exit_code == 0
    assert "AI Discovery & Inventory" in result.stdout


def test_format_json_produces_parseable_cyclonedx(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "json"]))

    assert doc["bomFormat"] == "CycloneDX"
    assert doc["specVersion"] == "1.6"


def test_format_cyclonedx_produces_parseable_cyclonedx_16(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    assert doc["bomFormat"] == "CycloneDX"
    assert doc["specVersion"] == "1.6"


def test_json_and_cyclonedx_have_equivalent_content(monkeypatch, runner):
    fixed_meta = {
        "project_name": "proj",
        "timestamp": "2026-01-01T00:00:00Z",
        "serial_number": "urn:uuid:00000000-0000-4000-8000-000000000001",
        "document_namespace": "https://example.test/doc",
        "tool_name": "AIR Blackbox",
        "tool_version": "test",
    }
    monkeypatch.setattr(
        "air_blackbox.cli._discover_metadata", lambda scan_path: fixed_meta
    )
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        json_doc = _json(_invoke(runner, ["--format", "json"]))
        cdx_doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    assert json_doc == cdx_doc


def test_format_spdx_produces_parseable_spdx_23(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "spdx"]))

    assert doc["spdxVersion"] == "SPDX-2.3"


def test_invalid_format_rejected_by_click(runner):
    result = _invoke(runner, ["--format", "bad"])

    assert result.exit_code != 0
    assert "Invalid value" in result.stderr


def test_dependency_only_project_works_without_runtime_traffic(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    names = {component["name"] for component in doc["components"]}
    assert "openai" in names


def test_runtime_only_discovery_works_without_dependency_manifests(runner):
    FakeGatewayClient.status = GatewayStatus(
        reachable=True,
        total_runs=1,
        models_observed=["gpt-4o"],
        providers_observed=["OpenAI"],
        recent_runs=[{"model": "gpt-4o", "tokens": 12}],
    )
    with runner.isolated_filesystem():
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    assert any(component["name"] == "gpt-4o" for component in doc["components"])


def test_empty_project_emits_valid_empty_cyclonedx_json(runner):
    with runner.isolated_filesystem():
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    assert doc["bomFormat"] == "CycloneDX"
    assert isinstance(doc["components"], list)


def test_empty_project_emits_valid_empty_spdx_json(runner):
    with runner.isolated_filesystem():
        doc = _json(_invoke(runner, ["--format", "spdx"]))

    assert doc["spdxVersion"] == "SPDX-2.3"
    assert isinstance(doc["packages"], list)


def test_direct_ai_dependency_appears_in_cyclonedx(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    openai = next(
        component for component in doc["components"] if component["name"] == "openai"
    )
    props = {prop["name"]: prop["value"] for prop in openai["properties"]}
    assert props["air-blackbox:ai-dependency"] == "true"


def test_transitive_ai_dependency_from_package_lock_appears(runner):
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {"dependencies": {"wrapper": "1.0.0"}},
            "node_modules/wrapper": {
                "name": "wrapper",
                "version": "1.0.0",
                "dependencies": {"openai": "4.2.0"},
            },
            "node_modules/openai": {"name": "openai", "version": "4.2.0"},
        },
    }
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    openai = next(
        component for component in doc["components"] if component["name"] == "openai"
    )
    props = {prop["name"]: prop["value"] for prop in openai["properties"]}
    assert props["air-blackbox:dependency-scope"] == "transitive"
    assert props["air-blackbox:ai-dependency"] == "true"


def test_parent_child_relationship_serialized_correctly(runner):
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": {"dependencies": {"wrapper": "1.0.0"}},
            "node_modules/wrapper": {
                "name": "wrapper",
                "version": "1.0.0",
                "dependencies": {"openai": "4.2.0"},
            },
            "node_modules/openai": {"name": "openai", "version": "4.2.0"},
        },
    }
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    edge = next(
        dep for dep in doc["dependencies"] if dep["ref"] == "pkg:npm/wrapper@1.0.0"
    )
    assert "pkg:npm/openai@4.2.0" in edge["dependsOn"]


def test_custom_ai_classifier_config_classifies_custom_package(runner):
    config = {
        "packages": {
            "python": {
                "custom-ai": {"category": "agent", "reason": "test rule"},
            }
        }
    }
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("custom-ai==0.1.0\n", encoding="utf-8")
        Path(cwd, "ai.yaml").write_text(json.dumps(config), encoding="utf-8")
        doc = _json(
            _invoke(runner, ["--format", "cyclonedx", "--ai-libraries", "ai.yaml"])
        )

    dep = next(
        component for component in doc["components"] if component["name"] == "custom-ai"
    )
    props = {prop["name"]: prop["value"] for prop in dep["properties"]}
    assert props["air-blackbox:ai-dependency"] == "true"
    assert props["air-blackbox:ai-category"] == "agent"


def test_invalid_classifier_config_exits_nonzero_without_json_stdout(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "bad.yaml").write_text("packages: [", encoding="utf-8")
        result = _invoke(
            runner, ["--format", "cyclonedx", "--ai-libraries", "bad.yaml"]
        )

    assert result.exit_code != 0
    assert result.stdout == ""
    assert "Error" in result.stderr


def test_gateway_unavailable_does_not_prevent_static_scanning(runner):
    FakeGatewayClient.error = RuntimeError("offline")
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        result = _invoke(runner, ["--format", "cyclonedx"])
        doc = json.loads(result.stdout)

    assert result.exit_code == 0
    assert any(component["name"] == "openai" for component in doc["components"])
    assert "Runtime discovery unavailable" in result.stderr


def test_malformed_manifest_warning_does_not_corrupt_json_stdout(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "pyproject.toml").write_text("[project\n", encoding="utf-8")
        result = _invoke(runner, ["--format", "cyclonedx"])
        doc = json.loads(result.stdout)

    assert result.exit_code == 0
    assert doc["bomFormat"] == "CycloneDX"
    assert "Warning:" in result.stderr


def test_warnings_go_to_stderr_for_machine_formats(runner):
    with runner.isolated_filesystem():
        result = _invoke(runner, ["--format", "spdx"])

    assert result.exit_code == 0
    assert result.stdout.startswith("{")
    assert "Warning:" in result.stderr


def test_banner_absent_from_machine_readable_stdout(runner):
    with runner.isolated_filesystem():
        result = _invoke(runner, ["--format", "cyclonedx"])

    assert result.exit_code == 0
    assert "AIR Blackbox" not in result.stdout.splitlines()[0]
    json.loads(result.stdout)


def test_table_output_includes_static_dependency_information(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        result = _invoke(runner, [])

    assert result.exit_code == 0
    assert "Static Dependencies" in result.stdout
    assert "openai" in result.stdout


def test_output_writes_cyclonedx_file(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "requirements.txt").write_text("openai==1.2.3\n", encoding="utf-8")
        result = _invoke(runner, ["--format", "cyclonedx", "--output", "bom.json"])
        content = Path(cwd, "bom.json").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert result.stdout == ""
    assert content.endswith("\n")
    assert json.loads(content)["bomFormat"] == "CycloneDX"


def test_output_writes_spdx_file(runner):
    with runner.isolated_filesystem() as cwd:
        result = _invoke(runner, ["--format", "spdx", "--output", "bom.spdx.json"])
        content = Path(cwd, "bom.spdx.json").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert result.stdout == ""
    assert content.endswith("\n")
    assert json.loads(content)["spdxVersion"] == "SPDX-2.3"


def test_output_file_status_message_does_not_include_json_stdout(runner):
    with runner.isolated_filesystem():
        result = _invoke(runner, ["--format", "cyclonedx", "--output", "bom.json"])

    assert result.exit_code == 0
    assert result.stdout == ""
    assert "Wrote cyclonedx output" in result.stderr


def test_unwritable_output_path_produces_clear_error(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "outdir").mkdir()
        result = _invoke(runner, ["--format", "cyclonedx", "--output", "outdir"])

    assert result.exit_code != 0
    assert "Could not write output file" in result.stderr


def test_missing_scan_path_rejected(runner):
    result = _invoke(runner, ["--scan-path", "missing", "--format", "cyclonedx"])

    assert result.exit_code != 0
    assert "path does not exist" in result.stderr


def test_scan_path_that_is_file_rejected(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "file.txt").write_text("x", encoding="utf-8")
        result = _invoke(runner, ["--scan-path", "file.txt", "--format", "cyclonedx"])

    assert result.exit_code != 0
    assert "path must be a directory" in result.stderr


def test_existing_approved_option_not_broken(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "approved.json").write_text(
            '{"models": [], "providers": []}', encoding="utf-8"
        )
        result = _invoke(runner, ["--approved", "approved.json"])

    assert result.exit_code == 0


def test_existing_init_registry_behavior_not_broken(runner):
    FakeGatewayClient.status = GatewayStatus(
        reachable=True,
        total_runs=1,
        models_observed=["gpt-4o"],
        providers_observed=["OpenAI"],
        recent_runs=[{"model": "gpt-4o"}],
    )
    with runner.isolated_filesystem() as cwd:
        result = _invoke(runner, ["--init-registry"])
        registry = json.loads(
            Path(cwd, "approved-models.json").read_text(encoding="utf-8")
        )

    assert result.exit_code == 0
    assert "gpt-4o" in registry["models"]


def test_generate_aibom_status_still_works():
    from air_blackbox.aibom.generator import generate_aibom

    status = GatewayStatus(
        total_runs=1, models_observed=["gpt-4o"], recent_runs=[{"model": "gpt-4o"}]
    )
    doc = generate_aibom(status)

    assert doc["bomFormat"] == "CycloneDX"
    assert doc["specVersion"] == "1.6"


def test_static_dependency_warnings_not_serialized_as_components(runner):
    with runner.isolated_filesystem() as cwd:
        Path(cwd, "pyproject.toml").write_text("[project\n", encoding="utf-8")
        doc = _json(_invoke(runner, ["--format", "cyclonedx"]))

    assert all(
        "warning" not in component["name"].lower() for component in doc["components"]
    )
