#!/usr/bin/env python3
"""Verify an AIR Blackbox audit chain.

See: https://airblackbox.ai/spec/audit-chain-v1

Usage:
    python verify_chain.py ./runs --key your-signing-key
    python verify_chain.py ./runs  # uses default key
"""

import argparse
import glob
import hashlib
import hmac
import json
import os
import sys


def load_records(runs_dir: str) -> list[dict]:
    """Load and sort .air.json records by timestamp."""
    records = []
    for fpath in glob.glob(os.path.join(runs_dir, "**/*.air.json"), recursive=True):
        try:
            with open(fpath) as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            print(f"  WARN: Could not read {fpath}", file=sys.stderr)
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def verify(records: list[dict], signing_key: str) -> tuple[bool, int, int]:
    """Verify chain integrity. Returns (intact, verified, total)."""
    key = signing_key.encode("utf-8")
    prev_hash = b"genesis"

    for i, record in enumerate(records):
        record_clean = {k: v for k, v in record.items() if k != "chain_hash"}
        record_bytes = json.dumps(record_clean, sort_keys=True).encode("utf-8")
        expected = hmac.new(key, prev_hash + record_bytes, hashlib.sha256)

        stored = record.get("chain_hash")
        if stored and stored != expected.hexdigest():
            return False, i, len(records)

        prev_hash = expected.digest()

    return True, len(records), len(records)


def main():
    parser = argparse.ArgumentParser(description="Verify AIR Blackbox audit chain")
    parser.add_argument("runs_dir", help="Path to runs directory")
    parser.add_argument("--key", default="air-blackbox-default", help="HMAC signing key")
    args = parser.parse_args()

    records = load_records(args.runs_dir)
    if not records:
        print("No .air.json records found.")
        sys.exit(1)

    print(f"Loaded {len(records)} records from {args.runs_dir}")
    print(f"Date range: {records[0].get('timestamp', '?')} → {records[-1].get('timestamp', '?')}")
    print()

    intact, verified, total = verify(records, args.key)

    if intact:
        print(f"PASS: Chain intact. {verified}/{total} records verified.")
        sys.exit(0)
    else:
        print(f"FAIL: Chain broken at record {verified} of {total}.")
        print(f"  Record: {records[verified].get('run_id', '?')}")
        print(f"  Timestamp: {records[verified].get('timestamp', '?')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
