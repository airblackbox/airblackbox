"""Agent-to-Agent compliance protocol for AIR Blackbox.

This module provides verification and communication protocols that ensure
agents communicating with each other both have proper compliance layers in place.
"""

from .protocol import (
    AgentComplianceCard,
    A2AComplianceGate,
    A2AVerificationResult,
    generate_compliance_card,
    verify_a2a_communication,
)

__all__ = [
    "AgentComplianceCard",
    "A2AComplianceGate",
    "A2AVerificationResult",
    "generate_compliance_card",
    "verify_a2a_communication",
]
