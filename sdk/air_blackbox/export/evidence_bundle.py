"""Self-verifying evidence bundle generator.

Generates a .air-evidence.zip containing:
  - audit_chain.json   (the real .air.json records, in write order)
  - scan_results.json  (compliance scan output)
  - bundle_meta.json   (manifest with SHA-256 of each file)
  - verify.py          (standalone verifier - stdlib only, no pip install)

An auditor extracts the ZIP and runs:  python verify.py --key <signing-key>
and gets PASS/FAIL. The verifier recomputes the production HMAC-SHA256 audit
chain exactly as air_blackbox.trust.chain.AuditChain writes it.
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
    scan_results: Any,
    signing_key: str = "air-blackbox-default",
    output_dir: str = ".",
    aibom: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a self-verifying .air-evidence.zip.

    Args:
        chain_entries: the real audit records (each a dict with a chain_hash),
                       in the order they were written.
        scan_results: compliance scan results (any JSON-serializable structure).
        signing_key: the HMAC key the chain was signed with.
        output_dir: directory to write the ZIP to.
        aibom: optional AI Bill of Materials dict.

    Returns:
        Absolute path to the generated ZIP.
    """
    now = datetime.utcnow()
    ts = now.strftime("%Y%m%dT%H%M%S")
    zip_path = os.path.join(output_dir, f"air-evidence-{ts}.zip")

    chain_json = json.dumps(chain_entries, indent=2, default=str)
    scan_json = json.dumps(scan_results, indent=2, default=str)

    meta = {
        "air_evidence_bundle": {
            "version": "1.1.0",
            "generated_at": now.isoformat() + "Z",
            "generator": "air-blackbox",
            "chain_algorithm": "HMAC-SHA256 (prev_hash || json.dumps(record, sort_keys=True))",
        },
        "contents": {
            "audit_chain": {
                "file": "audit_chain.json",
                "sha256": hashlib.sha256(chain_json.encode()).hexdigest(),
                "entries": len(chain_entries),
            },
            "scan_results": {
                "file": "scan_results.json",
                "sha256": hashlib.sha256(scan_json.encode()).hexdigest(),
            },
        },
    }
    if aibom:
        aibom_json = json.dumps(aibom, indent=2, default=str)
        meta["contents"]["aibom"] = {
            "file": "aibom.json",
            "sha256": hashlib.sha256(aibom_json.encode()).hexdigest(),
        }

    meta_json = json.dumps(meta, indent=2)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("audit_chain.json", chain_json)
        zf.writestr("scan_results.json", scan_json)
        zf.writestr("bundle_meta.json", meta_json)
        if aibom:
            zf.writestr("aibom.json", aibom_json)
        zf.writestr("verify.py", _VERIFY_SCRIPT)

    logger.info("evidence_bundle_generated path=%s entries=%d", zip_path, len(chain_entries))
    return os.path.abspath(zip_path)


# ---------------------------------------------------------------------------
# Standalone verify.py - stdlib only, no pip install required.
# Mirrors air_blackbox.trust.chain.AuditChain byte-for-byte:
#   chain_hash = HMAC-SHA256(key, prev_hash || json.dumps(record, sort_keys=True))
#   prev_hash starts at b"genesis" and advances to the raw digest each step.
# ---------------------------------------------------------------------------

_VERIFY_SCRIPT = '''#!/usr/bin/env python3
"""AIR Blackbox Evidence Bundle Verifier.

Verifies an AIR Blackbox evidence bundle using ONLY the Python standard library.
No pip install required. Run from inside the extracted bundle directory:

    python verify.py --key YOUR_SIGNING_KEY

Exit code 0 = PASS (untampered). Exit code 1 = FAIL.
"""

import argparse
import hashlib
import hmac
import json
import os
import sys


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_chain(records, signing_key):
    """Recompute the production HMAC-SHA256 audit chain.

    Matches air_blackbox.trust.chain.AuditChain exactly:
      record_bytes = json.dumps(record_without_chain_hash, sort_keys=True)
      chain_hash   = HMAC-SHA256(key, prev_hash || record_bytes).hexdigest()
      prev_hash advances to the raw .digest() after each record.
    """
    if not records:
        return True, 0, "empty chain"
    key = signing_key.encode("utf-8")
    prev = b"genesis"
    for i, rec in enumerate(records):
        stored = rec.get("chain_hash", "")
        rest = {k: v for k, v in rec.items() if k != "chain_hash"}
        record_bytes = json.dumps(rest, sort_keys=True).encode("utf-8")
        h = hmac.new(key, prev + record_bytes, hashlib.sha256)
        if h.hexdigest() != stored:
            return False, i, "chain hash mismatch at record %d (run_id=%s)" % (
                i, rec.get("run_id", "?"))
        prev = h.digest()
    return True, len(records), "all %d records verified" % len(records)


def main():
    ap = argparse.ArgumentParser(description="AIR Blackbox Evidence Verifier")
    ap.add_argument("--key", default="air-blackbox-default",
                    help="signing key the chain was created with")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    all_pass = True

    print("=" * 60)
    print("AIR Blackbox Evidence Bundle Verification")
    print("=" * 60)

    meta_path = os.path.join(here, "bundle_meta.json")
    if not os.path.exists(meta_path):
        print("FAIL: bundle_meta.json not found")
        sys.exit(1)
    with open(meta_path) as f:
        meta = json.load(f)

    print("Generated: %s" % meta["air_evidence_bundle"]["generated_at"])
    print()

    for name, info in meta.get("contents", {}).items():
        fp = os.path.join(here, info["file"])
        if not os.path.exists(fp):
            print("[FAIL] %s - missing" % info["file"]); all_pass = False; continue
        actual = sha256_file(fp)
        ok = (actual == info["sha256"])
        if not ok: all_pass = False
        print("[%s] %s (SHA-256)" % ("PASS" if ok else "FAIL", info["file"]))

    chain_path = os.path.join(here, "audit_chain.json")
    if os.path.exists(chain_path):
        with open(chain_path) as f:
            chain = json.load(f)
        ok, count, msg = verify_chain(chain, args.key)
        if not ok: all_pass = False
        print("[%s] Audit chain - %s" % ("PASS" if ok else "FAIL", msg))
    else:
        print("[SKIP] no audit_chain.json")

    print("=" * 60)
    if all_pass:
        print("RESULT: PASS - evidence has not been tampered with.")
        sys.exit(0)
    else:
        print("RESULT: FAIL - evidence integrity could not be verified.")
        print("(If the chain fails, confirm you passed the correct --key.)")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
