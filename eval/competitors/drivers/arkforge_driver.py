"""Run the ArkForge EU AI Act scanner (PyPI: eu-ai-act-scanner) on many dirs.

Run with the Python of a venv that has eu-ai-act-scanner installed:

    <venv>/bin/python arkforge_driver.py manifest.json out.json

manifest.json is a JSON list of directories. For each one this records what
the scanner reports through its own public classes, exactly as its CLI and
MCP server build their reports:

  ai_files         files it recognised as AI code (EUAIActChecker.scan_project)
  content_marking  its one code-level EU AI Act check (risk "limited")
  gdpr_patterns    GDPR code-pattern categories it detected (GDPRChecker)

Its other EU AI Act checks only test whether Markdown files such as
HUMAN_OVERSIGHT.md exist, so they have nothing to say about code.
"""
import json
import sys

from gdpr_module import GDPRChecker
from server import EUAIActChecker


def run(path):
    checker = EUAIActChecker(path)
    scan = checker.scan_project()
    compliance = checker.check_compliance("limited")
    gdpr = GDPRChecker(path)
    gdpr_scan = gdpr.scan_project()
    return {
        "ai_files": [f["file"] for f in scan.get("ai_files", [])],
        "content_marking": bool(compliance["compliance_status"].get("content_marking")),
        "gdpr_patterns": sorted(gdpr_scan.get("detected_patterns", {}).keys()),
    }


def main():
    with open(sys.argv[1]) as f:
        dirs = json.load(f)
    out = {}
    for d in dirs:
        try:
            out[d] = run(d)
        except Exception as exc:  # recorded, never hidden
            out[d] = {"error": repr(exc)}
    with open(sys.argv[2], "w") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()
