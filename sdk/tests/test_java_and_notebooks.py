"""Java and Jupyter notebook support in the compliance scanners.

A notebook must get exactly the result its code would get as a .py file;
Java must get the same result as the equivalent Python (parity corpus).
"""

import json
import re

import pytest

from air_blackbox.compliance.code_scanner import (
    _find_source_files,
    _java_definitions,
    _jsdoc_above,
    scan_codebase,
)
from air_blackbox.compliance.engine import detect_frameworks, run_all_checks
from air_blackbox.compliance.sources import (
    Source,
    has,
    language_of,
    notebook_code,
    read_text,
)
from air_blackbox.gateway_client import GatewayStatus


def _nb(cells, language="python", nbformat=4):
    def cell(src):
        kind = "markdown" if src.startswith("# MD ") else "code"
        return {"cell_type": kind, "metadata": {}, "source": src.splitlines(keepends=True)}
    if nbformat == 3:
        return json.dumps({"nbformat": 3, "metadata": {"language": language},
                           "worksheets": [{"cells": [
                               {"cell_type": "code", "input": c} for c in cells]}]})
    return json.dumps({"nbformat": 4, "cells": [cell(c) for c in cells],
                       "metadata": {"kernelspec": {"language": language, "name": "k"}}})


def _write(root, files):
    for name, code in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)


def _by_name(findings):
    return {f.name: (f.status, f.evidence) for f in findings}


# ── notebooks ──────────────────────────────────────────────────────────

def test_notebook_code_cells_magics_and_markdown():
    code = notebook_code(_nb(["%pip install openai\nimport openai", "# MD prose",
                              "!ls\nx = 1", "%%bash\necho hi"]))
    assert code == "# %pip install openai\nimport openai\n# !ls\nx = 1\n# %%bash\n# echo hi\n"


def test_non_python_kernel_and_junk_are_skipped():
    assert notebook_code(_nb(["x <- 1"], language="R")) is None
    assert notebook_code("not json") is None
    assert notebook_code("[1, 2]") is None
    assert notebook_code(_nb(["import os"], nbformat=3)) == "import os\n"


def test_notebook_scans_exactly_like_the_same_python_file(tmp_path):
    py = ('import logging\nimport openai\nlogger = logging.getLogger(__name__)\n\n'
          'def ask(q: str) -> str:\n    """Ask the model."""\n    try:\n'
          '        return openai.OpenAI().chat.completions.create(model="m", messages=q)\n'
          '    except Exception:\n        logger.error("failed")\n')
    (tmp_path / "py").mkdir()
    (tmp_path / "nb").mkdir()
    (tmp_path / "py" / "agent.py").write_text(py)
    cells = py.rstrip("\n").split("\n\n")
    (tmp_path / "nb" / "agent.ipynb").write_text(_nb(["%load_ext autoreload"] + cells))
    as_py = _by_name(scan_codebase(str(tmp_path / "py")))
    as_nb = _by_name(scan_codebase(str(tmp_path / "nb")))
    assert {k: v[0] for k, v in as_py.items()} == {k: v[0] for k, v in as_nb.items()}


def test_notebook_checkpoints_and_r_notebooks_are_not_scanned(tmp_path):
    _write(tmp_path, {"a.ipynb": _nb(["import openai"]),
                      ".ipynb_checkpoints/a-checkpoint.ipynb": _nb(["import openai"]),
                      "r.ipynb": _nb(["library(x)"], language="R")})
    files = _find_source_files(str(tmp_path))
    assert sorted(f.rsplit("/", 1)[1] for f in files) == ["a.ipynb", "r.ipynb"]
    assert read_text(str(tmp_path / "r.ipynb")) is None
    findings = scan_codebase(str(tmp_path))  # r.ipynb read as nothing, not as JSON
    assert findings


def test_frameworks_and_bias_read_notebook_code_not_json(tmp_path):
    _write(tmp_path, {"screen.ipynb": _nb([
        "from crewai import Crew",
        "def screen(applicant):\n    return applicant['gender'] == 'female' and applicant['years_experience'] > 2"])})
    results, frameworks, rec_pkg, _ = run_all_checks(GatewayStatus(), str(tmp_path), "all")
    assert frameworks == ["crewai"] and rec_pkg == "air-crewai-trust"
    bias = [c for a in results if a.get("number") == "BIAS" for c in a["checks"]]
    assert any(c["name"] == "Gender term references" for c in bias)


# ── Java ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name, lang", [
    ("Agent.java", "java"), ("module-info.java", None), ("package-info.java", None),
    ("agent.ipynb", "python"), ("Agent.kt", "kotlin"), ("main.kts", "kotlin"),
    ("build.gradle.kts", None), ("settings.gradle.kts", None),
])
def test_language_of(name, lang):
    assert language_of(name) == lang


def test_java_build_output_and_tests(tmp_path):
    _write(tmp_path, {
        "src/main/java/a/Agent.java": "/** Agent. */\npublic class Agent {\n"
                                      "    /** Run. */\n    public String run() { return \"\"; }\n}\n",
        "src/test/java/a/AgentTest.java": "public class AgentTest { void t() {} }\n",
        "src/main/java/a/AgentIT.java": "public class AgentIT { void t() {} }\n",
        "target/generated-sources/G.java": "public class G {}\n",
    })
    files = {f.split(str(tmp_path) + "/", 1)[1] for f in _find_source_files(str(tmp_path))}
    assert "target/generated-sources/G.java" not in files
    docs = _by_name(scan_codebase(str(tmp_path)))["Code documentation (docstrings)"]
    assert docs[0] == "pass" and docs[1].startswith("2/2 ") and "Javadoc" in docs[1]


JAVA = '''/** Service. */
@Service
public class Svc {
    public Svc(Repo r) { }
    /** Renders it. */
    @Override public String toString() { return ""; }
    @Transactional(readOnly = true)
    public List<Item> list() {
        return repo.findAll();
    }
    private void helper() {}
    abstract int size();
    String plain(int a,
                 int b) throws IOException {
        return foo(a);
    }
    public <T> T generic(Class<T> c)
    {
        return null;
    }
}
'''


def test_java_definitions():
    defs = {d.name: d for d in _java_definitions(Source(JAVA, "java"))}
    assert set(defs) == {"Svc", "toString", "list", "helper", "plain", "generic"}
    assert defs["Svc"].kind == "class" and defs["Svc"].documented
    assert defs["toString"].documented
    assert not defs["list"].documented  # the doc above belongs to toString
    assert defs["helper"].private
    assert all(d.typed for d in defs.values() if d.kind == "function")


def test_annotation_only_lines_are_skipped_but_code_lines_are_not():
    lines = ["/** Doc. */", "@Bean", "@Override public void a() {}", "void b() {}"]
    assert _jsdoc_above(lines, 3) is None
    assert _jsdoc_above(lines, 2) == "/** Doc. */"


def test_java_idioms(tmp_path):
    _write(tmp_path, {"Agent.java": '''import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import dev.langchain4j.model.chat.ChatModel;
import org.springframework.retry.annotation.Retryable;

public class Agent {
    private static final Logger log = LoggerFactory.getLogger(Agent.class);
    private ChatModel model;
    private boolean requireApproval;

    @Retryable
    public String ask(String userInput) {
        try {
            return model.chat("Answer: %s".formatted(userInput));
        } catch (RuntimeException e) {
            log.error("failed", e);
            return "";
        }
    }
}
'''})
    got = _by_name(scan_codebase(str(tmp_path)))
    assert got["LLM call error handling"][0] == "pass"
    assert got["Application logging"][0] == "pass"
    assert got["Retry / backoff logic"][0] == "pass"
    assert got["Human-in-the-loop patterns"][0] == "pass"  # requireApproval
    assert got["Unsafe input handling"][0] == "warn"
    assert got["Type annotations"][0] == "pass"


def test_system_out_is_not_logging(tmp_path):
    _write(tmp_path, {"A.java": "public class A { void f() { System.out.println(1); } }\n"})
    status, evidence = _by_name(scan_codebase(str(tmp_path)))["Application logging"]
    assert status == "fail" and "SLF4J" in evidence


def test_java_frameworks_and_advice(tmp_path):
    _write(tmp_path, {"A.java": "import dev.langchain4j.model.chat.ChatModel;\n"
                                "import org.springframework.ai.chat.client.ChatClient;\n"
                                "import static com.openai.client.okhttp.OpenAIOkHttpClient.fromEnv;\n"
                                "public class A {}\n"})
    results, frameworks, _rec, _ = run_all_checks(GatewayStatus(), str(tmp_path), "all")
    assert frameworks == ["LangChain4j", "OpenAI Java SDK", "Spring AI"]
    hints = [c.get("fix_hint", "") for a in results for c in a["checks"]]
    assert not any(re.search(r"pip install air-[\w-]+-trust", h) for h in hints)


def test_java_specific_patterns_only_apply_to_java():
    py = Source("x = '.formatted(input)'", "python")
    java = Source('String p = "Q: %s".formatted(input);', "java")
    pattern = r"zzz_never"
    assert not has(pattern, py, java=r"\.formatted\([^)\n]*input")
    assert has(pattern, java, java=r"\.formatted\([^)\n]*input")
    assert not has(pattern, Source("x.formatted(input)", "typescript"),
                   java=r"\.formatted\([^)\n]*input")
