"""
HMAC-SHA256 Audit Chain — shared chain state for all trust layers.

Implements the AIR Blackbox Audit Chain Specification v1.0.
See: docs/spec/audit-chain-v1.md

Each record's chain_hash depends on the previous record's hash,
creating a tamper-evident sequence. Modifying any record invalidates
all subsequent hashes.

Usage:
    from air_blackbox.trust.chain import AuditChain

    chain = AuditChain(runs_dir="./runs", signing_key="my-secret")
    chain.write(record)  # Adds chain_hash and writes .air.json
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AuditChain:
    """Thread-safe HMAC-SHA256 audit chain writer.

    Maintains chain state across writes so each record's hash
    links to the previous one per the Audit Chain Spec v1.0.
    """

    # Genesis hash — the initial previous_hash for the first record
    GENESIS = b"genesis"

    def __init__(
        self,
        runs_dir: str = "./runs",
        signing_key: Optional[str] = None,
    ):
        self.runs_dir = runs_dir
        self._key = (
            signing_key
            or os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default")
        ).encode("utf-8")
        self._prev_hash = self.GENESIS
        self._lock = threading.Lock()
        self._record_count = 0
        os.makedirs(self.runs_dir, exist_ok=True)

    def write(self, record: dict) -> Optional[str]:
        """Write a record with chain_hash to the runs directory.

        Computes HMAC-SHA256(key, prev_hash || JSON(record)) and stores
        the result in record["chain_hash"]. Then writes to disk.

        Args:
            record: The audit record dict (must have "run_id").

        Returns:
            The chain_hash hex string, or None if write failed.
        """
        with self._lock:
            try:
                # Ensure required fields
                if "run_id" not in record:
                    record["run_id"] = str(uuid.uuid4())
                if "version" not in record:
                    record["version"] = "1.0.0"
                if "timestamp" not in record:
                    record["timestamp"] = datetime.utcnow().isoformat() + "Z"

                # Compute chain hash per spec: HMAC(key, prev_hash || JSON(record))
                record_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
                h = hmac.new(
                    self._key, self._prev_hash + record_bytes, hashlib.sha256
                )
                chain_hash = h.hexdigest()
                record["chain_hash"] = chain_hash

                # Write .air.json file
                fname = f"{record['run_id']}.air.json"
                fpath = os.path.join(self.runs_dir, fname)
                with open(fpath, "w") as f:
                    json.dump(record, f, indent=2)

                # Advance chain state
                self._prev_hash = h.digest()
                self._record_count += 1

                return chain_hash

            except Exception:
                # Non-blocking: chain failure never breaks the agent
                return None

    @property
    def record_count(self) -> int:
        """Number of records written through this chain instance."""
        return self._record_count

    @property
    def current_hash(self) -> str:
        """Current chain head hash (hex-encoded)."""
        if self._prev_hash == self.GENESIS:
            return "genesis"
        return self._prev_hash.hex()


# Compliance helpers: audit logging, risk classification, event tracking

def audit_log(action: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Log an audit trail entry for compliance record-keeping (Art 12)."""
    logger.info("audit_trail action=%s details=%s", action, details or {})


def log_action(action_type: str, authorized_by: str = "system") -> None:
    """Record an action with delegation tracking (Art 14)."""
    logger.info("action_log type=%s authorized_by=%s", action_type, authorized_by)


@dataclass
class RiskClassification:
    """Risk classification for AI operations (Art 9).

    Attributes:
        level: Risk level (critical, high, medium, low)
        category: Risk category
        requires_human_approval: Whether human oversight is needed
    """
    level: str
    category: str
    requires_human_approval: bool = False

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate that the risk context contains required fields."""
        required = {"operation", "scope"}
        return required.issubset(context.keys())
