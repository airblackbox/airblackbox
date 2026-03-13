"""
Pre-commit hook entry point for AIR Blackbox.

Runs the compliance scanner and exits non-zero if any checks fail.
Used by .pre-commit-hooks.yaml (air-blackbox-comply-strict).

Usage:
    air-blackbox-comply-strict        # Fail on any failing check
"""
import sys
import os


def main():
    """Run compliance scan and fail if any checks fail."""
    from air_blackbox.compliance.engine import run_all_checks
    from air_blackbox.gateway_client import GatewayClient

    scan_path = "."

    # Find Python files to confirm there's something to scan
    py_files = []
    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if d not in {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", "deprecated", "archived",
        }]
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    if not py_files:
        print("AIR Blackbox: No Python files found, skipping compliance check.")
        sys.exit(0)

    # Run scan (no gateway needed for pre-commit)
    client = GatewayClient(gateway_url="http://localhost:8080", runs_dir=None)
    status = client.get_status()
    articles = run_all_checks(status, scan_path)

    # Count results
    total = sum(len(a["checks"]) for a in articles)
    passing = sum(1 for a in articles for c in a["checks"] if c["status"] == "pass")
    failing = sum(1 for a in articles for c in a["checks"] if c["status"] == "fail")
    warning = sum(1 for a in articles for c in a["checks"] if c["status"] == "warn")

    score_pct = int(passing / total * 100) if total > 0 else 0

    print(f"AIR Blackbox EU AI Act Compliance: {passing}/{total} ({score_pct}%)")
    print(f"  Passing: {passing}  Warnings: {warning}  Failing: {failing}")

    if failing > 0:
        print(f"\n{failing} compliance check(s) FAILED:")
        for art in articles:
            for c in art["checks"]:
                if c["status"] == "fail":
                    hint = f" — Fix: {c['fix_hint']}" if c.get("fix_hint") else ""
                    print(f"  ✗ Art {art['number']}: {c['name']}{hint}")
        print(f"\nRun `air-blackbox comply -v` for detailed fix instructions.")
        sys.exit(1)

    # Save to history
    try:
        from air_blackbox.compliance.history import save_scan
        save_scan(articles, scan_path=scan_path, version="1.2.5")
    except Exception:
        pass

    print("All compliance checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
