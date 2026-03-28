"""Trust chain implementation for AI system governance.

Establishes trust boundaries and verification chains for multi-step
AI operations with human oversight and approval requirements.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Classification of operational risk."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ApprovalRecord:
    """Record of approval decision.
    
    Attributes:
        approver: User or system that approved
        decision: Approval decision (approved, rejected, deferred)
        timestamp: When decision was made
        reason: Explanation for decision
    """
    approver: str
    decision: str
    timestamp: datetime
    reason: Optional[str]


class TrustChain:
    """Implements a verification chain with human oversight.
    
    Provides governance controls including approval requirements,
    rate limiting, and risk classification for AI operations.
    """
    
    def __init__(self, max_rate_limit: int = 100) -> None:
        """Initialize the trust chain.
        
        Args:
            max_rate_limit: Maximum operations per minute
        """
        self.max_rate_limit = max_rate_limit
        self.operation_log: List[Dict[str, Any]] = []
        self.approval_records: List[ApprovalRecord] = []
        logger.info("trust_chain_initialized", extra={"rate_limit": max_rate_limit})
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data before processing.
        
        Args:
            input_data: Input to validate
            
        Returns:
            True if input is valid
            
        Raises:
            ValueError: If input validation fails
        """
        if not isinstance(input_data, dict):
            raise ValueError("Input must be a dictionary")
        
        required_keys = ["operation", "context"]
        for key in required_keys:
            if key not in input_data:
                raise ValueError(f"Missing required key: {key}")
        
        return True
    
    def classify_risk(self, operation_type: str, impact_score: float) -> RiskLevel:
        """Classify the risk level of an operation.
        
        Args:
            operation_type: Type of operation being performed
            impact_score: Estimated impact (0-1)
            
        Returns:
            RiskLevel classification
        """
        if impact_score > 0.8 or operation_type in ["deletion", "modification"]:
            return RiskLevel.CRITICAL
        elif impact_score > 0.6:
            return RiskLevel.HIGH
        elif impact_score > 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def require_approval(self, operation: Dict[str, Any], 
                        risk_level: RiskLevel) -> bool:
        """Determine if operation requires human approval.
        
        Args:
            operation: Operation details
            risk_level: Classified risk level
            
        Returns:
            True if approval is required
        """
        requires_approval = risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        logger.info(
            "approval_requirement_assessed",
            extra={
                "operation": operation.get("type", "unknown"),
                "risk_level": risk_level.value,
                "approval_required": requires_approval
            }
        )
        return requires_approval
    
    def check_rate_limit(self) -> bool:
        """Check if operation would exceed rate limit.
        
        Returns:
            True if operation is within rate limits
        """
        recent_ops = len([op for op in self.operation_log 
                         if (datetime.utcnow() - op.get("timestamp", datetime.utcnow())).seconds < 60])
        
        within_limit = recent_ops < self.max_rate_limit
        
        if not within_limit:
            logger.warning(
                "rate_limit_exceeded",
                extra={"recent_operations": recent_ops, "limit": self.max_rate_limit}
            )
        
        return within_limit
    
    def record_approval(self, approver: str, decision: str, 
                       reason: Optional[str] = None) -> ApprovalRecord:
        """Record an approval decision.
        
        Args:
            approver: User providing approval
            decision: Approval decision (approved, rejected, deferred)
            reason: Explanation for the decision
            
        Returns:
            ApprovalRecord for the decision
        """
        if decision not in ("approved", "rejected", "deferred"):
            raise ValueError(f"Invalid decision: {decision}")
        
        record = ApprovalRecord(
            approver=approver,
            decision=decision,
            timestamp=datetime.utcnow(),
            reason=reason
        )
        
        self.approval_records.append(record)
        
        logger.info(
            "approval_recorded",
            extra={
                "approver": approver,
                "decision": decision,
                "reason": reason or "none provided"
            }
        )
        
        return record
    
    def execute_with_oversight(self, operation: Dict[str, Any],
                              handler: Callable) -> Any:
        """Execute operation with trust chain oversight.
        
        Args:
            operation: Operation to execute
            handler: Callable that performs the operation
            
        Returns:
            Result from the operation handler
        """
        try:
            self.validate_input(operation)
            
            if not self.check_rate_limit():
                raise PermissionError("Rate limit exceeded")
            
            risk_level = self.classify_risk(
                operation.get("type", "unknown"),
                operation.get("impact", 0.5)
            )
            
            if self.require_approval(operation, risk_level):
                logger.warning(
                    "human_approval_required",
                    extra={"operation": operation.get("type"), "risk": risk_level.value}
                )
                raise PermissionError("Human approval required for this operation")
            
            result = handler(operation)
            
            self.operation_log.append({
                "operation": operation,
                "timestamp": datetime.utcnow(),
                "risk_level": risk_level.value,
                "status": "completed"
            })
            
            logger.info(
                "operation_executed",
                extra={
                    "operation_type": operation.get("type"),
                    "risk_level": risk_level.value
                }
            )
            
            return result
            
        except (ValueError, PermissionError) as e:
            logger.error("operation_execution_error", extra={"error": str(e)})
            raise
