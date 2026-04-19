"""
Bilateral Action Receipt — cryptographic proof of authorization AND execution.

A receipt has two phases:
  1. Authorization: the gate evaluates the covenant and signs the decision
  2. Sealing: after execution, the result is attached and the receipt is
     sealed with a second signature

This gives you both sides of Art. 12:
  - What the agent was ALLOWED to do (authorization)
  - What the agent ACTUALLY did (execution result)

Both signatures use Ed25519 for non-repudiation — any third party can
verify without needing the signing key (unlike HMAC which requires
the shared secret).

The receipt also carries:
  - covenant_hash: which rules were active
  - parent_receipt_id: for cross-agent delegation chains
  - chain_hash: links into the HMAC-SHA256 audit chain
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any

# Ed25519 signing — use cryptography library if available, fall back to
# HMAC-SHA256 if not (still tamper-evident, just not non-repudiable)
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    HAS_ED25519 = True
except ImportError:
    HAS_ED25519 = False

import hmac as hmac_mod


class ReceiptStatus(str, Enum):
    """Lifecycle status of a receipt."""
    AUTHORIZED = "authorized"     # Phase 1: gate approved the action
    DENIED = "denied"             # Phase 1: gate blocked the action
    PENDING_APPROVAL = "pending"  # Phase 1: waiting for human approval
    SEALED = "sealed"             # Phase 2: execution result attached
    FAILED = "failed"             # Phase 2: execution failed


@dataclass
class ActionReceipt:
    """Bilateral receipt for one agent action.

    Phase 1 (authorization):
        Created by Gate.authorize(). Contains the decision, covenant
        hash, and authorization signature.

    Phase 2 (sealing):
        After execution, Gate.seal() attaches the result and seals
        the receipt with a second signature covering the full lifecycle.

    Attributes:
        receipt_id: Unique identifier for this receipt
        agent_id: Which agent requested the action
        action_name: What action was attempted (e.g. "send_email")
        action_category: Action category (e.g. "email", "database")
        payload_hash: SHA-256 of the action payload (not the payload itself)
        covenant_hash: SHA-256 of the covenant that was active
        decision: permit, forbid, or require_approval
        authorized: Whether the action was approved
        parent_receipt_id: Links to the authorizing receipt in delegation chains
        authorization_sig: Ed25519 or HMAC signature of the authorization phase
        result_hash: SHA-256 of the execution result (set during sealing)
        result_status: success, failure, error (set during sealing)
        seal_sig: Ed25519 or HMAC signature of the complete receipt
        chain_hash: Link into the HMAC-SHA256 audit chain
        status: Current lifecycle status
        created_at: When authorization was granted
        sealed_at: When the receipt was sealed with execution result
        metadata: Arbitrary key-value pairs for context
    """
    receipt_id: str = ""
    agent_id: str = ""
    action_name: str = ""
    action_category: str = ""
    payload_hash: str = ""
    covenant_hash: str = ""
    decision: str = ""          # "permit", "forbid", "require_approval"
    authorized: bool = False

    # Delegation
    parent_receipt_id: Optional[str] = None

    # Phase 1 signature
    authorization_sig: str = ""

    # Phase 2 (filled by seal())
    result_hash: str = ""
    result_status: str = ""     # "success", "failure", "error"
    seal_sig: str = ""

    # Chain integration
    chain_hash: str = ""

    # Lifecycle
    status: ReceiptStatus = ReceiptStatus.AUTHORIZED
    created_at: str = ""
    sealed_at: str = ""

    # Context
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.receipt_id:
            self.receipt_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    @property
    def authorization_payload(self) -> bytes:
        """The canonical bytes that the authorization signature covers."""
        data = {
            "receipt_id": self.receipt_id,
            "agent_id": self.agent_id,
            "action_name": self.action_name,
            "action_category": self.action_category,
            "payload_hash": self.payload_hash,
            "covenant_hash": self.covenant_hash,
            "decision": self.decision,
            "authorized": self.authorized,
            "parent_receipt_id": self.parent_receipt_id,
            "created_at": self.created_at,
        }
        return json.dumps(data, sort_keys=True).encode("utf-8")

    @property
    def seal_payload(self) -> bytes:
        """The canonical bytes that the seal signature covers.

        Includes the authorization signature, so the seal covers
        the entire lifecycle — you can't forge a seal without
        having the valid authorization.
        """
        data = {
            "receipt_id": self.receipt_id,
            "authorization_sig": self.authorization_sig,
            "result_hash": self.result_hash,
            "result_status": self.result_status,
            "sealed_at": self.sealed_at,
        }
        return json.dumps(data, sort_keys=True).encode("utf-8")

    def to_dict(self) -> dict:
        """Serialize the receipt to a dict for JSON export."""
        return {
            "receipt_id": self.receipt_id,
            "agent_id": self.agent_id,
            "action_name": self.action_name,
            "action_category": self.action_category,
            "payload_hash": self.payload_hash,
            "covenant_hash": self.covenant_hash,
            "decision": self.decision,
            "authorized": self.authorized,
            "parent_receipt_id": self.parent_receipt_id,
            "authorization_sig": self.authorization_sig,
            "result_hash": self.result_hash,
            "result_status": self.result_status,
            "seal_sig": self.seal_sig,
            "chain_hash": self.chain_hash,
            "status": self.status.value,
            "created_at": self.created_at,
            "sealed_at": self.sealed_at,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def hash_payload(payload: Any) -> str:
    """SHA-256 hash of an action payload. Never stores the payload itself."""
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_result(result: Any) -> str:
    """SHA-256 hash of an execution result."""
    raw = json.dumps(result, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class ReceiptSigner:
    """Signs and verifies receipts using Ed25519 or HMAC-SHA256 fallback.

    Ed25519 is preferred because any third party can verify the signature
    using only the public key — no shared secret needed. This is what
    regulators want: independent verifiability.

    If the cryptography library isn't installed, falls back to HMAC-SHA256
    which still provides tamper evidence but requires the shared key to verify.
    """

    def __init__(self, private_key: Optional[bytes] = None, hmac_key: Optional[str] = None):
        """Initialize the signer.

        Args:
            private_key: Ed25519 private key bytes (32 bytes). If provided,
                         Ed25519 signing is used. If None, generates a new key.
            hmac_key: HMAC-SHA256 key string. Used as fallback if Ed25519
                      is unavailable (cryptography package not installed).
        """
        self._hmac_key = (hmac_key or "air-blackbox-default").encode("utf-8")

        if HAS_ED25519:
            if private_key:
                self._private_key = Ed25519PrivateKey.from_private_bytes(private_key)
            else:
                self._private_key = Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            self.method = "ed25519"
        else:
            self._private_key = None
            self._public_key = None
            self.method = "hmac-sha256"

    @property
    def public_key_bytes(self) -> Optional[bytes]:
        """Export the public key for third-party verification."""
        if self._public_key and HAS_ED25519:
            return self._public_key.public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        return None

    @property
    def public_key_hex(self) -> Optional[str]:
        """Export the public key as hex string."""
        pk = self.public_key_bytes
        return pk.hex() if pk else None

    def sign(self, data: bytes) -> str:
        """Sign data and return the signature as hex string."""
        if HAS_ED25519 and self._private_key:
            sig = self._private_key.sign(data)
            return sig.hex()
        else:
            # HMAC-SHA256 fallback
            h = hmac_mod.new(self._hmac_key, data, hashlib.sha256)
            return h.hexdigest()

    def verify(self, data: bytes, signature_hex: str) -> bool:
        """Verify a signature against data.

        For Ed25519: uses the public key (no secret needed).
        For HMAC: recomputes and compares (requires the shared key).
        """
        try:
            if HAS_ED25519 and self._public_key:
                sig_bytes = bytes.fromhex(signature_hex)
                self._public_key.verify(sig_bytes, data)
                return True
            else:
                expected = hmac_mod.new(self._hmac_key, data, hashlib.sha256).hexdigest()
                return hmac_mod.compare_digest(expected, signature_hex)
        except Exception:
            return False

    def sign_authorization(self, receipt: ActionReceipt) -> str:
        """Sign the authorization phase of a receipt."""
        sig = self.sign(receipt.authorization_payload)
        receipt.authorization_sig = sig
        return sig

    def sign_seal(self, receipt: ActionReceipt) -> str:
        """Sign the seal phase of a receipt."""
        sig = self.sign(receipt.seal_payload)
        receipt.seal_sig = sig
        return sig

    def verify_authorization(self, receipt: ActionReceipt) -> bool:
        """Verify the authorization signature."""
        return self.verify(receipt.authorization_payload, receipt.authorization_sig)

    def verify_seal(self, receipt: ActionReceipt) -> bool:
        """Verify the seal signature."""
        return self.verify(receipt.seal_payload, receipt.seal_sig)

    def verify_full(self, receipt: ActionReceipt) -> tuple[bool, bool]:
        """Verify both signatures. Returns (auth_valid, seal_valid)."""
        auth = self.verify_authorization(receipt)
        seal = self.verify_seal(receipt) if receipt.seal_sig else False
        return auth, seal
