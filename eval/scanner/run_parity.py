#!/usr/bin/env python3
"""Cross-language parity for the AIR Blackbox scanner.

Every case in parity_corpus.json is one program written three times, in
Python, TypeScript and JavaScript, by a developer idiomatic in each (camelCase
in JS, the real npm packages, try/catch, JSDoc). The claim under test: the
scanner gives the labelled check the SAME status in all three languages.

The 72 cases of corpus.json are all here, translated, plus cases for the
checks corpus.json does not cover (docstrings, unsafe input, the OAuth and
delegation checks, the US hiring checks, GDPR and the US state-law checks).
Translations were written without access to the scanner's patterns, so they
reflect how people write code, not what the scanner looks for.

It also reports, per language, how often the status agrees with the human
label. Parity is the gate (exit 1 on any mismatch); label agreement is the
accuracy measure, and a miss shared by all three languages is a detection gap
for the check itself, not a language gap.

Usage (from repo root):
  PYTHONPATH=sdk python3 eval/scanner/run_parity.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
try:
    import air_blackbox  # noqa: F401  (an installed build is tested as installed)
except ImportError:
    sys.path.insert(0, os.path.join(REPO, "sdk"))

from air_blackbox.compliance.code_scanner import scan_codebase  # noqa: E402
from air_blackbox.compliance.gdpr_scanner import scan_gdpr  # noqa: E402
from air_blackbox.compliance.us_scanner import scan_us_laws  # noqa: E402

LANGUAGES = ("python", "typescript", "javascript")

#: Checks whose "positive" status is not "pass": the label marks the
#: presence of a problem, which the scanner reports as warn/fail.
POSITIVE_STATUS = {
    "Unsafe input handling": "warn",
    "Illinois HB 3773: ZIP code as proxy": "fail",
}


def statuses(files):
    """Write the files to a temp dir and return {check name: status}."""
    with tempfile.TemporaryDirectory() as d:
        for name, code in files.items():
            path = os.path.join(d, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(code)
        out = {f.name: f.status for f in scan_codebase(d)}
        out.update({f.name: f.status for f in scan_gdpr(d)})
        out.update({f.name: f.status for f in scan_us_laws(d)})
    return out


def run():
    with open(os.path.join(HERE, "parity_corpus.json")) as f:
        corpus = json.load(f)

    mismatches = []
    agree = {lang: 0 for lang in LANGUAGES}
    shared_misses = []
    for case in corpus:
        check = case["check"]
        got = {lang: statuses(case[lang]).get(check, "absent") for lang in LANGUAGES}
        if len(set(got.values())) > 1:
            mismatches.append((case["id"], check, got))
        positive = POSITIVE_STATUS.get(check, "pass")
        for lang in LANGUAGES:
            if (got[lang] == positive) == case["label"]:
                agree[lang] += 1
        if all((got[lang] == positive) != case["label"] for lang in LANGUAGES):
            shared_misses.append((case["id"], check))
    return corpus, mismatches, agree, shared_misses


def main():
    corpus, mismatches, agree, shared_misses = run()
    n = len(corpus)
    checks = len({c["check"] for c in corpus})
    print(f"\nAIR Blackbox scanner - cross-language parity on {n} cases, {checks} checks\n")
    for cid, check, got in mismatches:
        print(f"  MISMATCH {cid}: {check}: {got}")
    print(f"parity: {n - len(mismatches)}/{n} cases give the same status in "
          f"Python, TypeScript and JavaScript")
    for lang in LANGUAGES:
        print(f"label agreement, {lang:<10}: {agree[lang]}/{n} = {agree[lang] / n:.1%}")
    if shared_misses:
        print(f"\n{len(shared_misses)} case(s) missed identically in all three languages "
              "(detection gaps in the check, not language gaps):")
        for cid, check in shared_misses:
            print(f"  {cid}: {check}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
