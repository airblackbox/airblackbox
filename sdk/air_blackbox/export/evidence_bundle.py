"""Self-verifying evidence bundle generator.

Generates a .air-evidence.zip containing:
  - audit_chain.json   (HMAC-SHA256 tamper-evident chain)
  - scan_results.json  (compliance gap analysis)
  - bundle_meta.json   (metadata + HMAC attestation)
  - verify.py          (standalone verifier - no pip install needed)

Usage:
    from air_blackbox.export.evidence_bundle import generate_evidence_zip
    path = generate_evidence_zip(chain_data, scan_results, signing_key="your-key")
    # path is e.g. ./air-evidence-20260504T120000.zip
    # Auditor extracts, runs: python verify.py  -> PASS/FAIL
"""

import hashlib
import hmac
import json
import logging
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_evidence_zip(
    chain_entries: List[Dict[str, Any]],
    scan_results: List[Dict[str, Any]],
    signing_key: str = "air-blackbox-default",
    output_dir: str = ".",
    aibom: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a self-verifying .air-evidence.zip.

    The ZIP contains everything an auditor needs to verify compliance
    evidence independently, including a standalone verify.py that
    uses only Python stdlib (no pip install required).

    Args:
        chain_entries: List of HMAC chain entry dicts (sequence, run_id,
                       record_hash, prev_hash, signature, timestamp).
        scan_results: Compliance scan results from the scanner.
        signing_key: HMAC-SHA256 key used for chain signing.
        output_dir: Directory to write the ZIP to.
        aibom: Optional AI Bill of Materials dict.

    Returns:
        Absolute path to the generated ZIP file.
    """
    now = datetime.utcnow()
    ts = now.strftime("%Y%m%dT%H%M%S")
    zip_name = f"air-evidence-{ts}.zip"
    zip_path = os.path.join(output_dir, zip_name)

    # Build bundle metadata.
    chain_json = json.dumps(chain_entries, indent=2, default=str)
    scan_json = json.dumps(scan_results, indent=2, default=str)

    # Compute content hashes (SHA-256).
    chain_hash = hashlib.sha256(chain_json.encode()).hexdigest()
    scan_hash = hashlib.sha256(scan_json.encode()).hexdigest()

    meta = {
        "air_evidence_bundle": {
            "version": "1.0.0",
            "generated_at": now.isoformat() + "Z",
            "generator": "air-blackbox",
        },
        "contents": {
            "audit_chain": {
                "file": "audit_chain.json",
                "sha256": chain_hash,
                "entries": len(chain_entries),
            },
            "scan_results": {
                "file": "scan_results.json",
                "sha256": scan_hash,
            },
        },
        "attestation": {
            "algorithm": "HMAC-SHA256",
            "signature": "",  # computed below
        },
    }

    if aibom:
        aibom_json = json.dumps(aibom, indent=2, default=str)
        aibom_hash = hashlib.sha256(aibom_json.encode()).hexdigest()
        meta["contents"]["aibom"] = {
            "file": "aibom.json",
            "sha256": aibom_hash,
        }

    # Sign the metadata (with signature field empty during signing).
    meta_for_signing = json.dumps(meta, sort_keys=True).encode()
    sig = hmac.new(signing_key.encode(), meta_for_signing, hashlib.sha256).hexdigest()
    meta["attestation"]["signature"] = sig

    meta_json = json.dumps(meta, indent=2)

    # Write the ZIP.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audit_chain.json", chain_json)
        zf.writestr("scan_results.json", scan_json)
        zf.writestr("bundle_meta.json", meta_json)
        if aibom:
            zf.writestr("aibom.json", aibom_json)
        zf.writestr("verify.py", _VERIFY_SCRIPT)

    logger.info(
        "evidence_bundle_generated",
        extra={
            "path": zip_path,
            "chain_entries": len(chain_entries),
            "chain_hash": chain_hash,
            "scan_hash": scan_hash,
        },
    )

    return os.path.abspath(zip_path)


# ---------------------------------------------------------------------------
# Standalone verify.py script (embedded as a string).
# This script uses ONLY Python stdlib so auditors need zero dependencies.
# ---------------------------------------------------------------------------

_VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""AIR Blackbox Evidence Bundle Verifier.

Verifies the integrity of an AIR Blackbox evidence bundle.
Requires ONLY Python 3.8+ stdlib - no pip install needed.

Usage:
    python verify.py                      # verify with default key
    python verify.py --key YOUR_KEY       # verify with signing key
    python verify.py --chain-only         # verify audit chain only
"""

import argparse
import hashlib
import hmac
import json
import os
import sys


def verify_file_hash(filepath, expected_hash):
    """Verify SHA-256 hash of a file."""
    with open(filepath, "rb") as f:
        actual = hashlib.sha256(f.read()).hexdigest()
    return actual == expected_hash, actual


def verify_chain(chain_entries, signing_key):
    """Verify HMAC-SHA256 audit chain integrity.

    Each entry's signature = HMAC-SHA256(sequence|run_id|record_hash|prev_hash, key).
    Each entry's prev_hash = SHA-256 of the previous entry's JSON.
    """
    if not chain_entries:
        return True, 0, "Empty chain"

    prev_hash = ""
    for i, entry in enumerate(chain_entries):
        seq = entry["sequence"]

        # Check prev_hash linkage.
        if entry.get("prev_hash", "") != prev_hash:
            return False, seq, f"prev_hash mismatch at sequence {seq}"

        # Recompute HMAC signature.
        msg = f"{seq}|{entry['run_id']}|{entry['record_hash']}|{entry.get('prev_hash', '')}"
        expected_sig = hmac.new(
            signing_key.encode(), msg.encode(), hashlib.sha256
        ).hexdigest()

        if entry.get("signature", "") != expected_sig:
            return False, seq, f"signature mismatch at sequence {seq}"

        # Hash this entry for the next one's prev_hash.
        entry_json = json.dumps(entry, sort_keys=False, separators=(",", ":"))
        prev_hash = hashlib.sha256(entry_json.encode()).hexdigest()

    return True, len(chain_entries), "All entries verified"


def verify_attestation(meta, signing_key):
    """Verify the bundle attestation signature."""
    saved_sig = meta["attestation"]["signature"]
    meta["attestation"]["signature"] = ""
    meta_bytes = json.dumps(meta, sort_keys=True).encode()
    expected = hmac.new(signing_key.encode(), meta_bytes, hashlib.sha256).hexdigest()
    meta["attestation"]["signature"] = saved_sig
    return saved_sig == expected


def main():
    parser = argparse.ArgumentParser(description="AIR Blackbox Evidence Verifier")
    parser.add_argument("--key", default="air-blackbox-default",
                        help="HMAC signing key (default: air-blackbox-default)")
    parser.add_argument("--chain-only", action="store_true",
                        help="Only verify the audit chain")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    results = []
    all_pass = True

    print("=" * 60)
    print("AIR Blackbox Evidence Bundle Verification")
    print("=" * 60)
    print()

    # 1. Load and verify metadata.
    meta_path = os.path.join(script_dir, "bundle_meta.json")
    if not os.path.exists(meta_path):
        print("FAIL: bundle_meta.json not found")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    print(f"Bundle generated: {meta['air_evidence_bundle']['generated_at']}")
    print(f"Generator:        {meta['air_evidence_bundle']['generator']}")
    print()

    # 2. Verify attestation signature.
    if not args.chain_only:
        att_ok = verify_attestation(meta, args.key)
        status = "PASS" if att_ok else "FAIL"
        if not att_ok:
            all_pass = False
        print(f"[{status}] Bundle attestation (HMAC-SHA256)")
        results.append(("attestation", att_ok))

    # 3. Verify file hashes.
    if not args.chain_only:
        for name, info in meta.get("contents", {}).items():
            filepath = os.path.join(script_dir, info["file"])
            if not os.path.exists(filepath):
                print(f"[FAIL] {info['file']} - file missing")
                all_pass = False
                results.append((name, False))
                continue
            ok, actual = verify_file_hash(filepath, info["sha256"])
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_pass = False
            print(f"[{status}] {info['file']} (SHA-256)")
            results.append((name, ok))

    # 4. Verify audit chain.
    chain_path = os.path.join(script_dir, "audit_chain.json")
    if os.path.exists(chain_path):
        with open(chain_path) as f:
            chain = json.load(f)
        ok, count, msg = verify_chain(chain, args.key)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"[{status}] Audit chain ({count} entries) - {msg}")
        results.append(("chain", ok))
    else:
        print("[SKIP] No audit_chain.json found")

    # 5. Summary.
    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    if all_pass:
        print(f"RESULT: PASS ({passed}/{total} checks passed)")
        print("This evidence bundle has not been tampered with.")
    else:
        print(f"RESULT: FAIL ({passed}/{total} checks passed)")
        print("WARNING: Evidence integrity could not be verified.")
    print("=" * 60)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
'''
