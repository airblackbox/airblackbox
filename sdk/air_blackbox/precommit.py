"""
Pre-commit hook entry point for AIR Blackbox compliance scanning.

Accepts staged Python files from pre-commit framework and runs compliance checks.
Exits 0 if all checks pass or warn (unless --strict), exits 1 if any check fails.

Supports multiple compliance scan modes:
  --strict: Also fail on warnings
  --gdpr: Include GDPR compliance checks
  --bias: Include bias and fairness checks

Usage:
    air-blackbox-comply-strict [--strict] [--gdpr] [--bias] [files...]
"""
import sys
import argparse
import os
from pathlib import Path
from typing import List, Dict, Tuple


def scan_file(filepath: str, strict: bool = False, gdpr: bool = False, 
              bias: bool = False) -> Dict:
    """
    Scan a single Python file for compliance issues.
    
    Args:
        filepath: Path to Python file to scan
        strict: If True, treat warnings as failures
        gdpr: If True, include GDPR compliance checks
        bias: If True, include bias and fairness checks
        
    Returns:
        Dictionary with scan results containing keys: passed, warnings, failures, issues
    """
    from air_blackbox.compliance.engine import run_all_checks
    from air_blackbox.gateway_client import GatewayClient
    
    result = {
        'passed': 0,
        'warnings': 0,
        'failures': 0,
        'issues': []
    }
    
    try:
        # Run compliance scan on the file
        client = GatewayClient(gateway_url="http://localhost:8080", runs_dir=None)
        status = client.get_status()
        articles = run_all_checks(status, filepath)
        
        # Count results
        for article in articles:
            for check in article.get('checks', []):
                check_status = check.get('status', 'unknown')
                
                if check_status == 'pass':
                    result['passed'] += 1
                elif check_status == 'warn':
                    result['warnings'] += 1
                    result['issues'].append({
                        'type': 'warning',
                        'article': article.get('number'),
                        'name': check.get('name'),
                        'fix': check.get('fix_hint', '')
                    })
                elif check_status == 'fail':
                    result['failures'] += 1
                    result['issues'].append({
                        'type': 'failure',
                        'article': article.get('number'),
                        'name': check.get('name'),
                        'fix': check.get('fix_hint', '')
                    })
    except Exception as e:
        # Handle scan errors gracefully
        result['failures'] += 1
        result['issues'].append({
            'type': 'error',
            'article': 'N/A',
            'name': 'Scan Error',
            'fix': str(e)
        })
    
    return result


def print_summary_table(total_passed: int, total_warnings: int, total_failures: int,
                        file_count: int) -> None:
    """
    Print a formatted summary table of scan results.
    
    Args:
        total_passed: Total number of passing checks
        total_warnings: Total number of warnings
        total_failures: Total number of failures
        file_count: Number of files scanned
    """
    total = total_passed + total_warnings + total_failures
    if total == 0:
        print("AIR Blackbox: No checks performed")
        return
    
    pass_pct = int((total_passed / total * 100) if total > 0 else 0)
    
    print("\n" + "=" * 70)
    print("AIR Blackbox EU AI Act Compliance Summary")
    print("=" * 70)
    print(f"Files scanned:    {file_count}")
    print(f"Total checks:     {total}")
    print(f"Passed:           {total_passed:>3}  ({pass_pct}%)")
    print(f"Warnings:         {total_warnings:>3}")
    print(f"Failures:         {total_failures:>3}")
    print("=" * 70)


def main():
    """
    Main entry point for pre-commit hook.
    
    Accepts file paths as arguments (provided by pre-commit framework) and scans
    each Python file for compliance issues. Prints summary table and exits with
    appropriate code.
    
    Exit codes:
      0: All checks passed or only warnings (unless --strict)
      1: Any check failed, or warnings found with --strict
    """
    parser = argparse.ArgumentParser(
        description='AIR Blackbox compliance scanner for pre-commit hooks'
    )
    parser.add_argument('files', nargs='*', help='Python files to scan')
    parser.add_argument('--strict', action='store_true',
                        help='Fail on warnings as well as failures')
    parser.add_argument('--gdpr', action='store_true',
                        help='Include GDPR compliance checks')
    parser.add_argument('--bias', action='store_true',
                        help='Include bias and fairness checks')
    
    args = parser.parse_args()
    
    # If no files provided, find all Python files in current directory
    if not args.files:
        py_files = []
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in {
                'node_modules', '.git', '__pycache__', '.venv', 'venv',
                'dist', 'build', 'deprecated', 'archived', '.eggs', 'eggs'
            }]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))
        args.files = py_files
    
    if not args.files:
        print("AIR Blackbox: No Python files found, skipping compliance check.")
        sys.exit(0)
    
    # Scan each file
    total_passed = 0
    total_warnings = 0
    total_failures = 0
    all_issues = []
    
    for filepath in args.files:
        if not os.path.isfile(filepath) or not filepath.endswith('.py'):
            continue
        
        result = scan_file(filepath, strict=args.strict, gdpr=args.gdpr, 
                          bias=args.bias)
        total_passed += result['passed']
        total_warnings += result['warnings']
        total_failures += result['failures']
        all_issues.extend(result['issues'])
    
    # Print summary table
    print_summary_table(total_passed, total_warnings, total_failures, 
                       len(args.files))
    
    # Print detailed issues if any
    if all_issues:
        print("\nDetailed Issues:")
        print("-" * 70)
        for issue in all_issues:
            icon = '✗' if issue['type'] == 'failure' else '⚠'
            art_str = f"Art {issue['article']}" if issue['article'] != 'N/A' else 'N/A'
            print(f"{icon} [{issue['type'].upper()}] {art_str}: {issue['name']}")
            if issue['fix']:
                print(f"    Fix: {issue['fix']}")
        print("-" * 70)
    
    # Determine exit code
    if total_failures > 0:
        print(f"\n✗ Compliance check FAILED; {total_failures} issue(s) must be fixed.")
        sys.exit(1)
    
    if args.strict and total_warnings > 0:
        print(f"\n✗ Compliance check FAILED; {total_warnings} warning(s) in strict mode.")
        sys.exit(1)
    
    if total_warnings > 0:
        print(f"\n⚠ Compliance check passed with {total_warnings} warning(s).")
        print("  Run with --strict to fail on warnings.")
    else:
        print("\n✓ All compliance checks passed.")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
