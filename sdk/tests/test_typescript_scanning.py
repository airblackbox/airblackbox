"""TypeScript and JavaScript support in the compliance scanners.

The contract: equivalent code gets the same result in every language, and
Python results are exactly what they were before other languages existed.
"""

import json
import os
import re
import sys

import pytest

from air_blackbox.compliance import sources
from air_blackbox.compliance.code_scanner import (
    _find_python_files,
    _find_source_files,
    _js_definitions,
    scan_codebase,
)
from air_blackbox.compliance.engine import detect_frameworks, run_all_checks
from air_blackbox.compliance.sources import Source, has, language_of, snake_view
from air_blackbox.gateway_client import GatewayStatus

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _write(root, files):
    for name, code in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)


def _status(findings, name):
    (f,) = [f for f in findings if f.name == name]
    return f


# ── parity corpus ──────────────────────────────────────────────────────

def test_parity_corpus_same_status_in_every_language():
    sys.path.insert(0, os.path.join(REPO, "eval", "scanner"))
    try:
        import run_parity
    finally:
        sys.path.pop(0)
    corpus, mismatches, _agree, _shared = run_parity.run()
    assert len(corpus) >= 144
    assert mismatches == []


# ── Python stays exactly as it was ─────────────────────────────────────

def test_python_files_take_the_plain_regex_path():
    src = Source("maxRetries = 3", "python")
    assert src.alt is None and src.lowered is None
    # camelCase in a .py file must not be treated as snake_case
    assert not has(r"max_retries", src, re.IGNORECASE)
    assert has(r"max_retries", Source("max_retries = 3", "python"), re.IGNORECASE)


def test_python_only_tree_finds_exactly_the_old_file_list(tmp_path):
    _write(tmp_path, {"a.py": "", "pkg/b.py": "", "out/c.py": "", ".next/d.py": "",
                      "node_modules/e.py": "", "build/f.py": "", "X.PY": ""})
    assert _find_source_files(str(tmp_path)) == _find_python_files(str(tmp_path))


# ── which files are read ───────────────────────────────────────────────

@pytest.mark.parametrize("name, lang", [
    ("agent.py", "python"), ("agent.ts", "typescript"), ("App.tsx", "typescript"),
    ("x.mts", "typescript"), ("x.cts", "typescript"), ("agent.js", "javascript"),
    ("App.jsx", "javascript"), ("x.mjs", "javascript"), ("x.cjs", "javascript"),
    ("types.d.ts", None), ("vendor.min.js", None), ("app.bundle.js", None),
    ("vite.config.ts", None), ("jest.config.js", None), (".eslintrc.js", None),
    ("styles.css", None), ("agent.PY", None), ("config.ts", "typescript"),
])
def test_language_of(name, lang):
    assert language_of(name) == lang


def test_js_build_output_is_skipped_but_python_there_is_not(tmp_path):
    _write(tmp_path, {"src/agent.ts": "", ".next/server/page.js": "", "coverage/x.js": "",
                      "out/y.js": "", "node_modules/openai/index.js": "", "dist/z.js": "",
                      "out/tool.py": ""})
    found = {os.path.relpath(p, tmp_path) for p in _find_source_files(str(tmp_path))}
    assert found == {"src/agent.ts", "out/tool.py"}


def test_single_typescript_file(tmp_path):
    f = tmp_path / "agent.ts"
    f.write_text("import OpenAI from 'openai';\nconst c = new OpenAI();\n")
    assert _find_source_files(str(f)) == [str(f)]
    results, frameworks, *_ = run_all_checks(GatewayStatus(), str(f), standard="all")
    assert frameworks == ["OpenAI Node SDK"]
    assert results


# ── snake_case view and matching ───────────────────────────────────────

@pytest.mark.parametrize("text, view", [
    ("requireApproval", "require_approval"),
    ("detectPII", "detect_pii"),
    ("PIIRedactor", "pii_redactor"),
    ("maxTokens: 500", "max_tokens: 500"),
    ("rate-limiter-flexible", "rate_limiter_flexible"),
    ("HumanInTheLoop", "human_in_the_loop"),
    ("a\nbC", "a\nb_c"),
])
def test_snake_view(text, view):
    assert snake_view(text) == view


def test_fast_case_insensitive_path_matches_re_ignorecase():
    patterns = [r"prompt.?injection", r"\bpii\b", r"(?:agent|llm).*user_id",
                r"[A-Z][a-z]+Guard", r"\S+_log\b", r"Fingerprint", r"\d{4}\s*day",
                r"rate_limit(?:er|ing)", r"OpenAI\("]
    texts = ["const x = promptInjection(userInput)", "PII", "export const API = 1",
             "agentRun.userId", "class PromptGuard {}", "AUDIT_LOG", "fingerprint",
             "1460 days", "new RateLimiter()", "new OpenAI()", "nothing here"]
    for p in patterns:
        for t in texts:
            src = Source(t, "typescript")
            expected = bool(re.search(p, t, re.I) or re.search(p, src.alt, re.I))
            assert has(p, src, re.IGNORECASE) == expected, (p, t)


# ── syntax adapters ────────────────────────────────────────────────────

TS_DEFS = '''
/** Answers a question. */
export async function answer(q: string): Promise<string> { return q; }

export function untyped(q) { return q; }

export function overloaded(a: string): string;
export function overloaded(a: any) { return a; }

/**
 * @param {string} q
 */
export const tagsOnly = (q) => q;

export default function () {}

const timer = 1;

export const traced = traceable(async (x: unknown) => x);

function host() {
  const timer = setTimeout(() => {}, 10);
  const xs = [1].filter((x) => x > 0);
}

/** A store. */
@Injectable()
export class Store {
  constructor(private db: Db) {}
  /** Gets one. */
  get(id: string): Item { return this.db.get(id); }
  private secret() {}
  #hidden() {}
  _internal() {}
  async list() { return []; }
}
'''


def test_js_definitions():
    defs = {d.name: d for d in _js_definitions(Source(TS_DEFS, "typescript"))}
    assert set(defs) == {"answer", "untyped", "overloaded", "tagsOnly", "default",
                         "traced", "host", "Store", "get", "secret", "#hidden",
                         "_internal", "list"}
    assert defs["answer"].documented and defs["answer"].typed
    assert not defs["untyped"].typed and not defs["untyped"].documented
    assert defs["tagsOnly"].typed and not defs["tagsOnly"].documented  # tags are types, not docs
    assert defs["traced"].typed
    assert defs["Store"].kind == "class" and defs["Store"].documented  # decorator in between
    assert defs["get"].documented and defs["get"].typed
    assert defs["secret"].private and defs["#hidden"].private and defs["_internal"].private
    assert not defs["list"].private and not defs["list"].typed


def test_plain_javascript_types_come_from_jsdoc_only():
    js = Source("/** @param {string} a */\nfunction f(a) {}\nfunction g(a = {k: v}) {}\n",
                "javascript")
    defs = {d.name: d for d in _js_definitions(js)}
    assert defs["f"].typed and not defs["g"].typed


def test_js_test_files_do_not_count_toward_docs_or_types(tmp_path):
    _write(tmp_path, {
        "src/agent.ts": "/** Run. */\nexport function run(x: string): string { return x; }\n",
        "src/agent.test.ts": "function helperOne() {}\nfunction helperTwo() {}\n",
        "src/__tests__/b.ts": "function helperThree() {}\n",
    })
    findings = scan_codebase(str(tmp_path))
    assert _status(findings, "Code documentation (docstrings)").evidence.startswith("1/1 ")
    assert _status(findings, "Type annotations").evidence.startswith("1/1 ")


def test_error_handling_try_catch_and_promise_catch(tmp_path):
    _write(tmp_path, {
        "a.ts": "const r = await client.chat.completions.create({}).catch(() => null);\n",
        "b.js": "try {\n  await generateText({ model, prompt });\n} catch (e) {\n  log(e);\n}\n",
    })
    f = _status(scan_codebase(str(tmp_path)), "LLM call error handling")
    assert f.status == "pass"
    assert "try/catch" in f.evidence


def test_unsafe_template_literal(tmp_path):
    _write(tmp_path, {"a.ts": "const prompt = `Answer this: ${userInput}`;\n"})
    assert _status(scan_codebase(str(tmp_path)), "Unsafe input handling").status == "warn"


def test_console_log_is_not_logging(tmp_path):
    _write(tmp_path, {"a.ts": "console.log('hi');\n"})
    f = _status(scan_codebase(str(tmp_path)), "Application logging")
    assert f.status == "fail"
    assert "pino" in f.evidence and "loguru" not in f.evidence


def test_zod_counts_like_pydantic_and_interfaces_do_not(tmp_path):
    _write(tmp_path, {"a.ts": "interface Req { q: string }\n"
                              "await client.chat.completions.create({});\n"})
    assert _status(scan_codebase(str(tmp_path)),
                   "Input validation / schema enforcement").status == "warn"
    _write(tmp_path, {"a.ts": "import { z } from 'zod';\nconst Req = z.object({ q: z.string() });\n"
                              "await client.chat.completions.create({});\n"})
    assert _status(scan_codebase(str(tmp_path)),
                   "Input validation / schema enforcement").status == "pass"


# ── frameworks and advice ──────────────────────────────────────────────

def test_npm_frameworks_detected_from_imports_only(tmp_path):
    _write(tmp_path, {
        "a.ts": "import { generateText } from 'ai';\nimport { ChatOpenAI } from '@langchain/openai';\n",
        "b.js": "const Anthropic = require('@anthropic-ai/sdk');\n",
        "c.ts": "const msg = { role: 'ai', content: 'openai' };\n",
        "node_modules/openai/index.js": "import x from '@mastra/core';\n",
    })
    assert detect_frameworks(str(tmp_path)) == [
        "Anthropic TypeScript SDK", "LangChain.js", "Vercel AI SDK"]


def test_typescript_only_project_is_never_told_to_pip_install(tmp_path):
    _write(tmp_path, {"agent.ts": "import OpenAI from 'openai';\nconst c = new OpenAI();\n"})
    results, _fw, _rec, _hint = run_all_checks(GatewayStatus(), str(tmp_path), standard="all")
    hints = [c.get("fix_hint", "") for a in results for c in a["checks"]]
    assert not any("pip install" in h for h in hints)
    assert any("base URL" in h for h in hints)


def test_mixed_project_recommends_the_python_trust_layer(tmp_path):
    _write(tmp_path, {"web/app.ts": "import { generateText } from 'ai';\n",
                      "agents/crew.py": "from crewai import Crew\n"})
    _results, frameworks, rec_pkg, _ = run_all_checks(GatewayStatus(), str(tmp_path), standard="eu")
    assert frameworks == ["Vercel AI SDK", "crewai"]
    assert rec_pkg == "air-crewai-trust"


def test_cli_comply_on_a_typescript_project(tmp_path):
    from click.testing import CliRunner
    from air_blackbox.cli import main

    _write(tmp_path, {"agent.ts": "import OpenAI from 'openai';\nconst c = new OpenAI();\n"})
    result = CliRunner().invoke(main, ["comply", "--scan", str(tmp_path), "--no-llm",
                                       "--no-save", "--runs-dir", str(tmp_path / "runs")])
    assert result.exit_code == 0, result.output
    # the banner says `pip install air-blackbox`; no trust-layer advice
    assert not re.search(r"pip install air-[\w-]+-trust", result.output)
    assert "OpenAI Node SDK" in result.output
