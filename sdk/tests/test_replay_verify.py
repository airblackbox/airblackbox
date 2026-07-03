"""Regression tests for ReplayEngine.verify_chain.

The chain hash is computed by trust.chain.AuditChain.write as
HMAC-SHA256(key, prev_hash || json.dumps(record_without_chain_hash, sort_keys=True))
with prev_hash starting at b"genesis" and advancing to the raw digest.
The replay engine must verify exactly that construction, and must not
report "verified" for records that carry no chain_hash at all.
"""

import json
import os
import tempfile

from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.trust.chain import AuditChain


def _write_chained_records(runs_dir, key, n=3):
    chain = AuditChain(runs_dir=runs_dir, signing_key=key)
    for i in range(n):
        chain.write({
            "run_id": f"00000000-0000-0000-0000-00000000000{i}",
            "model": "gpt-4",
            "tokens": {"total": 10},
            "status": "success",
            "timestamp": f"2026-07-03T00:00:0{i}Z",
        })


def test_untampered_trust_layer_chain_verifies():
    with tempfile.TemporaryDirectory() as d:
        _write_chained_records(d, "test-key")
        engine = ReplayEngine(runs_dir=d)
        engine.load()
        result = engine.verify_chain(signing_key="test-key")
        assert result.intact
        assert result.verified_records == 3
        assert result.records_with_hash == 3


def test_tampered_record_breaks_chain():
    with tempfile.TemporaryDirectory() as d:
        _write_chained_records(d, "test-key")
        # Tamper with the middle record's content.
        path = os.path.join(d, "00000000-0000-0000-0000-000000000001.air.json")
        with open(path) as f:
            rec = json.load(f)
        rec["model"] = "TAMPERED"
        with open(path, "w") as f:
            json.dump(rec, f)

        engine = ReplayEngine(runs_dir=d)
        engine.load()
        result = engine.verify_chain(signing_key="test-key")
        assert not result.intact
        assert result.first_break_at == 1
        assert result.first_break_run_id == "00000000-0000-0000-0000-000000000001"


def test_wrong_key_breaks_chain():
    with tempfile.TemporaryDirectory() as d:
        _write_chained_records(d, "test-key")
        engine = ReplayEngine(runs_dir=d)
        engine.load()
        result = engine.verify_chain(signing_key="wrong-key")
        assert not result.intact


def test_records_without_chain_hash_are_not_counted_verified():
    with tempfile.TemporaryDirectory() as d:
        # Gateway-style records: no chain_hash field.
        for i in range(3):
            rec = {
                "run_id": f"11111111-0000-0000-0000-00000000000{i}",
                "model": "gpt-4",
                "tokens": {"total": 10},
                "status": "success",
                "timestamp": f"2026-07-03T00:00:0{i}Z",
            }
            with open(os.path.join(d, rec["run_id"] + ".air.json"), "w") as f:
                json.dump(rec, f)

        engine = ReplayEngine(runs_dir=d)
        engine.load()
        result = engine.verify_chain(signing_key="test-key")
        # Nothing to check, so nothing may be reported as verified.
        assert result.records_with_hash == 0
        assert result.verified_records == 0
        assert result.total_records == 3
