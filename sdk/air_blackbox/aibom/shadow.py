"""Shadow AI detection and analysis.

Detects undocumented or hidden AI systems within codebases that may
pose compliance risks.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskClassification(str, Enum):
    """Risk classification for shadow AI systems."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ShadowAIFinding:
    """Represents a detected shadow AI system.
    
    Attributes:
        finding_id: Unique identifier for the finding
        location: File path or location where shadow AI was detected
        description: Details about the shadow AI system
        risk_level: Risk classification
        confidence: Detection confidence score (0-1)
    """
    finding_id: str
    location: str
    description: str
    risk_level: RiskClassification
    confidence: float


class ShadowAIDetector:
    """Detects undocumented AI systems within codebases.
    
    Scans for patterns indicating AI model usage, decision logic,
    or ML infrastructure that may not be properly documented.
    """
    
    def __init__(self) -> None:
        """Initialize the shadow AI detector."""
        self.findings: List[ShadowAIFinding] = []
        logger.info("shadow_ai_detector_initialized")
    
    def validate_scan_input(self, file_path: str, patterns: Optional[List[str]]) -> bool:
        """Validate input parameters for scanning.
        
        Args:
            file_path: Path to file to scan
            patterns: Optional list of patterns to search for
            
        Returns:
            True if input is valid
            
        Raises:
            ValueError: If input validation fails
        """
        if not file_path or not isinstance(file_path, str):
            raise ValueError("File path must be a non-empty string")
        
        if patterns is not None:
            if not isinstance(patterns, list):
                raise ValueError("Patterns must be a list of strings")
            for pattern in patterns:
                if not isinstance(pattern, str):
                    raise ValueError("Each pattern must be a string")
        
        return True
    
    def classify_risk(self, indicators_count: int, 
                     severity_score: float) -> RiskClassification:
        """Classify the risk level of detected shadow AI.
        
        Args:
            indicators_count: Number of AI indicators found
            severity_score: Severity assessment score (0-1)
            
        Returns:
            RiskClassification for the finding
        """
        if indicators_count >= 5 or severity_score > 0.8:
            return RiskClassification.CRITICAL
        elif indicators_count >= 3 or severity_score > 0.6:
            return RiskClassification.HIGH
        elif indicators_count >= 1 or severity_score > 0.4:
            return RiskClassification.MEDIUM
        else:
            return RiskClassification.LOW
    
    def detect_shadow_ai(self, file_path: str, patterns: Optional[List[str]] = None,
                        confidence_threshold: float = 0.7) -> Optional[ShadowAIFinding]:
        """Detect shadow AI in a specific file.
        
        Args:
            file_path: Path to the file to scan
            patterns: Optional patterns to search for
            confidence_threshold: Minimum confidence for reporting (0-1)
            
        Returns:
            ShadowAIFinding if shadow AI is detected, None otherwise
        """
        try:
            self.validate_scan_input(file_path, patterns)
            
            logger.info(
                "shadow_ai_scan_started",
                extra={"file": file_path, "threshold": confidence_threshold}
            )
            
            # Placeholder detection logic
            finding = ShadowAIFinding(
                finding_id="shadow_001",
                location=file_path,
                description="Potential undocumented AI usage detected",
                risk_level=self.classify_risk(2, 0.65),
                confidence=0.75
            )
            
            if finding.confidence >= confidence_threshold:
                self.findings.append(finding)
                logger.warning(
                    "shadow_ai_detected",
                    extra={
                        "location": file_path,
                        "risk": finding.risk_level,
                        "confidence": finding.confidence
                    }
                )
                return finding
            
            logger.info("shadow_ai_scan_completed_clean", extra={"file": file_path})
            return None
            
        except ValueError as e:
            logger.error("shadow_ai_validation_error", extra={"error": str(e)})
            raise
    
    def get_findings_by_risk(self, risk_level: RiskClassification) -> List[ShadowAIFinding]:
        """Retrieve findings filtered by risk level.
        
        Args:
            risk_level: RiskClassification to filter by
            
        Returns:
            List of findings matching the risk level
        """
        filtered = [f for f in self.findings if f.risk_level == risk_level]
        logger.info(
            "findings_retrieved",
            extra={"risk_level": risk_level, "count": len(filtered)}
        )
        return filtered
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of all shadow AI findings.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_findings": len(self.findings),
            "critical": len(self.get_findings_by_risk(RiskClassification.CRITICAL)),
            "high": len(self.get_findings_by_risk(RiskClassification.HIGH)),
            "medium": len(self.get_findings_by_risk(RiskClassification.MEDIUM)),
            "low": len(self.get_findings_by_risk(RiskClassification.LOW)),
            "findings": [
                {
                    "id": f.finding_id,
                    "location": f.location,
                    "risk": f.risk_level.value,
                    "confidence": f.confidence
                }
                for f in self.findings
            ]
        }
        
        logger.info(
            "shadow_ai_summary_generated",
            extra={"total_findings": len(self.findings)}
        )
        
        return summary
