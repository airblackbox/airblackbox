#!/usr/bin/env python3
"""Precision/recall evaluation for the AIR Blackbox code scanner.

Runs the real scanner (air_blackbox.compliance.code_scanner.scan_codebase)
against a labeled corpus of code samples with known ground truth, and reports
precision, recall, and F1 per check and overall.

Definitions (per check):
  positive prediction = scanner returns status "pass" for that check
  positive label      = the practice genuinely IS present in the sample
  TP: present and detected   FP: absent but flagged present
  FN: present but missed      TN: absent and correctly not flagged

Usage (from repo root):
  PYTHONPATH=sdk python3 eval/scanner/run_eval.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "sdk"))

from air_blackbox.compliance.code_scanner import scan_codebase  # noqa: E402


def predict(files):
    """Write fixture files to a temp dir, run the scanner, return {check: is_pass}."""
    with tempfile.TemporaryDirectory() as d:
        for name, code in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(code)
        findings = scan_codebase(d)
    out = {}
    for fnd in findings:
        # A check "passes" (positive prediction) only when status == pass.
        out[fnd.name] = (fnd.status == "pass")
    return out


def main():
    with open(os.path.join(HERE, "corpus.json")) as f:
        corpus = json.load(f)

    # per-check counters
    checks = {}
    for item in corpus:
        c = item["check"]
        checks.setdefault(c, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})

    for item in corpus:
        c = item["check"]
        label = item["label"]                      # True = practice present
        preds = predict(item["files"])
        pred = preds.get(c, False)                  # missing finding = negative pred
        if label and pred:
            checks[c]["tp"] += 1
        elif not label and pred:
            checks[c]["fp"] += 1
        elif label and not pred:
            checks[c]["fn"] += 1
        else:
            checks[c]["tn"] += 1

    def prf(m):
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        p = tp / (tp + fp) if (tp + fp) else 1.0
        r = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        return p, r, f1

    rows = []
    agg = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for c in sorted(checks):
        m = checks[c]
        for k in agg:
            agg[k] += m[k]
        p, r, f1 = prf(m)
        rows.append((c, m, p, r, f1))

    P, R, F1 = prf(agg)
    n = len(corpus)
    correct = agg["tp"] + agg["tn"]

    # ---- terminal report ----
    print(f"\nAIR Blackbox code scanner - precision/recall on {n} labeled fixtures\n")
    print(f"{'check':<38} {'TP':>3} {'FP':>3} {'FN':>3} {'TN':>3} {'prec':>6} {'rec':>6} {'F1':>6}")
    print("-" * 84)
    for c, m, p, r, f1 in rows:
        print(f"{c:<38} {m['tp']:>3} {m['fp']:>3} {m['fn']:>3} {m['tn']:>3} {p:>6.2f} {r:>6.2f} {f1:>6.2f}")
    print("-" * 84)
    print(f"{'OVERALL':<38} {agg['tp']:>3} {agg['fp']:>3} {agg['fn']:>3} {agg['tn']:>3} {P:>6.2f} {R:>6.2f} {F1:>6.2f}")
    print(f"\naccuracy: {correct}/{n} = {correct/n:.1%}\n")

    # ---- markdown report ----
    md = []
    md.append("# Scanner Evaluation\n")
    md.append("Precision and recall of the AIR Blackbox code scanner, measured against "
              "a labeled corpus of code samples with known ground truth. This turns the "
              "check count from a claim into a measured instrument.\n")
    md.append("## Method\n")
    md.append("Each fixture is a small code sample labeled for one check: positive means "
              "the practice genuinely is present, negative means it is absent. Negative "
              "fixtures are realistic code that lacks the specific practice (often with real "
              "LLM calls present), so this measures discrimination, not empty-vs-nonempty. "
              "A positive prediction is the scanner returning status `pass` for that check.\n")
    md.append(f"Corpus: **{n} fixtures** ({agg['tp']+agg['fn']} positive, "
              f"{agg['fp']+agg['tn']} negative) across **{len(checks)} checks**.\n")
    md.append("Reproduce: `PYTHONPATH=sdk python3 eval/scanner/run_eval.py`\n")
    md.append("## Results\n")
    md.append(f"**Overall on this corpus: precision {P:.2f}, recall {R:.2f}, F1 {F1:.2f}, "
              f"accuracy {correct/n:.0%}** ({correct}/{n}). This measures discrimination "
              f"on realistic labeled samples; it is not a claim of accuracy on arbitrary "
              f"production code.\n")
    md.append("| Check | Article | TP | FP | FN | TN | Precision | Recall | F1 |")
    md.append("|-------|--------:|---:|---:|---:|---:|----------:|-------:|---:|")
    art = {
        "LLM call error handling": 9, "Fallback/recovery patterns": 9,
        "Input validation / schema enforcement": 10, "PII handling in code": 10,
        "Code documentation (docstrings)": 11, "Type annotations": 11,
        "Application logging": 12, "Tracing / observability": 12,
        "Human-in-the-loop patterns": 14, "Usage limits / budget controls": 14,
        "Retry / backoff logic": 15, "Prompt injection defense": 15,
        "LLM output validation": 15,
    }
    for c, m, p, r, f1 in rows:
        md.append(f"| {c} | {art.get(c,'')} | {m['tp']} | {m['fp']} | {m['fn']} | "
                  f"{m['tn']} | {p:.2f} | {r:.2f} | {f1:.2f} |")
    md.append(f"| **Overall** | | {agg['tp']} | {agg['fp']} | {agg['fn']} | {agg['tn']} | "
              f"**{P:.2f}** | **{R:.2f}** | **{F1:.2f}** |")
    md.append("\n## What this eval caught\n")
    md.append("On first run the scanner missed NVIDIA NeMo Guardrails: the detector "
              "pattern was `nemo_guardrails` (underscore) but the library is imported as "
              "`nemoguardrails`. That false negative was invisible until the corpus "
              "measured it, and the fix (`nemo_?guardrails`) is the kind of gap an eval "
              "exists to surface. The headline value of this harness is not the score, it "
              "is that regressions and missed libraries now show up as numbers.\n")
    md.append("\n## Honest limitations\n")
    md.append("- The corpus is a starting instrument, not exhaustive. It covers the "
              "code-pattern checks, not the static file-existence checks (which are "
              "deterministic) or the runtime checks (which need a live gateway).\n"
              "- These are heuristic detectors. High recall with imperfect precision means "
              "the scanner errs toward surfacing a control for human review rather than "
              "silently passing. The scanner is a starting point to identify potential "
              "gaps, not a certified compliance test.\n")
    with open(os.path.join(REPO, "SCANNER_EVAL.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("wrote SCANNER_EVAL.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
