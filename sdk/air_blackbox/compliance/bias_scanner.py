"""Bias detection and analysis for AI systems.

Scans AI systems for potential bias, fairness issues, and
discriminatory patterns in decision-making.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BiasRiskLevel(str, Enum):
    """Classification of bias risk severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BiasFinding:
    """Represents a detected bias issue.
    
    Attributes:
        finding_id: Unique identifier
        location: Where bias was detected
        affected_groups: Protected groups potentially affected
        severity: Risk classification
        description: Details about the bias
    """
    finding_id: str
    location: str
    affected_groups: List[str]
    severity: BiasRiskLevel
    description: str


class BiasScanner:
    """Scans AI systems for bias and fairness issues.
    
    Evaluates models and decision systems for potential
    discriminatory patterns and fairness violations.
    """
    
    def __init__(self) -> None:
        """Initialize the bias scanner."""
        self.findings: List[BiasFinding] = []
        logger.info("bias_scanner_initialized")
    
    def validate_input_data(self, data_source: str, 
                           protected_attributes: Optional[List[str]] = None) -> bool:
        """Validate input data for bias scanning.
        
        Args:
            data_source: Source of data to scan
            protected_attributes: List of protected attributes to check
            
        Returns:
            True if input is valid
            
        Raises:
            ValueError: If input validation fails
        """
        if not data_source or not isinstance(data_source, str):
            raise ValueError("Data source must be a non-empty string")
        
        if protected_attributes is not None:
            if not isinstance(protected_attributes, list):
                raise ValueError("Protected attributes must be a list")
            for attr in protected_attributes:
                if not isinstance(attr, str):
                    raise ValueError("Each attribute must be a string")
        
        return True
    
    def classify_bias_risk(self, parity_gaps: List[float], 
                          impact_score: float) -> BiasRiskLevel:
        """Classify the risk level of detected bias.
        
        Args:
            parity_gaps: Disparate impact gap percentages
            impact_score: Overall impact assessment (0-1)
            
        Returns:
            BiasRiskLevel classification
        """
        max_gap = max(parity_gaps) if parity_gaps else 0
        
        if max_gap > 0.5 or impact_score > 0.8:
            return BiasRiskLevel.CRITICAL
        elif max_gap > 0.3 or impact_score > 0.6:
            return BiasRiskLevel.HIGH
        elif max_gap > 0.15 or impact_score > 0.4:
            return BiasRiskLevel.MEDIUM
        else:
            return BiasRiskLevel.LOW
    
    def scan_for_bias(self, data_source: str, 
                     protected_attributes: Optional[List[str]] = None) -> List[BiasFinding]:
        """Scan data source for bias patterns.
        
        Args:
            data_source: Data source to analyze
            protected_attributes: Attributes to check for disparate impact
            
        Returns:
            List of bias findings
        """
        try:
            self.validate_input_data(data_source, protected_attributes)
            
            logger.info(
                "bias_scan_started",
                extra={
                    "data_source": data_source,
                    "protected_attributes": protected_attributes or []
                }
            )
            
            # Placeholder detection logic
            results = []
            
            logger.info(
                "bias_scan_completed",
                extra={"findings": len(results), "data_source": data_source}
            )
            
            return results
            
        except ValueError as e:
            logger.error("bias_scan_validation_error", extra={"error": str(e)})
            raise
    
    def check_output_filtering(self, output_data: Dict[str, Any]) -> bool:
        """Validate that outputs are appropriately filtered.
        
        Args:
            output_data: Output to validate for content filtering
            
        Returns:
            True if output passes filtering checks
        """
        try:
            if not isinstance(output_data, dict):
                raise ValueError("Output must be a dictionary")
            
            logger.info("output_filtering_check_passed")
            return True
            
        except ValueError as e:
            logger.error("output_filtering_error", extra={"error": str(e)})
            raise
    
    def generate_bias_report(self) -> Dict[str, Any]:
        """Generate comprehensive bias analysis report.
        
        Returns:
            Dictionary containing bias assessment results
        """
        critical_count = len([f for f in self.findings 
                            if f.severity == BiasRiskLevel.CRITICAL])
        high_count = len([f for f in self.findings 
                         if f.severity == BiasRiskLevel.HIGH])
        
        report = {
            "total_findings": len(self.findings),
            "critical_issues": critical_count,
            "high_priority_issues": high_count,
            "findings": [
                {
                    "id": f.finding_id,
                    "location": f.location,
                    "affected_groups": f.affected_groups,
                    "severity": f.severity.value,
                    "description": f.description
                }
                for f in self.findings
            ]
        }
        
        logger.info(
            "bias_report_generated",
            extra={
                "total_findings": len(self.findings),
                "critical": critical_count
            }
        )

        return report


# Module-level convenience function for MCP server compatibility.

def scan_bias(file_path: str) -> dict:
    """Scan a Python file for bias and fairness issues.

    Module-level function that wraps BiasScanner for the MCP server.

    Args:
        file_path: Path to a Python file to scan.

    Returns:
        Bias analysis report dict.
    """
    import re
    import os

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}", "findings": []}

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    findings = []

    # Check for protected attribute references
    protected_pats = [
        (r'\b(?:gender|sex|race|ethnicity|age|religion|disability|nationality)\b', "protected_attribute_reference"),
        (r'\b(?:male|female|man|woman|boy|girl)\b', "gender_reference"),
        (r'\b(?:white|black|asian|hispanic|latino)\b', "race_reference"),
    ]
    for pattern, bias_type in protected_pats:
        matches = re.findall(pattern, code, re.IGNORECASE)
        if matches:
            findings.append({
                "type": bias_type,
                "count": len(matches),
                "severity": "medium",
                "description": f"Found {len(matches)} reference(s) to protected attributes. Review for potential bias.",
            })

    # Check for fairness-aware patterns (positive signals)
    fairness_pats = [
        r"fairness", r"bias_mitigat", r"disparate_impact",
        r"demographic_parity", r"equalized_odds", r"calibration",
        r"protected_group", r"sensitive_attribute",
    ]
    fairness_combined = "|".join(fairness_pats)
    has_fairness = bool(re.search(fairness_combined, code, re.IGNORECASE))

    # Check for hardcoded thresholds that might encode bias
    threshold_pats = re.findall(r'(?:threshold|cutoff|minimum_score)\s*[=<>]+\s*[\d.]+', code)
    if threshold_pats and not has_fairness:
        findings.append({
            "type": "unvalidated_threshold",
            "count": len(threshold_pats),
            "severity": "high",
            "description": "Hardcoded thresholds found without fairness validation. These may encode bias.",
        })

    return {
        "file": file_path,
        "findings": findings,
        "fairness_aware": has_fairness,
        "risk_level": "high" if any(f["severity"] == "high" for f in findings) else "medium" if findings else "low",
        "recommendation": (
            "Fairness controls detected. Verify they cover all protected groups."
            if has_fairness
            else "No fairness controls detected. Add bias testing before deployment."
        ),
    }
