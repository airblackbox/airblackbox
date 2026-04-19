---
description: Scans a Python AI project for EU AI Act compliance gaps using AIR Blackbox. Use when the user asks to check compliance, scan their code, audit their AI project, or mentions EU AI Act, Articles 9-15, or compliance checking.
tags: ["compliance", "EU AI Act", "audit", "scanner", "Python"]
---

# AIR Blackbox Compliance Scan

You are running an EU AI Act compliance scan using AIR Blackbox. This checks a Python AI codebase against 51+ technical requirements mapped to EU AI Act Articles 9-15.

## Prerequisites

Check if `air-blackbox` is installed:

```bash
pip show air-blackbox 2>/dev/null || echo "NOT_INSTALLED"
```

If not installed, install it:

```bash
pip install air-blackbox
```

## Running the Scan

Run the scanner against the project directory. Default is the current directory:

```bash
air-blackbox comply --scan . -v
```

For JSON output (useful for programmatic analysis):

```bash
air-blackbox comply --scan . --format json
```

## Interpreting Results

The scanner checks 6 EU AI Act articles. For each one:

- **Article 9 — Risk Management**: Looks for risk assessment patterns, try/except blocks around AI calls, fallback handling, and confidence thresholds.
- **Article 10 — Data Governance**: Checks for data validation, schema enforcement, data quality checks, and provenance tracking.
- **Article 11 — Technical Documentation**: Looks for MODEL_CARD.md, SYSTEM_CARD.md, docstrings on model functions, and architecture docs.
- **Article 12 — Record-Keeping**: Checks for audit logging, HMAC chains, agent identity binding (air-trust, AAR, SCC), and structured logging of AI decisions.
- **Article 14 — Human Oversight**: Looks for human-in-the-loop patterns, approval workflows, confidence-based escalation, and delegation logging.
- **Article 15 — Accuracy & Robustness**: Checks for RNG seed setting, deterministic algorithm flags, hardware abstraction, input validation, and error handling.

## Result Statuses

- **PASS**: The technical control is present and correctly implemented.
- **WARN**: Partial implementation detected. The check found something but it may not be complete.
- **FAIL**: The technical control is missing. The output includes a fix hint with the specific code location and regulatory clause.

## Important Caveats

Always tell the user:
- This checks **technical requirements**, not legal compliance. It is a linter, not a lawyer.
- Passing every check does NOT mean legal compliance. It means the code implements the technical controls the regulation references.
- Legal interpretation is their counsel's job.
- Pattern-based detection has false positives. If they see one, they should open an issue on the repo.

## After the Scan

1. Show the user the summary table (articles, pass/warn/fail counts).
2. For each FAIL, explain what's missing in plain English and show the fix hint.
3. If they want to fix issues, help them implement the specific code changes the scanner suggests.
4. Offer to re-run the scan after fixes to verify improvement.
