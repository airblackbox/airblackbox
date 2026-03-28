"""Compliance scan history tracking and audit trail.

Maintains a complete audit trail of all compliance scans, decisions,
and remediation actions for regulatory record-keeping.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComplianceScanRecord:
    """Record of a single compliance scan.
    
    Attributes:
        scan_id: Unique identifier for the scan
        timestamp: When the scan was performed
        target: What was scanned (file, module, project)
        articles_checked: List of EU AI Act articles evaluated
        issues_found: Number of compliance issues found
        severity_distribution: Count of issues by severity
        remediation_status: Status of issue remediation
    """
    scan_id: str
    timestamp: datetime
    target: str
    articles_checked: List[int]
    issues_found: int
    severity_distribution: Dict[str, int]
    remediation_status: str


class ComplianceHistory:
    """Maintains audit trail of compliance scans and actions.
    
    Provides comprehensive record-keeping for regulatory compliance
    and historical analysis of compliance trends.
    """
    
    def __init__(self) -> None:
        """Initialize the compliance history tracker."""
        self.records: List[ComplianceScanRecord] = []
        logger.info("compliance_history_initialized")
    
    def validate_scan_record(self, scan_id: str, target: str,
                            articles: List[int]) -> bool:
        """Validate scan record data before recording.
        
        Args:
            scan_id: Unique scan identifier
            target: Target of the scan
            articles: List of article numbers
            
        Returns:
            True if record data is valid
            
        Raises:
            ValueError: If validation fails
        """
        if not scan_id or not isinstance(scan_id, str):
            raise ValueError("Scan ID must be a non-empty string")
        
        if not target or not isinstance(target, str):
            raise ValueError("Target must be a non-empty string")
        
        if not articles or not isinstance(articles, list):
            raise ValueError("Articles must be a non-empty list")
        
        for article in articles:
            if article not in (9, 10, 11, 12, 14, 15):
                raise ValueError(f"Invalid article: {article}")
        
        return True
    
    def log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log a compliance-related action to the audit trail.
        
        Args:
            action_type: Type of action (scan, remediation, review)
            details: Details about the action
        """
        logger.info(
            f"audit_log:{action_type}",
            extra={
                "timestamp": datetime.utcnow().isoformat(),
                **details
            }
        )
    
    def record_scan(self, scan_id: str, target: str, articles: List[int],
                   issues_found: int, severity_dist: Dict[str, int]) -> ComplianceScanRecord:
        """Record the results of a compliance scan.
        
        Args:
            scan_id: Unique identifier for this scan
            target: What was scanned (file path, module name)
            articles: EU AI Act articles that were evaluated
            issues_found: Total number of issues found
            severity_dist: Distribution of severity levels
            
        Returns:
            The created ComplianceScanRecord
        """
        try:
            self.validate_scan_record(scan_id, target, articles)
            
            record = ComplianceScanRecord(
                scan_id=scan_id,
                timestamp=datetime.utcnow(),
                target=target,
                articles_checked=articles,
                issues_found=issues_found,
                severity_distribution=severity_dist,
                remediation_status="pending"
            )
            
            self.records.append(record)
            
            self.log_action("scan_recorded", {
                "scan_id": scan_id,
                "target": target,
                "articles": articles,
                "issues": issues_found
            })
            
            return record
            
        except ValueError as e:
            logger.error("scan_validation_error", extra={"error": str(e)})
            raise
    
    def update_remediation_status(self, scan_id: str, status: str,
                                 notes: Optional[str] = None) -> None:
        """Update remediation status for a scan.
        
        Args:
            scan_id: ID of the scan to update
            status: New remediation status (pending, in_progress, resolved)
            notes: Optional notes about the remediation
        """
        for record in self.records:
            if record.scan_id == scan_id:
                record.remediation_status = status
                self.log_action("remediation_updated", {
                    "scan_id": scan_id,
                    "status": status,
                    "notes": notes or ""
                })
                logger.info(f"remediation_status_updated: {scan_id} -> {status}")
                return
        
        logger.warning(f"scan_not_found_for_update: {scan_id}")
    
    def get_scan_history(self, target: Optional[str] = None) -> List[ComplianceScanRecord]:
        """Retrieve scan history.
        
        Args:
            target: Optional filter by target name
            
        Returns:
            List of ComplianceScanRecords
        """
        if target:
            records = [r for r in self.records if target in r.target]
            logger.info(
                "history_retrieved_filtered",
                extra={"target": target, "count": len(records)}
            )
            return records
        
        logger.info("history_retrieved_all", extra={"count": len(self.records)})
        return self.records
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit report.
        
        Returns:
            Dictionary containing audit trail summary
        """
        total_scans = len(self.records)
        total_issues = sum(r.issues_found for r in self.records)
        
        resolved = sum(1 for r in self.records if r.remediation_status == "resolved")
        
        report = {
            "total_scans": total_scans,
            "total_issues_found": total_issues,
            "resolved_scans": resolved,
            "pending_scans": total_scans - resolved,
            "generated_at": datetime.utcnow().isoformat(),
            "scan_records": [
                {
                    "scan_id": r.scan_id,
                    "target": r.target,
                    "articles": r.articles_checked,
                    "issues": r.issues_found,
                    "status": r.remediation_status,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.records
            ]
        }
        
        self.log_action("audit_report_generated", {
            "total_scans": total_scans,
            "total_issues": total_issues
        })
        
        logger.info(
            "audit_report_generated",
            extra={"scans": total_scans, "issues": total_issues}
        )
        
        return report
