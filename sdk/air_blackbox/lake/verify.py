"""Chain verification directly over the Parquet dataset.

Two layers of checking:

1. Chain integrity: the record_json column carries each record exactly as
   recorded; the rows are ordered by (chain_seq, timestamp) and run through
   the same HMAC-SHA256 chain walk the replay engine uses. Tampering with
   any record breaks every record after it.
2. Column consistency: the flattened SQL columns must agree with
   record_json, so an attacker cannot present clean analytics columns while
   the verified payload says otherwise (or vice versa).

The equivalent walk runs anywhere the table does - a Spark UDF, a DuckDB
query, a notebook - because verification needs only the rows and the key.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from air_blackbox.replay.engine import ChainVerification, verify_records

# Flattened columns that must agree with the verified record_json payload.
_CONSISTENCY_COLUMNS = (
    ("run_id", "run_id"),
    ("timestamp", "timestamp"),
    ("model", "model"),
    ("provider", "provider"),
    ("endpoint", "endpoint"),
    ("status", "status"),
    ("chain_hash", "chain_hash"),
)


@dataclass
class LakeVerification:
    chain: ChainVerification
    column_mismatches: list = field(default_factory=list)

    @property
    def intact(self) -> bool:
        return self.chain.intact and not self.column_mismatches


def _resolve_key(signing_key: Optional[str], runs_dir: Optional[str]) -> bytes:
    """Same resolution order as the replay engine: explicit key, env var,
    the gateway's generated keyfile, then the development default."""
    if signing_key:
        return signing_key.encode()
    env = os.environ.get("TRUST_SIGNING_KEY")
    if env:
        return env.encode()
    if runs_dir:
        try:
            with open(os.path.join(runs_dir, ".air-signing-key")) as f:
                key = f.read().strip()
                if key:
                    return key.encode()
        except OSError:
            # The keyfile is an optional convenience source; fall through
            # to the development default when it doesn't exist.
            pass
    return b"air-blackbox-default"


def verify_lake(lake_dir: str, signing_key: Optional[str] = None,
                runs_dir: Optional[str] = None) -> LakeVerification:
    """Verify the HMAC audit chain over a Parquet lake dataset."""
    import pyarrow.dataset as ds

    # The date column is stored in the files themselves, so hive partition
    # inference is unnecessary (and its dictionary-typed column would clash
    # with the string column when fragments are merged).
    dataset = ds.dataset(lake_dir, format="parquet")
    rows = dataset.to_table().to_pylist()
    rows.sort(key=lambda r: (r.get("chain_seq") or 0, r.get("timestamp") or ""))

    mismatches = []
    records = []
    for row in rows:
        rec = json.loads(row["record_json"])
        records.append(rec)
        for col, json_field in _CONSISTENCY_COLUMNS:
            if (row.get(col) or "") != (rec.get(json_field) or ""):
                mismatches.append({
                    "run_id": row.get("run_id"),
                    "column": col,
                    "column_value": row.get(col),
                    "record_value": rec.get(json_field),
                })
        tokens = rec.get("tokens") or {}
        if int(row.get("tokens_total") or 0) != int(tokens.get("total", 0) or 0):
            mismatches.append({
                "run_id": row.get("run_id"),
                "column": "tokens_total",
                "column_value": row.get("tokens_total"),
                "record_value": tokens.get("total"),
            })
        if int(row.get("chain_seq") or 0) != int(rec.get("chain_seq", 0) or 0):
            mismatches.append({
                "run_id": row.get("run_id"),
                "column": "chain_seq",
                "column_value": row.get("chain_seq"),
                "record_value": rec.get("chain_seq"),
            })

    key = _resolve_key(signing_key, runs_dir)
    chain = verify_records(records, key)
    return LakeVerification(chain=chain, column_mismatches=mismatches)
