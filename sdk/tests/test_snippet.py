"""scan_snippet: one piece of pasted code gets the result a project scan gives.

The website console and the MCP server call this instead of keeping their
own copies of the checks, so a snippet's verdict can never drift from the
CLI's.
"""

import json

import pytest

from air_blackbox.compliance.code_scanner import scan_codebase
from air_blackbox.compliance.snippet import LANGUAGE_ALIASES, guess_language, scan_snippet

PY = 'import logging\nimport openai\nlog = logging.getLogger(__name__)\n\n' \
     'def ask(q: str) -> str:\n    """Ask."""\n    try:\n' \
     '        return openai.OpenAI().chat.completions.create(model="m", messages=q)\n' \
     '    except Exception:\n        log.error("x")\n'
TS = 'import OpenAI from "openai";\nconst client = new OpenAI();\n' \
     'export async function ask(q: string): Promise<string> {\n' \
     '  return client.chat.completions.create({ model: "m", messages: q });\n}\n'
JS = 'const OpenAI = require("openai");\nconst client = new OpenAI();\n' \
     'async function ask(q) {\n  return client.chat.completions.create({ model: "m" });\n}\n' \
     'module.exports = { ask };\n'
JAVA = 'import com.openai.client.OpenAIClient;\nimport org.slf4j.LoggerFactory;\n\n' \
       'public class Agent {\n    private static final Logger log = LoggerFactory.getLogger(Agent.class);\n' \
       '    public String ask(String q) {\n        return client.chat().completions().create(params).toString();\n    }\n}\n'
KT = 'import dev.langchain4j.model.chat.ChatModel\n\n' \
     'fun ask(model: ChatModel, q: String): String = model.chat(q)\n' \
     'val names = listOf("a", "b")\n'
NB = json.dumps({"nbformat": 4, "cells": [{"cell_type": "code", "metadata": {}, "source": [PY]}],
                 "metadata": {"kernelspec": {"language": "python", "name": "python3"}}})


@pytest.mark.parametrize("code, lang", [
    (PY, "python"), (TS, "typescript"), (JS, "javascript"), (JAVA, "java"),
    (KT, "kotlin"), (NB, "notebook"),
])
def test_guess_language(code, lang):
    assert guess_language(code) == lang


def test_filename_beats_content():
    assert guess_language(PY, "x.ts") == "typescript"
    assert guess_language("", "nb.ipynb") == "notebook"


def test_jsdoc_types_do_not_make_javascript_typescript():
    js = "/** @param {(call: any) => Promise<string>} execute */\nfunction run(execute) {}\n"
    assert guess_language(js) == "javascript"


def test_empty_or_unknown_defaults_to_python():
    assert guess_language("") == "python"
    assert guess_language("hello world") == "python"


def test_snippet_matches_project_scan(tmp_path):
    (tmp_path / "agent.py").write_text(PY)
    project = {f.name: f.status for f in scan_codebase(str(tmp_path))}
    result = scan_snippet(PY)
    assert result["language"] == "python" and result["language_source"] == "detected"
    assert {f["name"]: f["status"] for f in result["findings"]} == project
    assert "files" not in result["findings"][0]


def test_stated_language_and_aliases():
    for alias in ("ts", "TypeScript", "typescript"):
        assert scan_snippet(TS, language=alias)["language"] == "typescript"
    assert scan_snippet(KT, language="kt")["language_source"] == "stated"
    with pytest.raises(ValueError):
        scan_snippet(PY, language="cobol")
    assert set(LANGUAGE_ALIASES.values()) == {
        "python", "notebook", "typescript", "javascript", "java", "kotlin"}


def test_kotlin_snippet_uses_jvm_adapters():
    result = scan_snippet(KT)
    assert result["language"] == "kotlin"
    assert result["frameworks"] == ["LangChain4j"]
    status = {f["name"]: f["status"] for f in result["findings"]}
    assert status["LLM call error handling"] == "fail"   # a model call, no try/catch
    assert status["Type annotations"] == "pass"


def test_java_filename_is_kept_for_class_naming():
    result = scan_snippet(JAVA, filename="src/test/java/AgentTest.java")
    assert result["language_source"] == "filename"
    # a test file is excluded from documentation coverage, as in a project scan
    docs = next(f for f in result["findings"] if f["name"] == "Code documentation (docstrings)")
    assert docs["evidence"].startswith("No public")


def test_notebook_snippet():
    result = scan_snippet(NB)
    assert result["language"] == "notebook"
    assert {f["name"]: f["status"] for f in result["findings"]} == \
        {f["name"]: f["status"] for f in scan_snippet(PY)["findings"]}


def test_gdpr_and_us_sections_are_present():
    result = scan_snippet(PY)
    assert any(f["name"].startswith("GDPR") for f in result["gdpr"])
    assert len(result["us"]) == 9
