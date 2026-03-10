"""
Replay engine — incident reconstruction and HMAC audit chain verification.

Reads .air.json records and provides:
- Full episode timeline reconstruction
- HMAC-SHA256 chain verification (detect tampering)
- Filtering by time range, model, status
- Detail view for individual runs
"""

import json
import hashlib
import hmac
import os
import glob
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class AuditRecord:
    run_id: str
    timestamp: str
    model: str
    provider: str
    tokens: dict
    duration_ms: int
    status: str
    record_type: str = "llm_call"
    tool_calls: list = field(default_factory=list)
    pii_alerts: list = field(default_factory=list)
    injection_alerts: list = field(default_factory=list)
    error: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class ChainVerification:
    intact: bool
    total_records: int
    verified_records: int
    first_break_at: Optional[int] = None
    first_break_run_id: Optional[str] = None


class ReplayEngine:
    """Loads, filters, and replays .air.json audit records."""

    def __init__(self, runs_dir: str = "./runs"):
        self.runs_dir = runs_dir
        self.records: list[AuditRecord] = []
        self._raw_records: list[dict] = []

    def load(self) -> int:
        """Load all .air.json records from runs directory."""
        if not os.path.isdir(self.runs_dir):
            return 0
        air_files = glob.glob(os.path.join(self.runs_dir, "**/*.air.json"), recursive=True)
        if not air_files:
            air_files = glob.glob(os.path.join(self.runs_dir, "*.air.json"))
        self._raw_records = []
        for fpath in air_files:
            try:
                with open(fpath, "r") as f:
                    rec = json.load(f)
                    self._raw_records.append(rec)
            except (json.JSONDecodeError, IOError):
                continue
        self._raw_records.sort(key=lambda r: r.get("timestamp", ""))
        self.records = [self._parse(r) for r in self._raw_records]
        return len(self.records)

    def _parse(self, raw: dict) -> AuditRecord:
        return AuditRecord(
            run_id=raw.get("run_id", "unknown"),
            timestamp=raw.get("timestamp", ""),
            model=raw.get("model", "unknown"),
            provider=raw.get("provider", "unknown"),
            tokens=raw.get("tokens", {}),
            duration_ms=raw.get("duration_ms", 0),
            status=raw.get("status", "unknown"),
            record_type=raw.get("type", "llm_call"),
            tool_calls=raw.get("tool_calls", []),
            pii_alerts=raw.get("pii_alerts", []),
            injection_alerts=raw.get("injection_alerts", []),
            error=raw.get("error", ""),
            raw=raw,
        )

    def filter(self, since=None, until=None, model=None, status=None) -> list[AuditRecord]:
        """Filter records by criteria."""
        results = self.records
        if since:
            results = [r for r in results if r.timestamp >= since]
        if until:
            results = [r for r in results if r.timestamp <= until]
        if model:
            results = [r for r in results if model.lower() in r.model.lower()]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_run(self, run_id: str) -> Optional[AuditRecord]:
        """Get a specific run by ID (supports partial match)."""
        for r in self.records:
            if r.run_id.startswith(run_id):
                return r
        return None

    def verify_chain(self, signing_key: Optional[str] = None) -> ChainVerification:
        """Verify HMAC-SHA256 audit chain integrity.

        Each record's hash should chain to the next. If any record
        is modified, the chain breaks from that point forward.
        """
        key = (signing_key or os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default")).encode()
        prev_hash = b"genesis"
        verified = 0

        for i, raw in enumerate(self._raw_records):
            record_bytes = json.dumps(raw, sort_keys=True).encode()
            expected_hash = hmac.new(key, prev_hash + record_bytes, hashlib.sha256).digest()

            # Check if record has a stored hash
            stored_hash = raw.get("chain_hash")
            if stored_hash:
                if stored_hash != expected_hash.hex():
                    return ChainVerification(
                        intact=False, total_records=len(self._raw_records),
                        verified_records=verified, first_break_at=i,
                        first_break_run_id=raw.get("run_id"),
                    )
            # Even without stored hashes, we compute the chain
            prev_hash = expected_hash
            verified += 1

        return ChainVerification(
            intact=True, total_records=len(self._raw_records),
            verified_records=verified,
        )

    def get_stats(self) -> dict:
        """Get summary statistics for all records."""
        if not self.records:
            return {}
        models = {}
        providers = {}
        statuses = {"success": 0, "error": 0, "timeout": 0}
        total_tokens = 0
        total_duration = 0
        pii_count = 0
        injection_count = 0

        for r in self.records:
            models[r.model] = models.get(r.model, 0) + 1
            providers[r.provider] = providers.get(r.provider, 0) + 1
            statuses[r.status] = statuses.get(r.status, 0) + 1
            total_tokens += r.tokens.get("total", 0)
            total_duration += r.duration_ms
            pii_count += len(r.pii_alerts)
            injection_count += len(r.injection_alerts)

        return {
            "total_records": len(self.records),
            "models": models,
            "providers": providers,
            "statuses": statuses,
            "total_tokens": total_tokens,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration // len(self.records) if self.records else 0,
            "pii_alerts": pii_count,
            "injection_alerts": injection_count,
            "date_range": (self.records[0].timestamp, self.records[-1].timestamp) if self.records else None,
        }
