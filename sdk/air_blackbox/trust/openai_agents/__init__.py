"""OpenAI agents trust layer and compliance integration.

Provides compliance controls, monitoring, and oversight for
OpenAI-based agent implementations.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

__all__ = []


def validate_agent_config(config: Dict[str, Any]) -> bool:
    """Validate OpenAI agent configuration.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_fields = ["model", "instructions"]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
    
    logger.info("agent_config_validated", extra={"model": config.get("model")})
    return True


def monitor_agent_output(output: str, content_filter: Optional[callable] = None) -> bool:
    """Monitor and filter agent outputs for compliance.
    
    Args:
        output: Agent output text
        content_filter: Optional filtering function
        
    Returns:
        True if output passes compliance checks
    """
    try:
        if not output or not isinstance(output, str):
            raise ValueError("Output must be a non-empty string")
        
        if content_filter and not content_filter(output):
            logger.warning("agent_output_filtered")
            return False
        
        logger.info("agent_output_compliance_check_passed")
        return True
        
    except ValueError as e:
        logger.error("output_validation_error", extra={"error": str(e)})
        raise
