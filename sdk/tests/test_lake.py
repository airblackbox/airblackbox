"""Tests for the Parquet lake sink and in-lake chain verification."""

import glob
import json
import os
import tempfile

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402

from air_blackbox.lake import export_records, verify_lake  # noqa: E402
from air_blackbox.trust.chain import AuditChain  # noqa: E402


def _write_chained_records(runs_dir, key, n=3):
    chain = AuditChain(runs_dir=runs_dir, signing_key=key)
    for i in range(n):
        chain.write({
            "run_id": f"00000000-0000-0000-0000-00000000000{i}",
            "model": "gpt-4",
            "provider": "openai",
            "endpoint": "/v1/chat/completions",
            "status": "success",
            "tokens": {"prompt": 5, "completion": 5, "total": 10},
            "duration_ms": 7,
            "timestamp": f"2026-07-03T00:00:0{i}Z",
        })


def test_export_and_verify_intact():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "lake-key")
        count = export_records(runs, lake)
        assert count == 3

        result = verify_lake(lake, signing_key="lake-key")
        assert result.intact
        assert result.chain.verified_records == 3
        assert not result.column_mismatches


def test_export_is_incremental():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "lake-key")
        assert export_records(runs, lake) == 3
        # Re-export: nothing new.
        assert export_records(runs, lake) == 0

        # A new record lands, only it gets exported.
        extra_runs = os.path.join(runs, "extra")
        os.makedirs(extra_runs)
        rec = {"run_id": "11111111-0000-0000-0000-000000000000",
               "model": "gpt-4", "status": "success",
               "timestamp": "2026-07-03T00:01:00Z"}
        with open(os.path.join(extra_runs, rec["run_id"] + ".air.json"), "w") as f:
            json.dump(rec, f)
        assert export_records(runs, lake) == 1


def test_tampered_record_json_breaks_chain():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "lake-key")
        export_records(runs, lake)

        # Tamper with the record_json payload of the middle record inside
        # the Parquet file itself.
        part = glob.glob(os.path.join(lake, "**", "*.parquet"), recursive=True)[0]
        table = pq.read_table(part)
        rows = table.to_pylist()
        for row in rows:
            rec = json.loads(row["record_json"])
            if rec["run_id"].endswith("1"):
                rec["model"] = "TAMPERED"
                row["record_json"] = json.dumps(rec, sort_keys=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), part)

        result = verify_lake(lake, signing_key="lake-key")
        assert not result.intact
        assert not result.chain.intact
        assert result.chain.first_break_run_id == "00000000-0000-0000-0000-000000000001"


def test_inconsistent_column_detected():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "lake-key")
        export_records(runs, lake)

        # Tamper with a flattened SQL column while leaving record_json (and
        # therefore the chain) untouched.
        part = glob.glob(os.path.join(lake, "**", "*.parquet"), recursive=True)[0]
        table = pq.read_table(part)
        rows = table.to_pylist()
        rows[0]["model"] = "TAMPERED"
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), part)

        result = verify_lake(lake, signing_key="lake-key")
        assert result.chain.intact          # the verified payload is fine
        assert not result.intact            # but the table lies
        assert any(m["column"] == "model" for m in result.column_mismatches)


def test_wrong_key_breaks_chain():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "lake-key")
        export_records(runs, lake)
        result = verify_lake(lake, signing_key="wrong-key")
        assert not result.intact


def test_keyfile_resolution():
    with tempfile.TemporaryDirectory() as runs, tempfile.TemporaryDirectory() as lake:
        _write_chained_records(runs, "keyfile-key")
        with open(os.path.join(runs, ".air-signing-key"), "w") as f:
            f.write("keyfile-key\n")
        export_records(runs, lake)
        result = verify_lake(lake, runs_dir=runs)
        assert result.intact
