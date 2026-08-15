"""
Bilateral Action Receipt - cryptographic proof of authorization AND execution.

A receipt has two phases:
  1. Authorization: the gate evaluates the covenant and signs the decision
  2. Sealing: after execution, the result is attached and the receipt is
     sealed with a second signature

This gives you both sides of Art. 12:
  - What the agent was ALLOWED to do (authorization)
  - What the agent ACTUALLY did (execution result)

Both signatures use Ed25519 for non-repudiation - any third party can
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

# ML-DSA-65 (FIPS 204) post-quantum signing - preferred when available.
# Falls back to Ed25519 if ML-DSA-65 is not available, then to HMAC-SHA256.
#
# Two providers, tried in order:
#   1. pqcrypto (PQClean): ships prebuilt wheels, so it is installable in CI
#      and ordinary dev environments with no native toolchain. This is what
#      the `pqc` extra installs and what CI tests.
#   2. liboqs-python (import name `oqs`): kept as a fallback for
#      environments that already have liboqs built.
# Both implement FIPS 204, so signatures interoperate: a receipt carries its
# public key and either provider (or any FIPS 204 verifier) can check it.
HAS_MLDSA65 = False
HAS_ED25519 = False
_MLDSA_PROVIDER = None

try:
    from pqcrypto.sign import ml_dsa_65 as _pqclean_mldsa65
    HAS_MLDSA65 = True
    _MLDSA_PROVIDER = "pqcrypto"
except ImportError:
    try:
        # liboqs-python. NOTE: the PyPI package is `liboqs-python`; the
        # package named plain `oqs` on PyPI is an unrelated project.
        import oqs as _oqs
        HAS_MLDSA65 = True
        _MLDSA_PROVIDER = "liboqs"
    except ImportError:
        pass


def _oqs_mechanism():
    """liboqs mechanism name: current releases use ML-DSA-65; older ones
    only know the pre-standardization name Dilithium3."""
    enabled = getattr(_oqs, "get_enabled_sig_mechanisms", lambda: [])()
    return "ML-DSA-65" if "ML-DSA-65" in enabled else "Dilithium3"


def _pqcrypto_keygen():
    """pqcrypto renamed generate_keypair() to keygen() in 1.0.0.

    Both names are resolved at call time rather than pinning a version: 1.0.0
    is the current release, and pinning below it would leave installs on an
    old build of a cryptographic dependency, which is the wrong direction for
    this particular library.
    """
    fn = getattr(_pqclean_mldsa65, "keygen", None) or \
        getattr(_pqclean_mldsa65, "generate_keypair", None)
    if fn is None:
        raise RuntimeError(
            "pqcrypto is installed but exposes neither keygen() nor "
            "generate_keypair() for ML-DSA-65; unsupported version")
    return fn()


def mldsa_generate_keypair() -> tuple[bytes, bytes]:
    """Generate an ML-DSA-65 keypair. Returns (public_key, secret_key)."""
    if _MLDSA_PROVIDER == "pqcrypto":
        pk, sk = _pqcrypto_keygen()
        return bytes(pk), bytes(sk)
    if _MLDSA_PROVIDER == "liboqs":
        sig = _oqs.Signature(_oqs_mechanism())
        pk = sig.generate_keypair()
        return bytes(pk), bytes(sig.export_secret_key())
    raise RuntimeError("no ML-DSA-65 provider installed (pip install 'air-blackbox[pqc]')")


def mldsa_sign(secret_key: bytes, data: bytes) -> bytes:
    """Sign data with an ML-DSA-65 secret key (raw FIPS 204 key bytes)."""
    if _MLDSA_PROVIDER == "pqcrypto":
        return bytes(_pqclean_mldsa65.sign(secret_key, data))
    if _MLDSA_PROVIDER == "liboqs":
        sig = _oqs.Signature(_oqs_mechanism(), secret_key=secret_key)
        return bytes(sig.sign(data))
    raise RuntimeError("no ML-DSA-65 provider installed (pip install 'air-blackbox[pqc]')")


def mldsa_verify(public_key: bytes, data: bytes, signature: bytes) -> bool:
    """Verify an ML-DSA-65 signature. Never raises; returns False on failure.

    The two pqcrypto generations disagree about how a *valid* signature is
    reported, and the disagreement is silent and dangerous:

        0.4.0   verify(valid) -> True     verify(invalid) -> False
        1.0.0   verify(valid) -> None     verify(invalid) -> raises

    So `bool(verify(...))` - which this used to do - turns every VALID
    signature into False under 1.0.0. It fails closed rather than open, but it
    would have made the post-quantum path unusable while looking like mass
    tampering. Treat "returned without raising" as the success signal, and
    only trust a returned value when the provider actually returns a bool.
    """
    try:
        if _MLDSA_PROVIDER == "pqcrypto":
            result = _pqclean_mldsa65.verify(public_key, data, signature)
            return result if isinstance(result, bool) else True
        if _MLDSA_PROVIDER == "liboqs":
            return bool(_oqs.Signature(_oqs_mechanism()).verify(
                data, signature, public_key))
    except Exception:
        return False
    return False

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    HAS_ED25519 = True
except ImportError:
    pass

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

    # Self-describing signing info (filled at signing time so the receipt can
    # be verified by a third party from the JSON alone, no signer object needed).
    signing_method: str = ""        # "ed25519", "ML-DSA-65", or "hmac-sha256"
    signing_public_key: str = ""    # hex public key for ed25519 / ML-DSA-65; empty for hmac

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
        the entire lifecycle - you can't forge a seal without
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
            "signing_method": self.signing_method,
            "signing_public_key": self.signing_public_key,
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

    Signing algorithm priority:
      1. ML-DSA-65 (FIPS 204) - post-quantum secure, preferred
      2. Ed25519 - classical, non-repudiable
      3. HMAC-SHA256 - fallback, requires shared key

    ML-DSA-65 and Ed25519 signatures can be verified by third parties
    using only the public key. HMAC requires the shared secret.
    """

    def __init__(self, private_key: Optional[bytes] = None,
                 hmac_key: Optional[str] = None,
                 mldsa_keypair: Optional[tuple[bytes, bytes]] = None):
        """Initialize the signer.

        Key persistence contract (#63): a provided key is ALWAYS honored, so a
        signer reconstructed from persisted key material keeps the same public
        key across restarts - previously issued receipts keep verifying.

        Args:
            private_key: Ed25519 private key bytes (32 bytes). If provided,
                         Ed25519 signing is used with exactly this key - even
                         when ML-DSA-65 is available - because switching
                         algorithms would change the caller's persisted
                         identity out from under it.
            hmac_key: HMAC-SHA256 key string. Used as fallback if neither
                      ML-DSA-65 nor Ed25519 is available.
            mldsa_keypair: (public_key, secret_key) raw ML-DSA-65 bytes from a
                         previous signer's `mldsa_keypair` property. If
                         provided (and the pqc extra is installed), ML-DSA-65
                         signing resumes under the same keypair.

        With no key material provided, the strongest available algorithm is
        used with a freshly generated key: ML-DSA-65, then Ed25519, then HMAC.
        """
        self._hmac_key = (hmac_key or "air-blackbox-default").encode("utf-8")
        self._mldsa_pub: Optional[bytes] = None
        self._mldsa_secret: Optional[bytes] = None
        self._private_key = None
        self._public_key = None

        if HAS_MLDSA65 and mldsa_keypair is not None:
            # Resume a persisted ML-DSA-65 identity.
            self._mldsa_pub, self._mldsa_secret = mldsa_keypair
            self.method = "ML-DSA-65"
        elif HAS_ED25519 and private_key:
            # An explicit Ed25519 key is a persisted identity - honor it.
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_key)
            self._public_key = self._private_key.public_key()
            self.method = "ed25519"
        elif HAS_MLDSA65:
            # Fresh signer: post-quantum preferred.
            self._mldsa_pub, self._mldsa_secret = mldsa_generate_keypair()
            self.method = "ML-DSA-65"
        elif HAS_ED25519:
            self._private_key = Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            self.method = "ed25519"
        else:
            self.method = "hmac-sha256"

    @property
    def mldsa_keypair(self) -> Optional[tuple[bytes, bytes]]:
        """The (public_key, secret_key) raw bytes of an ML-DSA-65 signer, for
        persistence. Pass back via the mldsa_keypair constructor arg to resume
        the same signing identity. None for non-ML-DSA signers."""
        if self._mldsa_pub is not None and self._mldsa_secret is not None:
            return (self._mldsa_pub, self._mldsa_secret)
        return None

    @property
    def public_key_bytes(self) -> Optional[bytes]:
        """Export the public key for third-party verification."""
        if self._mldsa_pub is not None:
            return self._mldsa_pub
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
        """Sign data and return the signature as hex string.

        Uses the highest-priority algorithm available:
          1. ML-DSA-65 (post-quantum)
          2. Ed25519 (classical)
          3. HMAC-SHA256 (shared-secret fallback)
        """
        if self._mldsa_secret is not None:
            return mldsa_sign(self._mldsa_secret, data).hex()
        elif HAS_ED25519 and self._private_key:
            sig = self._private_key.sign(data)
            return sig.hex()
        else:
            # HMAC-SHA256 fallback
            h = hmac_mod.new(self._hmac_key, data, hashlib.sha256)
            return h.hexdigest()

    def verify(self, data: bytes, signature_hex: str) -> bool:
        """Verify a signature against data.

        For ML-DSA-65: uses the public key (post-quantum secure).
        For Ed25519: uses the public key (no secret needed).
        For HMAC: recomputes and compares (requires the shared key).
        """
        try:
            sig_bytes = bytes.fromhex(signature_hex)
            if self._mldsa_pub is not None:
                return mldsa_verify(self._mldsa_pub, data, sig_bytes)
            elif HAS_ED25519 and self._public_key:
                self._public_key.verify(sig_bytes, data)
                return True
            else:
                expected = hmac_mod.new(self._hmac_key, data, hashlib.sha256).hexdigest()
                return hmac_mod.compare_digest(expected, signature_hex)
        except Exception:
            return False

    def sign_authorization(self, receipt: ActionReceipt) -> str:
        """Sign the authorization phase of a receipt.

        Also stamps the receipt with the signing method and public key so a
        third party can verify it later from the receipt JSON alone.
        """
        receipt.signing_method = self.method
        receipt.signing_public_key = self.public_key_hex or ""
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


# ---------------------------------------------------------------------------
# Standalone third-party verification.
#
# verify_receipt(receipt_dict) verifies a receipt using ONLY the information
# embedded in the receipt itself (signing_method, signing_public_key, and the
# signature). It needs no ReceiptSigner instance and no shared secret. This is
# what makes an AIR Blackbox receipt independently verifiable.
#
# Returns (verified: bool, detail: str).
# ---------------------------------------------------------------------------


def _authorization_payload_from_dict(d: dict) -> bytes:
    """Rebuild the exact authorization payload bytes from a receipt dict.

    Must match ActionReceipt.authorization_payload byte-for-byte.
    """
    data = {
        "receipt_id": d.get("receipt_id", ""),
        "agent_id": d.get("agent_id", ""),
        "action_name": d.get("action_name", ""),
        "action_category": d.get("action_category", ""),
        "payload_hash": d.get("payload_hash", ""),
        "covenant_hash": d.get("covenant_hash", ""),
        "decision": d.get("decision", ""),
        "authorized": d.get("authorized", False),
        "parent_receipt_id": d.get("parent_receipt_id", None),
        "created_at": d.get("created_at", ""),
    }
    return json.dumps(data, sort_keys=True).encode("utf-8")


def verify_receipt(receipt_dict: dict,
                   expected_public_key: str | None = None) -> tuple[bool, str]:
    """Verify a receipt's authorization signature from the receipt JSON alone.

    Uses the embedded signing_method, signing_public_key, and
    authorization_sig. No signer object, no shared secret.

    Authenticity vs. consistency: with no expected_public_key, this proves the
    receipt is internally *consistent* (signature matches its own embedded
    key) - NOT that it came from a trusted signer, since an attacker can embed
    their own key. Pass expected_public_key (the hex of the key you trust -
    e.g. the tenant's published key or the key that signed the evidence
    bundle) to also verify *authenticity*: a receipt signed by any other key
    is rejected.

    Returns:
        (verified, detail) - verified is True only if the signature is valid,
        the method is asymmetric (independently verifiable), and - when an
        expected key is given - the signing key matches it.
    """
    method = receipt_dict.get("signing_method", "")
    pub_hex = receipt_dict.get("signing_public_key", "")
    sig_hex = receipt_dict.get("authorization_sig", "")

    if not sig_hex:
        return False, "no authorization signature present"

    if expected_public_key and method in ("ed25519", "ML-DSA-65"):
        if not pub_hex or pub_hex.strip().lower() != expected_public_key.strip().lower():
            return False, ("receipt is signed by a key that does not match the "
                           "expected/trusted public key (authenticity check "
                           "failed)")

    payload = _authorization_payload_from_dict(receipt_dict)

    if method == "ed25519":
        if not HAS_ED25519:
            return False, "ed25519 receipt but cryptography not installed to verify"
        if not pub_hex:
            return False, "ed25519 receipt missing public key"
        try:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
            pub.verify(bytes.fromhex(sig_hex), payload)
            return True, "verified (ed25519, third-party verifiable)"
        except Exception:
            return False, "ed25519 signature INVALID (tampered or wrong key)"

    if method == "ML-DSA-65":
        if not HAS_MLDSA65:
            return False, "ML-DSA-65 receipt but oqs not installed to verify"
        if not pub_hex:
            return False, "ML-DSA-65 receipt missing public key"
        try:
            ok = mldsa_verify(bytes.fromhex(pub_hex), payload,
                              bytes.fromhex(sig_hex))
            return (True, "verified (ML-DSA-65, post-quantum, third-party verifiable)") if ok \
                else (False, "ML-DSA-65 signature INVALID (tampered or wrong key)")
        except Exception as e:
            return False, f"ML-DSA-65 verification error: {e}"

    if method == "hmac-sha256":
        return False, ("hmac-sha256 is not third-party verifiable; it needs the "
                       "shared secret. Re-sign with ed25519 or ML-DSA-65 for "
                       "independent verification.")

    return False, f"unknown or missing signing_method: {method!r}"
