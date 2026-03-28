"""Evidence bundle generation for compliance submission.

Creates comprehensive evidence packages documenting compliance
controls, audit trails, and remediation actions.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """Single piece of compliance evidence.
    
    Attributes:
        evidence_id: Unique identifier
        evidence_type: Type of evidence (scan, audit, documentation)
        description: What this evidence demonstrates
        timestamp: When evidence was collected
        content: Evidence content or reference
    """
    evidence_id: str
    evidence_type: str
    description: str
    timestamp: datetime
    content: str


class EvidenceBundle:
    """Generates compliance evidence bundles.
    
    Collects and organizes evidence of compliance measures,
    controls, and remediation for regulatory submission.
    """
    
    def __init__(self, bundle_id: str) -> None:
        """Initialize evidence bundle.
        
        Args:
            bundle_id: Unique identifier for this bundle
        """
        self.bundle_id = bundle_id
        self.items: List[EvidenceItem] = []
        self.metadata: Dict[str, Any] = {
            "bundle_id": bundle_id,
            "created_at": datetime.utcnow().isoformat()
        }
        logger.info("evidence_bundle_created", extra={"bundle_id": bundle_id})
    
    def validate_evidence_item(self, evidence_type: str, 
                              description: str, content: str) -> bool:
        """Validate evidence item before adding.
        
        Args:
            evidence_type: Type of evidence
            description: Evidence description
            content: Evidence content
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        valid_types = ["scan", "audit", "documentation", "approval", "remediation"]
        
        if evidence_type not in valid_types:
            raise ValueError(f"Invalid evidence type: {evidence_type}")
        
        if not description or len(description) < 10:
            raise ValueError("Description must be at least 10 characters")
        
        if not content:
            raise ValueError("Content cannot be empty")
        
        return True
    
    def add_evidence(self, evidence_type: str, description: str, 
                    content: str) -> EvidenceItem:
        """Add evidence item to bundle.
        
        Args:
            evidence_type: Type of evidence
            description: Description of evidence
            content: Evidence content or reference
            
        Returns:
            The created EvidenceItem
        """
        try:
            self.validate_evidence_item(evidence_type, description, content)
            
            evidence = EvidenceItem(
                evidence_id=f"ev_{len(self.items) + 1}",
                evidence_type=evidence_type,
                description=description,
                timestamp=datetime.utcnow(),
                content=content
            )
            
            self.items.append(evidence)
            
            logger.info(
                "evidence_added_to_bundle",
                extra={
                    "bundle_id": self.bundle_id,
                    "evidence_type": evidence_type,
                    "evidence_id": evidence.evidence_id
                }
            )
            
            return evidence
            
        except ValueError as e:
            logger.error("evidence_validation_error", extra={"error": str(e)})
            raise
    
    def generate_bundle_report(self) -> Dict[str, Any]:
        """Generate comprehensive evidence bundle report.
        
        Returns:
            Dictionary containing the bundle report
        """
        try:
            type_counts: Dict[str, int] = {}
            for item in self.items:
                type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
            
            report = {
                "bundle_id": self.bundle_id,
                "created_at": self.metadata["created_at"],
                "total_items": len(self.items),
                "evidence_types": type_counts,
                "evidence": [
                    {
                        "id": item.evidence_id,
                        "type": item.evidence_type,
                        "description": item.description,
                        "timestamp": item.timestamp.isoformat(),
                        "content_length": len(item.content)
                    }
                    for item in self.items
                ],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(
                "evidence_bundle_report_generated",
                extra={
                    "bundle_id": self.bundle_id,
                    "total_items": len(self.items),
                    "evidence_types": list(type_counts.keys())
                }
            )
            
            return report
            
        except Exception as e:
            logger.error("bundle_report_generation_error", extra={"error": str(e)})
            raise
    
    def export_to_json(self) -> Dict[str, Any]:
        """Export bundle as JSON-serializable dictionary.
        
        Returns:
            JSON-safe dictionary representation
        """
        report = self.generate_bundle_report()
        logger.info("bundle_exported_to_json", extra={"bundle_id": self.bundle_id})
        return report
