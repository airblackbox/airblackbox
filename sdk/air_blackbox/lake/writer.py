"""Export chained .air.json records into a partitioned Parquet dataset."""

import glob
import json
import os


def _schema():
    import pyarrow as pa

    return pa.schema([
        ("run_id", pa.string()),
        ("timestamp", pa.string()),   # exact RFC3339 string, never a converted type
        ("date", pa.string()),        # hive partition key, derived from timestamp
        ("model", pa.string()),
        ("provider", pa.string()),
        ("endpoint", pa.string()),
        ("status", pa.string()),
        ("tokens_prompt", pa.int64()),
        ("tokens_completion", pa.int64()),
        ("tokens_total", pa.int64()),
        ("duration_ms", pa.int64()),
        ("trace_id", pa.string()),
        ("chain_seq", pa.int64()),
        ("chain_hash", pa.string()),
        # Source of truth: the record exactly as recorded, compact JSON.
        # Verification and replay read this; the columns above exist for SQL.
        ("record_json", pa.string()),
    ])


def _flatten(rec: dict) -> dict:
    tokens = rec.get("tokens") or {}
    timestamp = rec.get("timestamp", "")
    return {
        "run_id": rec.get("run_id", ""),
        "timestamp": timestamp,
        "date": timestamp[:10] if len(timestamp) >= 10 else "unknown",
        "model": rec.get("model", ""),
        "provider": rec.get("provider", ""),
        "endpoint": rec.get("endpoint", ""),
        "status": rec.get("status", ""),
        "tokens_prompt": int(tokens.get("prompt", 0) or 0),
        "tokens_completion": int(tokens.get("completion", 0) or 0),
        "tokens_total": int(tokens.get("total", 0) or 0),
        "duration_ms": int(rec.get("duration_ms", 0) or 0),
        "trace_id": rec.get("trace_id", ""),
        "chain_seq": int(rec.get("chain_seq", 0) or 0),
        "chain_hash": rec.get("chain_hash", ""),
        "record_json": json.dumps(rec, sort_keys=True),
    }


def _existing_run_ids(lake_dir: str) -> set:
    import pyarrow.dataset as ds

    has_parts = glob.glob(os.path.join(lake_dir, "**", "*.parquet"), recursive=True)
    if not has_parts:
        return set()
    dataset = ds.dataset(lake_dir, format="parquet")
    return set(dataset.to_table(columns=["run_id"])["run_id"].to_pylist())


def export_records(runs_dir: str, lake_dir: str, incremental: bool = True) -> int:
    """Export .air.json records from runs_dir into a Parquet dataset.

    The dataset is hive-partitioned by date (date=YYYY-MM-DD/...). With
    incremental=True (the default), run_ids already present in the dataset
    are skipped, so repeated exports append only new records.

    Returns the number of records written.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    skip = _existing_run_ids(lake_dir) if incremental else set()

    rows = []
    for path in sorted(glob.glob(os.path.join(runs_dir, "**", "*.air.json"),
                                 recursive=True)):
        try:
            with open(path) as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if rec.get("run_id") in skip:
            continue
        rows.append(_flatten(rec))

    if not rows:
        return 0

    table = pa.Table.from_pylist(rows, schema=_schema())
    pq.write_to_dataset(table, root_path=lake_dir, partition_cols=["date"])
    return len(rows)
