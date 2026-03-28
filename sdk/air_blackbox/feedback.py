"""Compliance feedback collection and processing.

This module handles gathering, validating, and recording user feedback
on compliance scanning results.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComplianceFeedback:
    """Represents feedback on a compliance scan result.
    
    Attributes:
        scan_id: Unique identifier for the scanned item
        article: EU AI Act article number (9, 10, 11, 12, 14, 15)
        severity: Issue severity level (critical, high, medium, low)
        feedback_text: User feedback text
        timestamp: When feedback was collected
    """
    scan_id: str
    article: int
    severity: str
    feedback_text: str
    timestamp: datetime


def validate_feedback_input(feedback_text: str, article: int, severity: str) -> bool:
    """Validate user feedback before processing.
    
    Performs input sanitization and validation to ensure feedback
    meets minimum quality standards.
    
    Args:
        feedback_text: The feedback text to validate
        article: EU AI Act article number
        severity: Issue severity level
        
    Returns:
        True if feedback passes validation
        
    Raises:
        ValueError: If feedback fails validation
    """
    if not feedback_text or len(feedback_text.strip()) < 10:
        raise ValueError("Feedback text must be at least 10 characters")
    
    if article not in (9, 10, 11, 12, 14, 15):
        raise ValueError(f"Invalid article: {article}")
    
    if severity not in ("critical", "high", "medium", "low"):
        raise ValueError(f"Invalid severity: {severity}")
    
    return True


def record_feedback(scan_id: str, article: int, severity: str, 
                   feedback_text: str) -> ComplianceFeedback:
    """Record user feedback on a compliance scan result.
    
    Args:
        scan_id: Unique identifier for the scanned item
        article: EU AI Act article number
        severity: Issue severity level
        feedback_text: User feedback text
        
    Returns:
        ComplianceFeedback object with audit logging
    """
    try:
        validate_feedback_input(feedback_text, article, severity)
        
        feedback = ComplianceFeedback(
            scan_id=scan_id,
            article=article,
            severity=severity,
            feedback_text=feedback_text.strip(),
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            "feedback_recorded",
            extra={
                "scan_id": scan_id,
                "article": article,
                "severity": severity,
                "timestamp": feedback.timestamp.isoformat()
            }
        )
        
        return feedback
        
    except ValueError as e:
        logger.error("feedback_validation_error", extra={"error": str(e)})
        raise


def collect_feedback_batch(feedback_items: List[Dict[str, Any]]) -> List[ComplianceFeedback]:
    """Collect multiple feedback items with error recovery.
    
    Args:
        feedback_items: List of feedback dictionaries
        
    Returns:
        List of successfully recorded feedback items
    """
    results = []
    failed_count = 0
    
    for item in feedback_items:
        try:
            feedback = record_feedback(
                scan_id=item.get("scan_id", ""),
                article=item.get("article", 0),
                severity=item.get("severity", ""),
                feedback_text=item.get("feedback_text", "")
            )
            results.append(feedback)
        except (ValueError, KeyError) as e:
            failed_count += 1
            logger.warning(f"Failed to record feedback item: {e}")
    
    logger.info(
        "batch_feedback_processed",
        extra={"total": len(feedback_items), "failed": failed_count}
    )
    
    return results
