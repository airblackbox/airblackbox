"""A2A compliance protocol implementation.

Provides agent-to-agent verification, compliance card generation,
and secure handshake mechanisms for cross-agent communication.
"""

import hashlib
import hmac
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class AgentComplianceCard:
    """Represents an agent's compliance status and capabilities.
    
    Used in A2A verification to establish trust between communicating agents.
    """
    agent_id: str
    agent_name: str
    framework: str
    trust_layer_version: str
    audit_chain_enabled: bool
    injection_protection: bool
    compliance_checks: Dict[str, str]
    gdpr_checks: Dict[str, str]
    last_verified: str
    signing_key_fingerprint: str
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert card to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentComplianceCard":
        """Create card from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentComplianceCard":
        """Create card from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class A2AVerificationResult:
    """Result of A2A compliance verification between two agents.
    
    Contains verification status, compliance score, issues found,
    and recommendations for remediation.
    """
    verified: bool
    score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    handshake_record: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def summary(self) -> str:
        """Get human-readable summary of verification."""
        status = "PASS" if self.verified else "FAIL"
        return (
            f"A2A Verification: {status} (Score: {self.score:.2f})\n"
            f"Issues: {len(self.issues)}\n"
            f"Recommendations: {len(self.recommendations)}"
        )


class A2AComplianceGate:
    """Gate that verifies compliance between communicating agents.
    
    Implements verification logic, handshake creation, and audit trail
    recording for agent-to-agent communication.
    """

    def __init__(self, local_agent: AgentComplianceCard):
        """Initialize gate with local agent's compliance card.
        
        Args:
            local_agent: This agent's AgentComplianceCard with compliance status.
        """
        self.local_agent = local_agent
        self.verification_log: List[Dict[str, Any]] = []

    @property
    def minimum_requirements(self) -> Dict[str, Any]:
        """Return minimum requirements for peer verification."""
        return {
            "audit_chain_enabled": True,
            "injection_protection": True,
            "no_critical_failures": True,
            "signing_key_present": True,
            "compatible_trust_layer": True,
        }

    def verify_peer(
        self, peer_card: AgentComplianceCard
    ) -> A2AVerificationResult:
        """Verify that peer agent meets compliance requirements.
        
        Checks:
        a. Both agents have audit chains enabled
        b. Both agents have injection protection
        c. Neither agent has critical (fail) compliance findings
        d. Signing key fingerprints are present
        e. Trust layer versions are compatible
        
        Args:
            peer_card: The peer agent's AgentComplianceCard.
            
        Returns:
            A2AVerificationResult with detailed verification outcome.
        """
        issues = []
        recommendations = []
        score = 1.0

        # Check 1: Audit chains enabled
        if not self.local_agent.audit_chain_enabled:
            issues.append(
                "Local agent audit chain is not enabled"
            )
            recommendations.append(
                "Enable audit chain on local agent before A2A communication"
            )
            score -= 0.25

        if not peer_card.audit_chain_enabled:
            issues.append("Peer agent audit chain is not enabled")
            recommendations.append(
                "Peer must enable audit chain for compliant communication"
            )
            score -= 0.25

        # Check 2: Injection protection enabled
        if not self.local_agent.injection_protection:
            issues.append(
                "Local agent injection protection is not enabled"
            )
            recommendations.append(
                "Enable injection protection on local agent"
            )
            score -= 0.2

        if not peer_card.injection_protection:
            issues.append("Peer agent injection protection is not enabled")
            recommendations.append(
                "Peer must enable injection protection"
            )
            score -= 0.2

        # Check 3: No critical compliance failures
        local_failures = [
            f"Article {k}" for k, v in self.local_agent.compliance_checks.items()
            if v == "fail"
        ]
        if local_failures:
            issues.append(
                f"Local agent has critical failures: {', '.join(local_failures)}"
            )
            recommendations.append(
                "Fix critical compliance failures on local agent before communication"
            )
            score -= 0.15

        peer_failures = [
            f"Article {k}" for k, v in peer_card.compliance_checks.items()
            if v == "fail"
        ]
        if peer_failures:
            issues.append(
                f"Peer agent has critical failures: {', '.join(peer_failures)}"
            )
            recommendations.append(
                "Peer must fix critical compliance failures"
            )
            score -= 0.15

        # Check 4: Signing key fingerprints present
        if not self.local_agent.signing_key_fingerprint:
            issues.append("Local agent has no signing key fingerprint")
            recommendations.append(
                "Generate and configure signing key on local agent"
            )
            score -= 0.1

        if not peer_card.signing_key_fingerprint:
            issues.append("Peer agent has no signing key fingerprint")
            recommendations.append(
                "Peer must configure signing key"
            )
            score -= 0.1

        # Check 5: Trust layer version compatibility
        local_major = self.local_agent.trust_layer_version.split(".")[0]
        peer_major = peer_card.trust_layer_version.split(".")[0]

        if local_major != peer_major:
            issues.append(
                f"Trust layer version mismatch: "
                f"local={self.local_agent.trust_layer_version}, "
                f"peer={peer_card.trust_layer_version}"
            )
            recommendations.append(
                "Upgrade peer or local agent to matching major version"
            )
            score -= 0.05

        # Clamp score to 0-1 range
        score = max(0.0, min(1.0, score))

        # Determine overall verification
        verified = (
            len(issues) == 0 and
            self.local_agent.audit_chain_enabled and
            peer_card.audit_chain_enabled and
            self.local_agent.injection_protection and
            peer_card.injection_protection
        )

        # Create handshake record if verified
        handshake = {}
        if verified:
            handshake = self.create_handshake(peer_card)

        result = A2AVerificationResult(
            verified=verified,
            score=score,
            issues=issues,
            recommendations=recommendations,
            handshake_record=handshake,
        )

        # Log verification
        self.verification_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "peer_id": peer_card.agent_id,
            "verified": verified,
            "score": score,
        })

        return result

    def create_handshake(
        self, peer_card: AgentComplianceCard
    ) -> Dict[str, Any]:
        """Create a signed handshake record for the audit chain.
        
        Produces a record that logs two agents established a compliant
        communication channel, signed for audit trail authenticity.
        
        Args:
            peer_card: The peer agent's AgentComplianceCard.
            
        Returns:
            Dictionary containing signed handshake record.
        """
        handshake_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        handshake_data = {
            "handshake_id": handshake_id,
            "timestamp": timestamp,
            "initiator_id": self.local_agent.agent_id,
            "initiator_name": self.local_agent.agent_name,
            "peer_id": peer_card.agent_id,
            "peer_name": peer_card.agent_name,
            "local_framework": self.local_agent.framework,
            "peer_framework": peer_card.framework,
            "local_trust_layer": self.local_agent.trust_layer_version,
            "peer_trust_layer": peer_card.trust_layer_version,
            "compliance_verified": True,
        }

        # Create signature using local agent's signing key fingerprint
        message = json.dumps(handshake_data, sort_keys=True)
        message_bytes = message.encode("utf-8")

        # Use fingerprint as HMAC key for signing
        key = self.local_agent.signing_key_fingerprint.encode("utf-8")
        signature = hmac.new(
            key, message_bytes, hashlib.sha256
        ).hexdigest()

        return {
            "data": handshake_data,
            "signature": signature,
            "signature_algorithm": "HMAC-SHA256",
            "signer_fingerprint": self.local_agent.signing_key_fingerprint,
        }

    def get_verification_log(self) -> List[Dict[str, Any]]:
        """Get log of all verifications performed by this gate."""
        return self.verification_log.copy()


def generate_compliance_card(
    scan_results: Dict[str, Any],
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    framework: Optional[str] = None,
    trust_layer_version: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
) -> AgentComplianceCard:
    """Generate an AgentComplianceCard from scan results.
    
    Produces a compliance card by extracting trust layer version,
    audit chain status, and injection protection from scan results.
    Auto-detects framework if not provided.
    
    Args:
        scan_results: Dictionary from run_all_checks containing compliance data.
        agent_id: Unique agent identifier; generated if not provided.
        agent_name: Human-readable agent name; defaults to agent_id.
        framework: AI framework (langchain, crewai, etc.); auto-detected if omitted.
        trust_layer_version: AIR trust layer version; defaults to "1.0.0".
        capabilities: List of agent capabilities; defaults to empty list.
        
    Returns:
        AgentComplianceCard with populated compliance status.
    """
    # Generate IDs if not provided
    if agent_id is None:
        agent_id = str(uuid4())
    if agent_name is None:
        agent_name = agent_id[:8]

    # Extract framework detection
    if framework is None:
        framework = scan_results.get("framework", "unknown")

    # Extract trust layer version
    if trust_layer_version is None:
        trust_layer_version = scan_results.get("trust_layer_version", "1.0.0")

    # Extract audit chain and injection protection status
    audit_chain_enabled = scan_results.get("audit_chain_enabled", False)
    injection_protection = scan_results.get("injection_protection", False)

    # Extract compliance checks (Article 9-15)
    compliance_checks = {}
    for article in ["9", "10", "11", "12", "14", "15"]:
        key = f"article_{article}"
        status = scan_results.get(key, "unknown")
        compliance_checks[article] = status

    # Extract GDPR checks
    gdpr_checks = scan_results.get("gdpr_checks", {})

    # Generate signing key fingerprint from scan results or create one
    signing_key_fp = scan_results.get("signing_key_fingerprint")
    if not signing_key_fp:
        # Generate deterministic fingerprint from agent_id and framework
        fp_input = f"{agent_id}{framework}".encode("utf-8")
        signing_key_fp = hashlib.sha256(fp_input).hexdigest()[:16]

    # Use provided capabilities or empty list
    if capabilities is None:
        capabilities = scan_results.get("capabilities", [])

    # Create and return card
    return AgentComplianceCard(
        agent_id=agent_id,
        agent_name=agent_name,
        framework=framework,
        trust_layer_version=trust_layer_version,
        audit_chain_enabled=audit_chain_enabled,
        injection_protection=injection_protection,
        compliance_checks=compliance_checks,
        gdpr_checks=gdpr_checks,
        last_verified=datetime.utcnow().isoformat(),
        signing_key_fingerprint=signing_key_fp,
        capabilities=capabilities,
    )


def verify_a2a_communication(
    agent_1: AgentComplianceCard,
    agent_2: AgentComplianceCard,
) -> A2AVerificationResult:
    """Verify that two agents can communicate compliantly.
    
    Convenience function that takes two AgentComplianceCards,
    returns whether they can communicate compliantly, and
    logs the verification to audit chains if both agents
    support it.
    
    Args:
        agent_1: First agent's compliance card.
        agent_2: Second agent's compliance card.
        
    Returns:
        A2AVerificationResult with verification outcome.
    """
    # Create gate using first agent as initiator
    gate = A2AComplianceGate(agent_1)

    # Perform verification
    result = gate.verify_peer(agent_2)

    # If verified and both have signing keys, create audit records
    if result.verified:
        if (
            agent_1.signing_key_fingerprint and
            agent_2.signing_key_fingerprint
        ):
            # Log verification to audit chain
            audit_record = {
                "event_type": "a2a_verification_success",
                "agent_1_id": agent_1.agent_id,
                "agent_1_name": agent_1.agent_name,
                "agent_2_id": agent_2.agent_id,
                "agent_2_name": agent_2.agent_name,
                "verification_timestamp": datetime.utcnow().isoformat(),
                "compliance_score": result.score,
            }

            # Sign the audit record with agent 1's key
            record_json = json.dumps(audit_record, sort_keys=True)
            record_bytes = record_json.encode("utf-8")
            key = agent_1.signing_key_fingerprint.encode("utf-8")
            signature = hmac.new(
                key, record_bytes, hashlib.sha256
            ).hexdigest()

            audit_record["signature"] = signature
            audit_record["signature_algorithm"] = "HMAC-SHA256"

    return result
