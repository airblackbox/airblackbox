"""Scan a pasted piece of code, in any supported language.

The website console and the MCP server's `scan_code` tool receive code as a
string, usually without a filename. They used to run their own copies of the
scanner, which drifted from this one (different checks, Python only). This
module gives them the real scanner: the code is written to a temporary file
with the right extension and goes through exactly the path a project scan
does, so a snippet gets the result the same code gets in a repository.

    from air_blackbox.compliance.snippet import scan_snippet
    result = scan_snippet(code)                      # language detected
    result = scan_snippet(code, language="kotlin")   # or stated
"""

import json
import os
import re
import tempfile
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from air_blackbox.compliance.sources import (
    ALL_LANGUAGES,
    JAVA,
    JAVASCRIPT,
    KOTLIN,
    PYTHON,
    TYPESCRIPT,
    language_of,
)

#: Accepted names for `language`, mapped to the scanner's language ids.
LANGUAGE_ALIASES = {
    "python": PYTHON, "py": PYTHON,
    "notebook": "notebook", "ipynb": "notebook", "jupyter": "notebook",
    "typescript": TYPESCRIPT, "ts": TYPESCRIPT, "tsx": TYPESCRIPT,
    "javascript": JAVASCRIPT, "js": JAVASCRIPT, "jsx": JAVASCRIPT, "node": JAVASCRIPT,
    "java": JAVA,
    "kotlin": KOTLIN, "kt": KOTLIN,
}

_DEFAULT_FILENAME = {
    PYTHON: "snippet.py", "notebook": "snippet.ipynb", TYPESCRIPT: "snippet.ts",
    JAVASCRIPT: "snippet.js", JAVA: "Snippet.java", KOTLIN: "Snippet.kt",
}

# Signals per language, as (pattern, weight). Only syntax a language cannot
# share with the others scores high; ambiguous tokens score low.
_SIGNALS: Dict[str, List[Tuple[str, int]]] = {
    PYTHON: [
        (r"^\s*def \w+\s*\(.*\)\s*(?:->\s*[^:]+)?:\s*$", 5),
        (r"^\s*class \w+(?:\([^)]*\))?:\s*$", 5),
        (r"^\s*from [\w.]+ import [\w*, ()]+$", 5),
        (r"^\s*import [\w.]+(?: as \w+)?(?:, [\w.]+)*\s*$", 2),
        (r"^\s*(?:if|elif|else|for|while|try|except|with)\b[^{;]*:\s*$", 3),
        (r"\bself\.\w+", 2), (r"^\s*@\w+(?:\.\w+)*\s*$", 1), (r"\bNone\b|\bTrue\b|\bFalse\b", 1),
        (r'^\s*"""', 3), (r"\bf\"[^\"]*\{", 2), (r"^\s*print\(", 1),
    ],
    TYPESCRIPT: [
        (r"^\s*(?:export\s+)?(?:interface|type)\s+\w+(?:<[^>]*>)?\s*(?:=|\{|extends)", 6),
        (r"\w\??:\s*(?:string|number|boolean|unknown|any|void|never)\b", 5),
        (r"\bimport\s+type\b|\bas\s+const\b|\bsatisfies\b", 6),
        (r"\):\s*Promise<", 6), (r"\bprivate\s+readonly\b|\bpublic\s+readonly\b", 4),
        # return / parameter annotations on a method or function: `step(): number {`
        (r"^\s*(?:(?:export|async|public|private|protected|static)\s+)*(?:function\s+)?\w+\s*"
         r"(?:<[^>]*>)?\([^)]*\)\s*:\s*[\w<>\[\]|, .]+\s*\{\s*$", 4),
        (r"\(\s*\w+\??:\s*[\w{\[][^)]*\)\s*(?::\s*[^=]+)?=>", 4),
        (r"^\s*declare\s+(?:const|function|class|module)\b", 6),
        # annotated parameter in a function declaration: `function run(p: Foo[])`
        (r"\bfunction\s*\*?\s*\w*\s*(?:<[^>]*>)?\([^)]*?\b\w+\??:\s*[A-Za-z_{\[(]", 5),
    ],
    JAVASCRIPT: [
        (r"^\s*(?:const|let|var)\s+\w+\s*=", 3), (r"=>", 2),
        (r"\brequire\(\s*['\"]", 4), (r"^\s*import\s+.*\s+from\s+['\"]", 4),
        (r"^\s*export\s+(?:default|const|async|function|class)\b", 4),
        # method with untyped parameters: `act(obs) {` (Java/Kotlin name types)
        (r"^\s*(?:async\s+)?\w+\((?:\w+(?:\s*,\s*\w+)*)?\)\s*\{\s*$", 3),
        (r"\bfunction\s*\w*\s*\(", 2), (r"\bconsole\.\w+\(", 2), (r"===|!==", 3),
        (r"\bawait\s+\w", 1), (r"`[^`]*\$\{", 2),
    ],
    JAVA: [
        (r"^\s*(?:public|private|protected)\s+(?:static\s+|final\s+|abstract\s+)*"
         r"(?:class|interface|enum|record)\s+\w+", 6),
        (r"^\s*(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\],? ]+\s+\w+\s*\([^)]*\)"
         r"\s*(?:throws [\w., ]+)?\s*\{", 6),
        (r"^\s*import\s+(?:static\s+)?[\w.]+(?:\.\*)?;\s*$", 5),
        (r"^\s*package\s+[\w.]+;\s*$", 5), (r"\bSystem\.out\.print", 5),
        (r"\bnew\s+\w+(?:<[^>]*>)?\(", 1), (r";\s*$", 1), (r"@Override\b", 2),
    ],
    KOTLIN: [
        (r"^\s*(?:(?:private|internal|public|override|suspend|inline|open)\s+)*fun\s+"
         r"(?:<[^>]+>\s+)?[\w.]+\s*\(", 6),
        (r"^\s*(?:(?:private|internal|public|const)\s+)*val\s+\w+\s*(?::[^=]+)?=", 4),
        (r"\{\s*\w+(?:\s*,\s*\w+)*\s*->", 3),
        (r"^\s*data\s+class\s+\w+", 6), (r"^\s*(?:companion\s+)?object\s+\w*\s*\{", 4),
        (r"^\s*import\s+[\w.]+(?:\.\*)?\s*$", 2), (r"^\s*package\s+[\w.]+\s*$", 4),
        (r"\bprintln\(", 2), (r"\bsuspend\b|\blistOf\(|\bmapOf\(|\?\.let\b|\?:", 3),
        (r"\"[^\"\n]*\$\{?\w", 1),
    ],
}


def guess_language(code: str, filename: Optional[str] = None) -> str:
    """Best guess at the language of a snippet: a filename extension wins,
    then a Jupyter notebook's JSON, then syntax that only one language has.
    Returns one of python, notebook, typescript, javascript, java, kotlin."""
    if filename:
        if filename.endswith(".ipynb"):
            return "notebook"
        lang = language_of(filename)
        if lang:
            return lang
    stripped = code.lstrip()
    if stripped.startswith("{") and '"cells"' in code:
        try:
            if isinstance(json.loads(code), dict):
                return "notebook"
        except ValueError:
            pass
    # Score code, not comments: JSDoc carries TypeScript-looking types
    # (`@param {(x: any) => void}`) in plain JavaScript.
    body = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    body = re.sub(r"^\s*//.*$", "", body, flags=re.MULTILINE)
    scores = {}
    for lang, signals in _SIGNALS.items():
        scores[lang] = sum(weight for pattern, weight in signals
                           if re.search(pattern, body, re.MULTILINE))
    # TypeScript is a superset of JavaScript: JS signals count for it too,
    # and JS only wins when nothing TypeScript-specific is present.
    scores[TYPESCRIPT] += scores[JAVASCRIPT] if scores[TYPESCRIPT] else 0
    best = max(scores, key=lambda lang: (scores[lang], lang == PYTHON))
    return best if scores[best] > 0 else PYTHON


def _normalise_language(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    key = str(language).strip().lower()
    if key not in LANGUAGE_ALIASES:
        raise ValueError(f"unsupported language {language!r}; expected one of "
                         + ", ".join(sorted(set(LANGUAGE_ALIASES.values()))))
    return LANGUAGE_ALIASES[key]


def scan_snippet(code: str, language: Optional[str] = None,
                 filename: Optional[str] = None) -> dict:
    """Run every scanner over one piece of code, as a one-file project.

    Returns a JSON-serialisable dict:
      language        the language scanned (stated, or detected)
      language_source "stated", "filename" or "detected"
      frameworks      AI frameworks found in the imports
      findings        code-scanner findings (EU AI Act articles, OAuth and
                      delegation, US hiring when the code is hiring code)
      gdpr            GDPR findings
      us              US state-law findings
    Findings are the scanner's own dataclasses as dicts: the same names,
    statuses and evidence a project scan produces.
    """
    from air_blackbox.compliance.code_scanner import scan_codebase
    from air_blackbox.compliance.engine import detect_frameworks
    from air_blackbox.compliance.gdpr_scanner import scan_gdpr
    from air_blackbox.compliance.us_scanner import scan_us_laws

    stated = _normalise_language(language)
    from_name = None
    if filename:
        from_name = "notebook" if filename.endswith(".ipynb") else language_of(filename)
    if stated:
        lang, source = stated, "stated"
    elif from_name:
        lang, source = from_name, "filename"
    else:
        lang, source = guess_language(code), "detected"

    name = _DEFAULT_FILENAME[lang]
    if filename and from_name == lang:
        name = os.path.basename(filename)  # keeps Java's class name and test naming

    with tempfile.TemporaryDirectory(prefix="air-snippet-") as root:
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        result = {
            "language": lang,
            "language_source": source,
            "frameworks": detect_frameworks(root),
            "findings": [asdict(f) for f in scan_codebase(root)],
            "gdpr": [asdict(f) for f in scan_gdpr(root)],
            "us": [asdict(f) for f in scan_us_laws(root)],
        }
    for group in ("findings", "gdpr", "us"):
        for f in result[group]:
            f.pop("files", None)  # temp paths mean nothing to the caller
    return result
