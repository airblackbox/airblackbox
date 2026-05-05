import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from air_blackbox.cli import (
    _compliance_score,
    _load_baseline_score,
    _staged_scan_tree,
    comply,
)


def test_compliance_score_counts_passing_checks() -> None:
    articles = [
        {"checks": [{"status": "pass"}, {"status": "fail"}]},
        {"checks": [{"status": "warn"}, {"status": "pass"}]},
    ]

    assert _compliance_score(articles) == 50


def test_load_baseline_score_accepts_saved_shapes(tmp_path) -> None:
    simple = tmp_path / "score.json"
    simple.write_text(json.dumps({"score": 87}))
    articles = tmp_path / "articles.json"
    articles.write_text(
        json.dumps([{"checks": [{"status": "pass"}, {"status": "fail"}]}])
    )

    assert _load_baseline_score(str(simple)) == 87
    assert _load_baseline_score(str(articles)) == 50


def test_staged_scan_tree_reads_git_index_not_worktree(tmp_path, monkeypatch) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sample = tmp_path / "agent.py"
    sample.write_text("STAGED = True\n")
    subprocess.run(
        ["git", "add", "agent.py"], cwd=tmp_path, check=True, capture_output=True
    )
    sample.write_text("STAGED = False\n")
    monkeypatch.chdir(tmp_path)

    with _staged_scan_tree(["agent.py"]) as scan_root:
        staged_copy = Path(scan_root) / "agent.py"
        assert staged_copy.read_text() == "STAGED = True\n"


def test_changed_only_comply_allows_no_staged_python_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        subprocess.run(["git", "init"], check=True, capture_output=True)
        result = runner.invoke(comply, ["--changed-only", "--no-llm", "--no-save"])

    assert result.exit_code == 0
    assert "No staged Python files" in result.output


def test_changed_only_baseline_blocks_score_decrease() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        subprocess.run(["git", "init"], check=True, capture_output=True)
        with open("agent.py", "w", encoding="utf-8") as fh:
            fh.write("import openai\n")
        subprocess.run(["git", "add", "agent.py"], check=True, capture_output=True)
        with open("baseline.json", "w", encoding="utf-8") as fh:
            json.dump({"score": 101}, fh)

        result = runner.invoke(
            comply,
            ["--changed-only", "--baseline", "baseline.json", "--no-llm", "--no-save"],
        )

    assert result.exit_code != 0
    assert "compliance score decreased" in result.output
