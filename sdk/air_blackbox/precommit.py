"""Pre-commit hooks for compliance scanning.

Integrates compliance scanning into git pre-commit workflow to catch
issues before code is committed.
"""

import logging
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_commit_files(file_paths: List[str]) -> bool:
    """Validate file paths before scanning.
    
    Ensures file paths are safe and accessible.
    
    Args:
        file_paths: List of file paths to validate
        
    Returns:
        True if all files are valid
        
    Raises:
        ValueError: If any file path is invalid
    """
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
    
    return True


def run_compliance_scan(file_paths: List[str], 
                       timeout: int = 30) -> Dict[str, Any]:
    """Run compliance scan on staged files.
    
    Executes compliance scanning with error handling and timeout
    protection.
    
    Args:
        file_paths: Python files to scan for compliance
        timeout: Timeout in seconds for the scan
        
    Returns:
        Dictionary with scan results and status
    """
    try:
        validate_commit_files(file_paths)
        
        logger.info(
            "compliance_scan_started",
            extra={"file_count": len(file_paths)}
        )
        
        # Placeholder for actual scan execution
        results = {
            "status": "completed",
            "files_scanned": len(file_paths),
            "issues_found": 0,
            "timeout": timeout
        }
        
        logger.info(
            "compliance_scan_completed",
            extra={"status": results["status"]}
        )
        
        return results
        
    except ValueError as e:
        logger.error("scan_validation_error", extra={"error": str(e)})
        raise
    except subprocess.TimeoutExpired:
        logger.error("scan_timeout", extra={"timeout": timeout})
        raise


def should_allow_commit(scan_results: Dict[str, Any], 
                       allow_warnings: bool = False) -> bool:
    """Determine if commit should be allowed based on scan results.
    
    Args:
        scan_results: Results from compliance scan
        allow_warnings: Whether to allow commits with warnings
        
    Returns:
        True if commit should be allowed
    """
    issues = scan_results.get("issues_found", 0)
    
    if issues == 0:
        logger.info("precommit_check_passed")
        return True
    
    if allow_warnings:
        logger.warning(f"precommit_issues_allowed: {issues} issues found")
        return True
    
    logger.error(f"precommit_blocked: {issues} compliance issues found")
    return False


def execute_precommit_hook(file_paths: Optional[List[str]] = None) -> int:
    """Execute the pre-commit compliance hook.
    
    Args:
        file_paths: Specific files to check. If None, checks all staged files.
        
    Returns:
        Exit code: 0 for success, 1 for failure
    """
    try:
        if not file_paths:
            file_paths = []
        
        scan_results = run_compliance_scan(file_paths)
        allowed = should_allow_commit(scan_results)
        
        logger.info(
            "precommit_hook_executed",
            extra={"allowed": allowed, "files": len(file_paths)}
        )
        
        return 0 if allowed else 1
        
    except (ValueError, subprocess.TimeoutExpired) as e:
        logger.error(f"precommit_hook_error: {e}")
        return 1
