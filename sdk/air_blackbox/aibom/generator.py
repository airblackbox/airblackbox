"""AI Bill of Materials (AIBOM) generator.

Generates compliance documentation and bill of materials for AI systems
according to EU AI Act requirements.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AIBOMEntry:
    """Single entry in an AI Bill of Materials.
    
    Attributes:
        component_name: Name of the AI component
        article: Applicable EU AI Act article
        risk_level: Risk classification (critical, high, medium, low)
        documentation: Reference to compliance documentation
        timestamp: Generation timestamp
    """
    component_name: str
    article: int
    risk_level: str
    documentation: str
    timestamp: datetime


class AIBOMGenerator:
    """Generates AI Bill of Materials with compliance tracking.
    
    This class creates comprehensive AIBOM documents that catalog
    all AI components and their compliance requirements.
    """
    
    def __init__(self) -> None:
        """Initialize the AIBOM generator."""
        self.entries: List[AIBOMEntry] = []
        logger.info("aibom_generator_initialized")
    
    def validate_component_data(self, component_name: str, article: int, 
                               risk_level: str) -> bool:
        """Validate component data before adding to AIBOM.
        
        Args:
            component_name: Name of the component
            article: EU AI Act article number
            risk_level: Risk classification
            
        Returns:
            True if component data is valid
            
        Raises:
            ValueError: If any field is invalid
        """
        if not component_name or not isinstance(component_name, str):
            raise ValueError("Component name must be a non-empty string")
        
        if article not in (9, 10, 11, 12, 14, 15):
            raise ValueError(f"Invalid article number: {article}")
        
        if risk_level not in ("critical", "high", "medium", "low"):
            raise ValueError(f"Invalid risk level: {risk_level}")
        
        return True
    
    def add_component(self, component_name: str, article: int,
                     risk_level: str, documentation: str) -> AIBOMEntry:
        """Add a component to the AIBOM.
        
        Args:
            component_name: Name of the component
            article: EU AI Act article number
            risk_level: Risk classification
            documentation: Link or reference to documentation
            
        Returns:
            The created AIBOMEntry
        """
        try:
            self.validate_component_data(component_name, article, risk_level)
            
            entry = AIBOMEntry(
                component_name=component_name,
                article=article,
                risk_level=risk_level,
                documentation=documentation,
                timestamp=datetime.utcnow()
            )
            
            self.entries.append(entry)
            
            logger.info(
                "aibom_component_added",
                extra={
                    "component": component_name,
                    "article": article,
                    "risk_level": risk_level
                }
            )
            
            return entry
            
        except ValueError as e:
            logger.error("aibom_validation_error", extra={"error": str(e)})
            raise
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate the AIBOM report.
        
        Creates a comprehensive report of all components and their
        compliance requirements.
        
        Returns:
            Dictionary containing the AIBOM report data
        """
        try:
            if not self.entries:
                logger.warning("aibom_empty_report")
                return {
                    "components_count": 0,
                    "entries": [],
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            report = {
                "components_count": len(self.entries),
                "entries": [
                    {
                        "component_name": e.component_name,
                        "article": e.article,
                        "risk_level": e.risk_level,
                        "documentation": e.documentation,
                        "added_at": e.timestamp.isoformat()
                    }
                    for e in self.entries
                ],
                "generated_at": datetime.utcnow().isoformat(),
                "risk_distribution": self._calculate_risk_distribution()
            }
            
            logger.info(
                "aibom_report_generated",
                extra={"components": len(self.entries)}
            )
            
            return report
            
        except Exception as e:
            logger.error("aibom_report_generation_error", extra={"error": str(e)})
            raise
    
    def _calculate_risk_distribution(self) -> Dict[str, int]:
        """Calculate distribution of risk levels.
        
        Returns:
            Dictionary with risk level counts
        """
        distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for entry in self.entries:
            if entry.risk_level in distribution:
                distribution[entry.risk_level] += 1
        
        return distribution
