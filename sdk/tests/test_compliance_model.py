"""Where the compliance model comes from, and reading what it says.

`air-blackbox setup` and the deep scan pull one registry name, which
AIR_COMPLIANCE_MODEL can pin to a tag. model/Modelfile's system prompt asks
the model for FINDING / ARTICLE / SEVERITY blocks, which the parser must
read: output it cannot read adds no findings, silently.
"""

import subprocess
import types

from click.testing import CliRunner

from air_blackbox.compliance import deep_scan as ds


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        return types.SimpleNamespace(returncode=0, stdout="air-compliance:latest\n", stderr="")


def test_the_registry_name_defaults_and_can_be_pinned(monkeypatch):
    monkeypatch.delenv("AIR_COMPLIANCE_MODEL", raising=False)
    assert ds.registry_model() == "airblackbox/air-compliance"
    monkeypatch.setenv("AIR_COMPLIANCE_MODEL", "airblackbox/air-compliance:v3")
    assert ds.registry_model() == "airblackbox/air-compliance:v3"


def test_the_deep_scan_pulls_the_pinned_name(monkeypatch):
    monkeypatch.setenv("AIR_COMPLIANCE_MODEL", "airblackbox/air-compliance:v3")
    rec = Recorder()
    monkeypatch.setattr(ds.subprocess, "run", rec)
    assert ds._auto_pull_model("air-compliance")
    assert rec.calls == [["ollama", "pull", "airblackbox/air-compliance:v3"],
                         ["ollama", "cp", "airblackbox/air-compliance:v3", "air-compliance"]]


def test_another_model_is_pulled_by_its_own_name(monkeypatch):
    monkeypatch.setenv("AIR_COMPLIANCE_MODEL", "airblackbox/air-compliance:v3")
    rec = Recorder()
    monkeypatch.setattr(ds.subprocess, "run", rec)
    ds._auto_pull_model("llama3.2")
    assert rec.calls == [["ollama", "pull", "llama3.2"]]


def test_setup_pulls_the_pinned_name_and_points_the_alias_at_it(monkeypatch):
    from air_blackbox.cli import main

    monkeypatch.setenv("AIR_COMPLIANCE_MODEL", "airblackbox/air-compliance:v3")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    rec = Recorder()
    monkeypatch.setattr(subprocess, "run", rec)
    result = CliRunner().invoke(main, ["setup"])
    assert result.exit_code == 0, result.output
    assert ["ollama", "pull", "airblackbox/air-compliance:v3"] in rec.calls
    assert ["ollama", "cp", "airblackbox/air-compliance:v3", "air-compliance"] in rec.calls
    assert "8GB" not in result.output


MODELFILE_FORMAT = """FINDING: LLM call has no error handling
ARTICLE: 9
SEVERITY: HIGH
EVIDENCE: agent.py line 12, client.chat.completions.create() outside try/except
RECOMMENDATION: Wrap the call in try/except with a fallback response

FINDING: COMPLIANT
ARTICLE: 12
SEVERITY: NONE
EVIDENCE: logging.getLogger() records every call in agent.py
RECOMMENDATION: No action needed

**FINDING:** Approval step can be skipped by the model
**ARTICLE:** Article 14
**SEVERITY:** MEDIUM
**EVIDENCE:** human_approved read from tool arguments
**RECOMMENDATION:** Pass approval from the application, not the model
"""


def test_the_modelfile_format_is_read():
    findings = ds._parse_llm_output(MODELFILE_FORMAT)
    assert [(f["article"], f["status"]) for f in findings] == [(9, "fail"), (12, "pass"), (14, "warn")]
    assert findings[0]["name"] == "LLM call has no error handling"
    assert "outside try/except" in findings[0]["evidence"]
    assert findings[0]["fix_hint"].startswith("Wrap the call")
    assert findings[1]["name"] == "Article 12 analysis" and findings[1]["fix_hint"] == ""
    assert findings[2]["fix_hint"] == "Pass approval from the application, not the model"


def test_a_block_without_an_article_is_dropped():
    assert ds._parse_finding_blocks("FINDING: something\nSEVERITY: HIGH\n") == []


def test_the_markdown_format_still_parses():
    out = "### Article 10 - Data Governance\n**Status**: FAIL\nEvidence: no input validation in tool.py\n"
    assert [(f["article"], f["status"]) for f in ds._parse_llm_output(out)] == [(10, "fail")]
