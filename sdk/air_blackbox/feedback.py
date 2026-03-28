"""
Feedback loop MVP for AIR Blackbox compliance scanner.

Enables users to correct scan findings and flows corrections into
training data for fine-tuning the air-compliance model. Stores
feedback in JSONL format and exports to training data.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


FEEDBACK_DIR = os.path.expanduser("~/.air-blackbox")
FEEDBACK_FILE = os.path.join(FEEDBACK_DIR, "feedback.jsonl")
LAST_SCAN_FILE = os.path.join(FEEDBACK_DIR, "last_scan.json")


def _ensure_feedback_dir():
    """Create feedback directory if it doesn't exist."""
    Path(FEEDBACK_DIR).mkdir(parents=True, exist_ok=True)


class FeedbackStore:
    """
    Stores user corrections to scan findings in JSONL format.
    
    Each feedback record contains:
    - finding_name: Name of the compliance finding
    - original_status: Original finding status (pass/warn/fail)
    - corrected_status: User's corrected status
    - reason: Optional user explanation
    - timestamp: ISO 8601 timestamp
    - scan_path: Path that was scanned
    - code_snippet: First 500 chars of triggering file
    - finding_id: Unique identifier for the finding
    """
    
    def __init__(self, feedback_file: Optional[str] = None):
        """Initialize feedback store with optional custom path."""
        _ensure_feedback_dir()
        self.feedback_file = feedback_file or FEEDBACK_FILE
    
    def record_feedback(
        self,
        finding_name: str,
        original_status: str,
        corrected_status: str,
        reason: Optional[str] = None,
        scan_path: Optional[str] = None,
        code_snippet: Optional[str] = None,
        finding_id: Optional[str] = None,
    ) -> str:
        """
        Record user feedback on a scan finding.
        
        Args:
            finding_name: Name of the finding being corrected
            original_status: Original status from scan (pass/warn/fail)
            corrected_status: Corrected status (pass/warn/fail/false_positive)
            reason: Optional user explanation for the correction
            scan_path: Path that was scanned
            code_snippet: First 500 chars of the triggering file
            finding_id: Unique finding identifier
        
        Returns:
            Feedback record ID (timestamp-based)
        """
        record_id = f"{int(time.time() * 1000)}"
        
        record = {
            "id": record_id,
            "finding_name": finding_name,
            "original_status": original_status,
            "corrected_status": corrected_status,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scan_path": scan_path,
            "code_snippet": code_snippet[:500] if code_snippet else None,
            "finding_id": finding_id,
        }
        
        with open(self.feedback_file, "a") as f:
            f.write(json.dumps(record) + "\n")
        
        return record_id
    
    def list_feedback(
        self,
        finding_name: Optional[str] = None,
        scan_path: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List feedback records with optional filtering.
        
        Args:
            finding_name: Filter by finding name
            scan_path: Filter by scan path
            limit: Maximum number of records to return
        
        Returns:
            List of feedback records matching filters
        """
        if not os.path.exists(self.feedback_file):
            return []
        
        records = []
        with open(self.feedback_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                
                if finding_name and record.get("finding_name") != finding_name:
                    continue
                if scan_path and record.get("scan_path") != scan_path:
                    continue
                
                records.append(record)
        
        if limit:
            records = records[-limit:]
        
        return records
    
    def export_to_training_data(
        self,
        output_path: str,
        include_articles: Optional[List[int]] = None,
    ) -> int:
        """
        Export feedback records to training data format for model fine-tuning.
        
        Converts feedback corrections into instruction, input, output format
        compatible with the fine-tuned air-compliance model. Stores as JSONL.
        
        Args:
            output_path: Path to write training data JSONL file
            include_articles: Optional list of article numbers to include
        
        Returns:
            Number of records exported
        """
        feedback_records = self.list_feedback()
        exported = 0
        
        with open(output_path, "w") as out_f:
            for record in feedback_records:
                finding_name = record.get("finding_name", "")
                original = record.get("original_status", "")
                corrected = record.get("corrected_status", "")
                code = record.get("code_snippet", "")
                reason = record.get("reason", "")
                
                if not code:
                    continue
                
                article_num = _extract_article_number(finding_name)
                if include_articles and article_num not in include_articles:
                    continue
                
                instruction = _build_instruction(finding_name, article_num)
                
                output_text = _build_output(
                    original,
                    corrected,
                    reason,
                    article_num
                )
                
                training_record = {
                    "instruction": instruction,
                    "input": code,
                    "output": output_text,
                    "metadata": {
                        "finding_name": finding_name,
                        "original_status": original,
                        "corrected_status": corrected,
                        "article": article_num,
                        "source": "user_feedback",
                        "timestamp": record.get("timestamp"),
                    }
                }
                
                out_f.write(json.dumps(training_record) + "\n")
                exported += 1
        
        return exported


def record_correction(
    finding_name: str,
    corrected_status: str,
    reason: Optional[str] = None,
) -> str:
    """
    Convenience function to record a correction for the most recent scan.
    
    Looks up the last scan result for context (scan path, code snippets)
    and records the feedback. Useful for CLI integration.
    
    Args:
        finding_name: Name of the finding being corrected
        corrected_status: New status (pass/warn/fail/false_positive)
        reason: Optional explanation for the correction
    
    Returns:
        Feedback record ID
    """
    _ensure_feedback_dir()
    
    last_scan = _load_last_scan()
    if not last_scan:
        raise ValueError(
            "No previous scan found. Run 'air-blackbox comply' first."
        )
    
    finding = _find_in_last_scan(finding_name, last_scan)
    if not finding:
        raise ValueError(f"Finding '{finding_name}' not found in last scan.")
    
    store = FeedbackStore()
    return store.record_feedback(
        finding_name=finding_name,
        original_status=finding.get("status", "unknown"),
        corrected_status=corrected_status,
        reason=reason,
        scan_path=last_scan.get("scan_path"),
        code_snippet=finding.get("code_snippet"),
        finding_id=finding.get("id"),
    )


def get_feedback_stats() -> Dict[str, int]:
    """
    Get statistics about feedback corrections by type.
    
    Returns:
        Dictionary with counts of false_positives, upgraded,
        downgraded, and total corrections
    """
    store = FeedbackStore()
    feedback = store.list_feedback()
    
    stats = {
        "total": len(feedback),
        "false_positive": 0,
        "upgraded": 0,
        "downgraded": 0,
        "status_unchanged": 0,
    }
    
    status_order = {"fail": 3, "warn": 2, "pass": 1}
    
    for record in feedback:
        original = record.get("original_status", "")
        corrected = record.get("corrected_status", "")
        
        if corrected == "false_positive":
            stats["false_positive"] += 1
        elif original == corrected:
            stats["status_unchanged"] += 1
        else:
            orig_val = status_order.get(original, 0)
            corr_val = status_order.get(corrected, 0)
            if corr_val > orig_val:
                stats["upgraded"] += 1
            else:
                stats["downgraded"] += 1
    
    return stats


def save_scan_context(
    articles: List[Dict[str, Any]],
    scan_path: str,
    findings_with_code: Optional[Dict[str, str]] = None,
) -> None:
    """
    Save context from the most recent scan for use by record_correction.
    
    Called by CLI after running a compliance scan. Stores scan path
    and findings for lookup when user records corrections.
    
    Args:
        articles: List of article check results from compliance engine
        scan_path: Path that was scanned
        findings_with_code: Optional dict mapping finding_id to code snippet
    """
    _ensure_feedback_dir()
    
    findings = []
    for article in articles:
        for check in article.get("checks", []):
            finding_id = f"art{article['number']}_{check['name'].replace(' ', '_')}"
            findings.append({
                "id": finding_id,
                "name": check.get("name"),
                "article": article.get("number"),
                "status": check.get("status"),
                "evidence": check.get("evidence"),
                "code_snippet": findings_with_code.get(finding_id) if findings_with_code else None,
            })
    
    context = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "scan_path": scan_path,
        "findings": findings,
    }
    
    with open(LAST_SCAN_FILE, "w") as f:
        json.dump(context, f, indent=2)


def _load_last_scan() -> Optional[Dict[str, Any]]:
    """Load the last saved scan context."""
    if not os.path.exists(LAST_SCAN_FILE):
        return None
    
    with open(LAST_SCAN_FILE, "r") as f:
        return json.load(f)


def _find_in_last_scan(
    finding_name: str,
    last_scan: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Find a specific finding in the last scan context."""
    for finding in last_scan.get("findings", []):
        if finding.get("name") == finding_name:
            return finding
    return None


def _extract_article_number(finding_name: str) -> int:
    """Extract EU AI Act article number from finding name."""
    import re
    match = re.search(r"Article\s+(\d+)", finding_name)
    if match:
        return int(match.group(1))
    return 0


def _build_instruction(finding_name: str, article_num: int) -> str:
    """Build the instruction text for training data."""
    if article_num:
        return (
            f"Analyze this Python AI agent code for EU AI Act "
            f"Article {article_num} compliance. Focus on: {finding_name}"
        )
    return f"Analyze this Python AI agent code for compliance. Focus on: {finding_name}"


def _build_output(
    original: str,
    corrected: str,
    reason: Optional[str],
    article_num: int,
) -> str:
    """Build the output text for training data."""
    parts = []
    
    if corrected == "false_positive":
        parts.append(
            f"Status: PASS (original finding was a false positive)"
        )
    else:
        parts.append(f"Status: {corrected.upper()}")
    
    if reason:
        parts.append(f"Explanation: {reason}")
    
    if article_num:
        parts.append(
            f"Article {article_num} compliance implication: "
            f"This correction improves accuracy of AI-based compliance checking."
        )
    
    return "\n".join(parts)
