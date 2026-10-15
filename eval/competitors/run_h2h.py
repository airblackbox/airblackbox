#!/usr/bin/env python3
"""Head-to-head: AIR Blackbox against other open-source EU AI Act scanners.

Every scanner is run on the same programs: the 144 cases of
eval/scanner/parity_corpus.json, each written in Python, TypeScript,
JavaScript, Java and Kotlin, plus each Python case as a Jupyter notebook.
Each case is labelled by hand: a practice (logging, human oversight, consent
handling, ...) is present or absent.

A scanner is only scored on the practices it claims to check. The mapping
from its own check names to corpus practices is MAPPING below, taken from
each tool's documentation and source. Checks of theirs that no corpus case
covers (prohibited practices, documentation files, revocation) are listed in
UNSCORED and not scored at all, for or against anyone.

Two measures:

  practice detection  for each competitor, its mapped checks on every case
                      and language, and AIR on exactly the same cases.
                      Only programs that import an AI SDK are scored (some
                      Python cases are fragments with no imports, which a
                      scanner scoped to AI code rightly skips). A scored
                      sample with no verdict (the tool skipped the file or
                      the language) counts as not correct. Totals over every
                      sample, fragments included, are printed too.
  AI-code recognition how often each tool notices that a program calls an AI
                      SDK at all, per language. Ground truth is the program's
                      import lines (AI_IMPORTS); nothing else.

Usage (from repo root; see README.md for installing the other tools):

  ARKFORGE_PYTHON=/path/to/venv/bin/python \\
  SYSTIMA_COMPLY=/path/to/node_modules/.bin/comply \\
  ASQAV_SCANNER=/path/to/compiled/scanner.js \\
  PYTHONPATH=sdk python3 eval/competitors/run_h2h.py [--json results.json]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "eval", "scanner"))
try:
    import air_blackbox  # noqa: F401
except ImportError:
    sys.path.insert(0, os.path.join(REPO, "sdk"))

from run_parity import POSITIVE_STATUS, as_notebooks, statuses  # noqa: E402
from air_blackbox import __version__ as AIR_VERSION  # noqa: E402
from air_blackbox.compliance.engine import detect_frameworks  # noqa: E402

LANGUAGES = ("python", "notebook", "typescript", "javascript", "java", "kotlin")

TOOLS = {
    "air": "AIR Blackbox",
    "arkforge": "ArkForge eu-ai-act-scanner",
    "systima": "Systima Comply",
    "asqav": "Asqav compliance scanner",
}

#: competitor check -> the corpus practice it claims to detect.
#: Sources: ArkForge server.py/gdpr_module.py, Systima
#: knowledge/eu-ai-act/obligations.json and its art12/art50 checks, Asqav
#: src/scanner.ts and its report's recommendation text.
MAPPING = {
    "arkforge": {
        "content_marking": "CA: AI content transparency",
        "gdpr:consent_mechanism": "GDPR consent management",
        "gdpr:data_deletion": "GDPR right to erasure",
    },
    "systima": {
        "art12 logging": "Application logging",
        "art50 disclosure": ["CO: Consumer AI disclosure", "CA: AI content transparency"],
    },
    "asqav": {
        "auditTrail": "Agent action audit trail",
        "policyEnforcement": ["Agent action boundaries", "Usage limits / budget controls"],
        "humanOversight": "Human-in-the-loop patterns",
        "errorHandling": "LLM call error handling",
    },
}

#: Checks the competitors run that no corpus case exercises, so nobody is
#: scored on them. Listed so the report says what this benchmark does not see.
UNSCORED = {
    "arkforge": ["Articles 9-15 and GDPR documents: tests whether Markdown files "
                 "such as HUMAN_OVERSIGHT.md exist and how complete they are",
                 "GDPR encryption-usage pattern"],
    "systima": ["Article 5 prohibited-practice indicators",
                "Articles 9-14 and 27: declared documentation files and their sections",
                "risk classification from a declared .systima.yml"],
    "asqav": ["Revocation / kill-switch patterns"],
}

#: Languages each tool reads, from its own source: ArkForge's code_extensions
#: (.py .js .ts .java .go .rs .cpp .c), Systima's language filter
#: (python, typescript, javascript), Asqav's `.py` filter.
SUPPORTED = {
    "arkforge": ("python", "typescript", "javascript", "java"),
    "systima": ("python", "typescript", "javascript"),
    "asqav": ("python",),
}

#: Ground truth for "this program calls an AI SDK": module prefixes in its
#: imports. Deliberately plain so anyone can audit it.
AI_IMPORTS = {
    "python": r"^\s*(?:from|import)\s+(openai|anthropic|langchain\w*|langgraph|crewai|autogen\w*|"
              r"llama_index|haystack|google\.generativeai|google\.genai|vertexai|mistralai|cohere|"
              r"litellm|dspy|smolagents|pydantic_ai|semantic_kernel|ollama|groq|transformers)\b",
    "js": r"""(?:from\s+|require\(\s*|import\(\s*)["'](openai|@openai/[\w-]+|@anthropic-ai/[\w-]+|"""
          r"""langchain|@langchain/[\w-]+|ai|@ai-sdk/[\w-]+|@google/genai|@google/generative-ai|"""
          r"""@mistralai/[\w-]+|cohere-ai|ollama|groq-sdk|llamaindex)(?:/[\w./-]*)?["']""",
    "jvm": r"^\s*import\s+(com\.openai|com\.anthropic|dev\.langchain4j|org\.springframework\.ai|ai\.koog|"
           r"com\.google\.genai|com\.google\.cloud\.vertexai|com\.aallam\.openai)\.",
}

_PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
_JS_SPEC = re.compile(r"""(?:from\s+|require\(\s*|import\(\s*)["']([^"'./][^"']*)["']""")
_NODE_BUILTINS = {"fs", "path", "crypto", "http", "https", "url", "os", "util", "events",
                  "stream", "child_process", "assert", "buffer", "zlib", "readline"}


def _manifest(lang, files):
    """The dependency manifest a real project would have, built from the
    imports, so dependency-based checks (Systima) are not starved."""
    code = "\n".join(files.values())
    if lang in ("python", "notebook"):
        if lang == "notebook":
            code = "\n".join("".join(c["source"]) for f in files.values()
                             for c in json.loads(f)["cells"] if c["cell_type"] == "code")
        mods = sorted({(a or b).split(".")[0] for a, b in _PY_IMPORT.findall(code)})
        return {"requirements.txt": "\n".join(m.replace("_", "-") for m in mods) + "\n"}
    if lang in ("typescript", "javascript"):
        deps = {}
        for spec in _JS_SPEC.findall(code):
            if spec.startswith("node:"):
                continue
            parts = spec.split("/")
            name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
            if name not in _NODE_BUILTINS:
                deps[name] = "*"
        return {"package.json": json.dumps({"name": "sample", "version": "0.0.0",
                                            "dependencies": dict(sorted(deps.items()))}, indent=2)}
    return {}


def is_ai_program(lang, files):
    pattern = AI_IMPORTS["python" if lang == "python" else "js" if lang in ("typescript", "javascript") else "jvm"]
    return any(re.search(pattern, code, re.M) for code in files.values())


def materialise(corpus, root):
    """Write every (case, language) program to its own directory."""
    samples = []
    for case in corpus:
        for lang in LANGUAGES:
            files = as_notebooks(case["python"]) if lang == "notebook" else case.get(lang)
            if files is None:
                continue
            d = os.path.join(root, case["id"], lang)
            os.makedirs(d)
            for name, code in {**files, **_manifest(lang, files)}.items():
                with open(os.path.join(d, name), "w") as f:
                    f.write(code)
            # A notebook is judged on the Python it was built from.
            ai = is_ai_program("python" if lang == "notebook" else lang,
                               case["python"] if lang == "notebook" else files)
            samples.append({"id": case["id"], "check": case["check"], "label": case["label"],
                            "lang": lang, "dir": d, "ai": ai})
    return samples


# --- running each tool ----------------------------------------------------

def run_air(samples):
    out = {}
    for s in samples:
        out[s["dir"]] = {"statuses": statuses_of(s["dir"]), "frameworks": detect_frameworks(s["dir"])}
    return out


def statuses_of(d):
    files = {}
    for name in os.listdir(d):
        with open(os.path.join(d, name)) as f:
            files[name] = f.read()
    return statuses(files)


def run_arkforge(samples, python):
    driver = os.path.join(HERE, "drivers", "arkforge_driver.py")
    site = subprocess.run([python, "-c", "import server, os; print(os.path.dirname(server.__file__))"],
                          capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as t:
        manifest, result = os.path.join(t, "m.json"), os.path.join(t, "r.json")
        with open(manifest, "w") as f:
            json.dump([s["dir"] for s in samples], f)
        # cwd=site so its top-level modules (server, gdpr_module) import as
        # its own CLI imports them; telemetry is never called from these classes.
        subprocess.run([python, driver, manifest, result], cwd=site, check=True)
        with open(result) as f:
            return json.load(f)


def run_asqav(samples, scanner_js):
    driver = os.path.join(HERE, "drivers", "asqav_driver.js")
    with tempfile.TemporaryDirectory() as t:
        manifest, result = os.path.join(t, "m.json"), os.path.join(t, "r.json")
        with open(manifest, "w") as f:
            json.dump([s["dir"] for s in samples], f)
        subprocess.run(["node", driver, os.path.abspath(scanner_js), manifest, result], check=True)
        with open(result) as f:
            return json.load(f)


SYSTIMA_CONFIG = """version: "1"
organisation:
  name: "Benchmark"
  eu_presence: true
  operator_role: provider
systems:
  - id: bench
    name: "Benchmark system"
    description: "Benchmark fixture"
    scope:
      paths:
        - "**"
    classification:
      risk_level: high
      annex_iii_category: "4a"
      rationale: "Benchmark: declared high-risk so every obligation check runs"
    regulations:
      - eu_ai_act
"""


def run_systima(samples, comply):
    with tempfile.TemporaryDirectory() as t:
        config = os.path.join(t, "systima.yml")
        with open(config, "w") as f:
            f.write(SYSTIMA_CONFIG)

        def one(d):
            p = subprocess.run([comply, "scan", f"--path={d}", f"--config={config}",
                                "--output=json", "--fail-on=none"],
                               capture_output=True, text=True, timeout=300)
            try:
                scan = json.loads(p.stdout)["scan"]
            except (ValueError, KeyError):
                return d, {"error": (p.stdout + p.stderr)[-500:]}
            results = [r for sy in scan["systems"] for r in sy["complianceResults"]]
            return d, {"detections": scan["summary"]["totalDetections"],
                       "results": [{"article": r["articleId"], "status": r["status"],
                                    "title": r["title"]} for r in results]}

        with ThreadPoolExecutor(max_workers=8) as pool:
            return dict(pool.map(one, [s["dir"] for s in samples]))


# --- verdicts -------------------------------------------------------------

def _listify(v):
    return v if isinstance(v, list) else [v]


def practices_for(tool):
    out = {}
    for check, practices in MAPPING[tool].items():
        for p in _listify(practices):
            out.setdefault(p, []).append(check)
    return out


def verdict(tool, check, raw, sample):
    """True = the tool says the practice is present, False = absent,
    None = no verdict on this program."""
    if raw is None or "error" in raw:
        return None
    if tool == "air":
        status = raw["statuses"].get(sample["check"], "absent")
        if status == "absent":
            return None
        return status == POSITIVE_STATUS.get(sample["check"], "pass")
    if tool == "arkforge":
        if check == "content_marking":
            return raw["content_marking"]
        return check.split(":", 1)[1] in raw["gdpr_patterns"]
    if tool == "systima":
        article = {"art12 logging": "art12", "art50 disclosure": "art50"}[check]
        rows = [r for r in raw["results"] if r["article"] == article and r["status"] != "skipped"]
        if not rows:
            return None
        if article == "art12":  # pass = its own audit-log package, warning = other structured logging
            return rows[0]["status"] in ("pass", "warning")
        return rows[0]["status"] == "pass"
    if tool == "asqav":
        if not raw["files"]:
            return None  # it only reads .py files that import an agent framework
        return all(f[check] for f in raw["files"])  # its report: PASS only if every file passes
    raise ValueError(tool)


def recognised(tool, raw):
    if raw is None or "error" in raw:
        return False
    return bool({"air": lambda r: r["frameworks"], "arkforge": lambda r: r["ai_files"],
                 "systima": lambda r: r["detections"], "asqav": lambda r: r["files"]}[tool](raw))


def score(samples, raw):
    report = {"head_to_head": {}, "recognition": {}}
    for tool in ("arkforge", "systima", "asqav"):
        by_practice = practices_for(tool)
        rows = []
        for s in samples:
            if s["check"] not in by_practice:
                continue
            theirs = [verdict(tool, c, raw[tool].get(s["dir"]), s) for c in by_practice[s["check"]]]
            their_v = None if all(v is None for v in theirs) else any(v for v in theirs if v is not None)
            air_v = verdict("air", None, raw["air"].get(s["dir"]), s)
            rows.append({"id": s["id"], "check": s["check"], "lang": s["lang"], "label": s["label"],
                         "ai": s["ai"], tool: their_v, "air": air_v})
        scored = [r for r in rows if r["ai"]]
        per_lang = {}
        for lang in LANGUAGES:
            lr = [r for r in scored if r["lang"] == lang]
            if lr:
                per_lang[lang] = {
                    "n": len(lr),
                    tool: sum(r[tool] == r["label"] for r in lr),
                    tool + "_no_verdict": sum(r[tool] is None for r in lr),
                    "air": sum(r["air"] == r["label"] for r in lr),
                    "air_no_verdict": sum(r["air"] is None for r in lr),
                }
        report["head_to_head"][tool] = {
            "practices": sorted(by_practice),
            "n": len(scored),
            tool: sum(r[tool] == r["label"] for r in scored),
            "air": sum(r["air"] == r["label"] for r in scored),
            "all_samples": {"n": len(rows), tool: sum(r[tool] == r["label"] for r in rows),
                            "air": sum(r["air"] == r["label"] for r in rows)},
            "supported_languages": {
                "languages": list(SUPPORTED[tool]),
                "n": sum(r["lang"] in SUPPORTED[tool] for r in scored),
                tool: sum(r[tool] == r["label"] for r in scored if r["lang"] in SUPPORTED[tool]),
                "air": sum(r["air"] == r["label"] for r in scored if r["lang"] in SUPPORTED[tool])},
            "per_language": per_lang,
            "rows": rows,
        }
    for tool in TOOLS:
        per_lang = {}
        for lang in LANGUAGES:
            ai = [s for s in samples if s["lang"] == lang and s["ai"]]
            if ai:
                per_lang[lang] = {"n": len(ai), "recognised": sum(recognised(tool, raw[tool].get(s["dir"])) for s in ai)}
        report["recognition"][tool] = per_lang
    report["recognition_rows"] = [
        {"id": s["id"], "lang": s["lang"], **{t: recognised(t, raw[t].get(s["dir"])) for t in TOOLS}}
        for s in samples if s["ai"]]
    report["all_practices"] = len({s["check"] for s in samples})
    return report


def pct(a, b):
    return f"{a}/{b} ({a / b:.0%})" if b else "n/a"


def print_report(rep, versions):
    print("\nHead-to-head on the shared corpus\n")
    for tool, v in versions.items():
        print(f"  {TOOLS[tool]:<28} {v}")
    print("\n1. Practice detection, scored only on the practices each competitor claims\n")
    for tool, h in rep["head_to_head"].items():
        print(f"{TOOLS[tool]}: {len(h['practices'])} of {rep['all_practices']} corpus practices mapped")
        for p in h["practices"]:
            print(f"    - {p}")
        print(f"  {'language':<11} {'samples':>7}  {TOOLS[tool].split()[0]:>18}  {'AIR Blackbox':>18}")
        for lang, r in h["per_language"].items():
            print(f"  {lang:<11} {r['n']:>7}  {pct(r[tool], r['n']):>18}  {pct(r['air'], r['n']):>18}")
        print(f"  {'all':<11} {h['n']:>7}  {pct(h[tool], h['n']):>18}  {pct(h['air'], h['n']):>18}")
        s = h["supported_languages"]
        print(f"  {'its langs':<11} {s['n']:>7}  {pct(s[tool], s['n']):>18}  {pct(s['air'], s['n']):>18}"
              f"   ({', '.join(s['languages'])})")
        a = h["all_samples"]
        print(f"  {'(+ fragments)':<11} {a['n']:>5}  {pct(a[tool], a['n']):>18}  {pct(a['air'], a['n']):>18}\n")
    print("2. AI-code recognition: programs that import an AI SDK, recognised as AI code\n")
    langs = [lang for lang in LANGUAGES if lang in rep["recognition"]["air"]]
    print("  " + f"{'tool':<28}" + "".join(f"{lang:>12}" for lang in langs))
    for tool in TOOLS:
        cells = []
        for lang in langs:
            r = rep["recognition"][tool].get(lang)
            cells.append(f"{r['recognised']}/{r['n']}" if r else "-")
        print("  " + f"{TOOLS[tool]:<28}" + "".join(f"{c:>12}" for c in cells))
    print()


def versions(env):
    v = {"air": AIR_VERSION}
    v["arkforge"] = subprocess.run([env["ARKFORGE_PYTHON"], "-m", "pip", "show", "eu-ai-act-scanner"],
                                   capture_output=True, text=True).stdout.split("Version: ")[1].split()[0]
    v["systima"] = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(env["SYSTIMA_COMPLY"]))),
                                               "package.json")))["version"]
    v["asqav"] = env.get("ASQAV_REF", "unknown commit")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full results (every verdict) here")
    args = ap.parse_args()
    env = {k: os.environ.get(k) for k in ("ARKFORGE_PYTHON", "SYSTIMA_COMPLY", "ASQAV_SCANNER", "ASQAV_REF")}
    missing = [k for k in ("ARKFORGE_PYTHON", "SYSTIMA_COMPLY", "ASQAV_SCANNER") if not env[k]]
    if missing:
        sys.exit(f"set {', '.join(missing)} (see eval/competitors/README.md)")

    with open(os.path.join(REPO, "eval", "scanner", "parity_corpus.json")) as f:
        corpus = json.load(f)
    with tempfile.TemporaryDirectory() as root:
        samples = materialise(corpus, root)
        raw = {"air": run_air(samples),
               "arkforge": run_arkforge(samples, env["ARKFORGE_PYTHON"]),
               "systima": run_systima(samples, env["SYSTIMA_COMPLY"]),
               "asqav": run_asqav(samples, env["ASQAV_SCANNER"])}
        errors = {t: [d for d, r in raw[t].items() if isinstance(r, dict) and "error" in r] for t in raw}
        rep = score(samples, raw)
        for s in samples:  # paths are temporary; keep ids in the saved results
            s.pop("dir")
    vers = versions(env)
    print_report(rep, vers)
    for t, errs in errors.items():
        if errs:
            print(f"  {TOOLS[t]}: {len(errs)} sample(s) errored and count as no verdict")
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"versions": vers, "report": rep, "samples": samples,
                       "mapping": MAPPING, "unscored": UNSCORED}, f, indent=1)


if __name__ == "__main__":
    main()
