"""Which files the scanners read, and in which language.

The checks are text patterns written against Python naming (``max_retries``,
``require_approval``, ``detect_pii``). TypeScript, JavaScript, Java and Kotlin
express the same practices in camelCase (``maxRetries``, ``requireApproval``,
``detectPii``), so every non-Python file also carries a snake_case view of its
text, and a pattern counts as found if it matches either. Python files get no
view, so their results are exactly what they were before other languages
existed.

Jupyter notebooks are Python: their code cells are read as one Python file
(IPython ``%magic`` and ``!shell`` lines commented out), so a notebook gets
the result the same code would get in a ``.py`` file. Notebooks whose kernel
is not Python (R, Julia...) are skipped.

Adding a language means: its extensions in ``LANGUAGE_BY_EXTENSION``, its
test-file and generated-file conventions below, the syntax-level adapters in
``code_scanner`` (try/catch, doc comments, type annotations, logging
libraries), and a translated copy of the labelled corpus proving parity.
"""

import functools
import json
import os
import re
from typing import Dict, Iterable, List, Optional

PYTHON = "python"
TYPESCRIPT = "typescript"
JAVASCRIPT = "javascript"
JAVA = "java"
KOTLIN = "kotlin"

#: Display order, and the order languages are reported in.
ALL_LANGUAGES = (PYTHON, TYPESCRIPT, JAVASCRIPT, JAVA, KOTLIN)

LANGUAGE_BY_EXTENSION = {
    ".py": PYTHON, ".ipynb": PYTHON,
    ".ts": TYPESCRIPT, ".tsx": TYPESCRIPT, ".mts": TYPESCRIPT, ".cts": TYPESCRIPT,
    ".js": JAVASCRIPT, ".jsx": JAVASCRIPT, ".mjs": JAVASCRIPT, ".cjs": JAVASCRIPT,
    ".java": JAVA,
    ".kt": KOTLIN, ".kts": KOTLIN,
}

#: Languages whose files get the JS syntax adapters.
JS_FAMILY = (TYPESCRIPT, JAVASCRIPT)
#: JVM languages share Java's library adapters (LangChain4j, Spring AI, SLF4J...).
JVM_FAMILY = (JAVA, KOTLIN)
#: Languages whose files get the snake_case view (everything but Python).
CAMEL_CASE_LANGUAGES = (TYPESCRIPT, JAVASCRIPT, JAVA, KOTLIN)

# Compiled, bundled or declaration-only output: not code anyone wrote, and a
# minified bundle would otherwise satisfy every check at once.
_JS_GENERATED_SUFFIXES = (".d.ts", ".d.mts", ".d.cts", ".min.js", ".min.mjs",
                          ".min.cjs", ".bundle.js", ".chunk.js")
# Tool configuration (vite.config.ts, jest.config.js, .eslintrc.js).
_JS_CONFIG_NAME = re.compile(r"\.config\.[cm]?[jt]s$|^\.[\w-]+rc\.[cm]?js$")
# Build output and caches of JS toolchains. Only applied to JS-family files,
# so a Python package in a directory of the same name is unaffected.
_JS_GENERATED_DIRS = {
    ".next", ".nuxt", ".svelte-kit", ".turbo", ".vercel", ".output",
    ".expo", ".docusaurus", ".angular", ".wrangler", ".parcel-cache",
    ".yarn", ".pnpm-store", "bower_components", "jspm_packages",
    "coverage", "out", "storybook-static",
}
_JS_TEST_DIRS = {"__tests__", "__mocks__", "__fixtures__", "e2e", "cypress"}
_JS_TEST_NAME = re.compile(r"\.(?:test|spec|e2e|stories)\.[cm]?[jt]sx?$")

# Maven/Gradle output and generated sources. Java-only, like the JS list.
_JAVA_GENERATED_DIRS = {"target", ".gradle", ".mvn", "generated", "generated-sources",
                        "generated-test-sources", "out", "bin", ".kotlin"}
_JAVA_NOT_SOURCE = {"module-info.java", "package-info.java"}
# JUnit/TestNG naming; src/test/... is already a test directory.
_JAVA_TEST_NAME = re.compile(r"(?:Tests?|IT|ITCase|TestCase)\.(?:java|kt)$|^Test\w*\.(?:java|kt)$")


def language_of(path: str) -> Optional[str]:
    """Return the language of a source file, or None if it is not one we scan."""
    name = os.path.basename(path)
    # Case-sensitive on purpose: the scanners have always matched ".py"
    # exactly, and Python results must not move.
    lang = LANGUAGE_BY_EXTENSION.get(os.path.splitext(name)[1])
    if lang in JS_FAMILY:
        lower = name.lower()
        if lower.endswith(_JS_GENERATED_SUFFIXES) or _JS_CONFIG_NAME.search(lower):
            return None
    if lang == JAVA and name in _JAVA_NOT_SOURCE:
        return None
    if lang == KOTLIN and name.endswith(".gradle.kts"):
        return None  # build script, not application code
    return lang


def is_notebook(path: str) -> bool:
    return path.endswith(".ipynb")


def is_scannable(path: str, scan_root: str = "") -> bool:
    """True if ``path`` is a source file the scanners should read.

    ``scan_root`` lets build-output directories of one toolchain be excluded
    without affecting other languages' files that happen to share the path.
    Notebooks under .ipynb_checkpoints are autosave copies and skipped.
    """
    lang = language_of(path)
    if lang is None:
        return False
    rel = os.path.relpath(path, scan_root) if scan_root else path
    parts = rel.replace("\\", "/").split("/")[:-1]
    if lang in JS_FAMILY and any(p in _JS_GENERATED_DIRS for p in parts):
        return False
    if lang in JVM_FAMILY and any(p in _JAVA_GENERATED_DIRS for p in parts):
        return False
    if is_notebook(path) and ".ipynb_checkpoints" in parts:
        return False
    return True


def is_js_test_file(rel_path: str) -> bool:
    """JS/TS test conventions: *.test.ts, *.spec.js, __tests__/, e2e/ ..."""
    parts = rel_path.replace("\\", "/").split("/")
    if any(p in _JS_TEST_DIRS for p in parts[:-1]):
        return True
    return bool(_JS_TEST_NAME.search(parts[-1].lower()))


def is_java_test_file(rel_path: str) -> bool:
    """JUnit/TestNG naming (Java and Kotlin): FooTest.java, FooTests.kt, FooIT.java."""
    return bool(_JAVA_TEST_NAME.search(os.path.basename(rel_path)))


# ── snake_case view ──────────────────────────────────────────────────────

_ACRONYM_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_KEBAB = re.compile(r"(?<=[A-Za-z0-9])-(?=[A-Za-z])")


def snake_view(text: str) -> str:
    """camelCase / PascalCase / kebab-case -> snake_case, same line structure.

    ``requireApproval`` -> ``require_approval``, ``detectPII`` ->
    ``detect_pii``, ``PIIRedactor`` -> ``pii_redactor``, ``rate-limiter`` ->
    ``rate_limiter``. Newlines are untouched, so line-based logic still lines
    up with the original.
    """
    out = _ACRONYM_BOUNDARY.sub(r"\1_\2", text)
    out = _CAMEL_BOUNDARY.sub(r"\1_\2", out)
    out = _KEBAB.sub("_", out)
    return out.lower()


class Source(str):
    """File text that also knows its language and, for JS-family files, its
    snake_case view. Behaves as the original string everywhere else."""

    language: str
    alt: Optional[str]
    lowered: Optional[str]

    def __new__(cls, text: str, language: str):
        obj = super().__new__(cls, text)
        obj.language = language
        camel = language in CAMEL_CASE_LANGUAGES
        obj.alt = snake_view(text) if camel else None
        obj.lowered = text.lower() if camel else None
        return obj


@functools.lru_cache(maxsize=1024)
def _lowercase_pattern(pattern: str) -> "re.Pattern":
    """Lowercase a pattern's literals, leaving escapes (\\S, \\W, \\B...) alone.

    On lowercased text this matches what the original pattern matches with
    re.IGNORECASE, for ASCII text, at a fraction of the cost (case-insensitive
    alternations defeat the regex engine's fast paths). Used for TS/JS files
    only; Python files keep the exact original call.
    """
    out, i = [], 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\" and i + 1 < len(pattern):
            out.append(pattern[i:i + 2])
            i += 2
            continue
        out.append(ch.lower())
        i += 1
    return re.compile("".join(out))


def has(pattern: str, content: str, flags: int = 0, js: Optional[str] = None,
        java: Optional[str] = None, kotlin: Optional[str] = None) -> bool:
    """re.search over a file, as the checks use it.

    Python files (and notebooks): exactly ``re.search(pattern, content, flags)``.
    Other languages: the pattern may also match the snake_case view, and
    ``js`` / ``java`` / ``kotlin`` is an extra pattern for idioms that only
    exist there, searched in both texts. Kotlin also gets the ``java``
    patterns: it uses the same JVM libraries.
    """
    alt = getattr(content, "alt", None)
    if alt is None:
        return bool(re.search(pattern, content, flags))
    if content.language == JAVA:
        js = java
    elif content.language == KOTLIN:
        js = "|".join(f"(?:{p})" for p in (java, kotlin) if p) or None
    elif content.language not in JS_FAMILY:
        js = None
    if flags & re.IGNORECASE and not flags & ~(re.IGNORECASE | re.DOTALL):
        rest = flags & re.DOTALL
        texts = (content.lowered, alt)  # both already lowercase
        pats = [_lowercase_pattern(pattern if not rest else f"(?s:{pattern})")]
        if js:
            pats.append(_lowercase_pattern(js if not rest else f"(?s:{js})"))
        return any(p.search(t) for p in pats for t in texts)
    if re.search(pattern, content, flags) or re.search(pattern, alt, flags):
        return True
    return bool(js) and bool(re.search(js, content, flags) or re.search(js, alt, flags))


def is_js(content: str) -> bool:
    return getattr(content, "language", PYTHON) in JS_FAMILY


def notebook_code(raw: str) -> Optional[str]:
    """The code cells of a Jupyter notebook as one Python source, or None if
    it is not a readable notebook or its kernel is not Python.

    Cells are joined with a newline, so code keeps the line structure it has
    in the notebook. IPython-only lines (``%pip install x``, ``!ls``) and
    whole ``%%cell`` magics are commented out rather than dropped, which keeps
    line numbers stable and leaves the text visible, as a comment in a .py
    file would be.
    """
    try:
        nb = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(nb, dict):
        return None
    meta = nb.get("metadata") or {}
    kernel = ((meta.get("kernelspec") or {}).get("language")
              or (meta.get("language_info") or {}).get("name") or "python")
    if str(kernel).lower() != "python":
        return None
    cells = nb.get("cells")
    if cells is None:  # nbformat 3
        cells = [c for ws in nb.get("worksheets") or [] for c in ws.get("cells") or []]
    parts = []
    for cell in cells or []:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        src = cell.get("source", cell.get("input", ""))
        if isinstance(src, list):
            src = "".join(src)
        lines = str(src).split("\n")
        if lines and lines[0].lstrip().startswith("%%"):
            lines = ["# " + line for line in lines]
        else:
            lines = ["# " + line if line.lstrip().startswith(("%", "!")) else line
                     for line in lines]
        parts.append("\n".join(lines))
    return "\n".join(parts) + ("\n" if parts else "")


def read_text(path: str, limit: Optional[int] = None) -> Optional[str]:
    """A source file's text as the scanners see it (a notebook's code cells),
    truncated to ``limit`` characters; None if unreadable or not scannable."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read() if (limit is None or is_notebook(path)) else f.read(limit)
    except Exception:
        return None
    if is_notebook(path):
        code = notebook_code(raw)
        if code is None:
            return None
        return code[:limit] if limit else code
    return raw


def read_sources(paths: Iterable[str], limit: Optional[int] = None) -> Dict[str, Source]:
    """Read files into {path: Source}; unreadable files are skipped."""
    out: Dict[str, Source] = {}
    for fp in paths:
        text = read_text(fp, limit)
        if text is None:
            continue
        out[fp] = Source(text, language_of(fp) or PYTHON)
    return out


def languages_in(file_contents: Dict[str, str]) -> List[str]:
    """Distinct languages present, Python first, in a stable order."""
    seen = {getattr(c, "language", PYTHON) for c in file_contents.values()}
    return [lang for lang in ALL_LANGUAGES if lang in seen]


def project_languages(scan_path: str) -> List[str]:
    """Languages of the scannable files under ``scan_path`` (cheap walk)."""
    from air_blackbox.compliance.code_scanner import _find_source_files
    seen = {language_of(p) for p in _find_source_files(scan_path)}
    return [lang for lang in ALL_LANGUAGES if lang in seen]
