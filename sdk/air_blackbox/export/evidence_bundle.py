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
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Required members of a v1 .air-evidence bundle (attachments are optional).
V1_REQUIRED_FILES = (
    "manifest.json",
    "records/actions.jsonl",
    "verification/chain.json",
    "verification/receipts.json",
    "verification/public_key.pem",
    "mapping/sb24-205.json",
)


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
# Evidence Bundle v1 (.air-evidence) - structured, signed, regulator-mappable.
# Layout per the AIR Evidence Bundle v1 spec:
#   manifest.json  records/actions.jsonl  verification/{chain,receipts}.json
#   verification/public_key.pem  mapping/sb24-205.json  attachments/*
# ---------------------------------------------------------------------------

#: Screening actions: records with these action names (or an explicit
#: "screening" object) evidence consequential decisions under SB 24-205.
_SCREENING_ACTIONS = frozenset(
    {"advance_candidate", "reject_candidate", "score_candidate",
     "rank_candidates", "schedule_interview"})


def categorize_record(record: Dict[str, Any]) -> str:
    """Map a chained record to its evidence category (see mapping/*.json)."""
    if record.get("status") == "blocked":
        return "blocked_action"
    action = record.get("action", "")
    if action == "human_approval":
        return "human_approval"
    if "screening" in record or action in _SCREENING_ACTIONS:
        return "screening_decision"
    return "agent_action"


def canonical_manifest_bytes(manifest: Dict[str, Any]) -> bytes:
    """Canonical byte form of the manifest for signing: signature field
    removed, keys sorted, no whitespace. Sign the sha256 of THIS, never the
    pretty-printed JSON."""
    stripped = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(stripped, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _pem_public_key(public_key_hex: str) -> str:
    """Render a raw Ed25519 public key as SubjectPublicKeyInfo PEM so the
    verifier needs no secret and no custom parsing."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        return key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
    except Exception:
        # HMAC-fallback signers have no public key; ship the hex (possibly
        # empty) with an explanatory header so the bundle stays well-formed.
        return ("-----BEGIN AIR PUBLIC KEY HEX-----\n"
                f"{public_key_hex}\n"
                "-----END AIR PUBLIC KEY HEX-----\n")


def _retention_until(created: datetime, years: int = 3) -> str:
    """SB 24-205 retention floor: created + 3 years (Feb 29 clamps to 28)."""
    try:
        return created.replace(year=created.year + years).date().isoformat()
    except ValueError:
        return created.replace(year=created.year + years,
                               day=28).date().isoformat()


def _load_framework_mapping(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "mappings", f"{name}.json")
    with open(path, encoding="utf-8") as f:
        return f.read()


def generate_evidence_bundle_v1(
    chain_entries: List[Dict[str, Any]],
    tenant: str,
    signer,
    chain_verification: Dict[str, Any],
    system: Optional[Dict[str, Any]] = None,
    attachments_dir: Optional[str] = None,
    anchor_manifest: Optional[Dict[str, Any]] = None,
    output_dir: str = ".",
) -> Tuple[str, Dict[str, Any]]:
    """Generate a v1 .air-evidence bundle and return (path, manifest).

    Args:
        chain_entries: chained records in write order (each carries
                       chain_hash and, normally, a signed receipt).
        tenant: tenant id the records belong to.
        signer: ReceiptSigner for the tenant - signs the manifest with the
                same key that signed the per-record receipts.
        chain_verification: verify_chain result stamped into the bundle.
        system: deployer-supplied system register info (name,
                high_risk_rationale, deployer). Missing values are recorded
                as "deployer-supplied" so gaps are explicit, never hidden.
        attachments_dir: directory of deployer documents (impact assessment,
                         system register, monitoring plan) copied under
                         attachments/.
        anchor_manifest: external timestamp anchor manifest, if anchoring ran.
        output_dir: where to write the bundle.
    """
    now = datetime.now(timezone.utc)
    created_at = now.isoformat(timespec="seconds").replace("+00:00", "Z")

    # --- records/actions.jsonl: one canonical line per record, chain order.
    actions_jsonl = "\n".join(
        json.dumps(r, sort_keys=True, default=str) for r in chain_entries)
    if actions_jsonl:
        actions_jsonl += "\n"

    # --- counts (screening decisions missing a reviewer are themselves
    # assessment output: the gap is reported, not hidden).
    cats = [categorize_record(r) for r in chain_entries]
    screening_records = [r for r, c in zip(chain_entries, cats)
                         if c == "screening_decision"]
    missing_reviewer = sum(
        1 for r in screening_records
        if not r.get("screening", {}).get("human_reviewer"))
    counts = {
        "actions": len(chain_entries),
        "screening_decisions": len(screening_records),
        "blocked_actions": cats.count("blocked_action"),
        "human_approvals": cats.count("human_approval"),
        "screening_decisions_missing_reviewer": missing_reviewer,
    }

    # --- verification/chain.json
    timestamps = [r.get("timestamp", "") for r in chain_entries
                  if r.get("timestamp")]
    chain_doc = json.dumps({
        "algorithm": ("HMAC-SHA256(key, prev_hash || "
                      "json.dumps(record_without_chain_hash, sort_keys=True)); "
                      "prev_hash starts at b'genesis' and advances to the raw "
                      "digest each step"),
        "head_hash": (chain_entries[-1].get("chain_hash", "")
                      if chain_entries else ""),
        "records": [{"run_id": r.get("run_id", ""),
                     "chain_hash": r.get("chain_hash", "")}
                    for r in chain_entries],
        "verification_at_export": chain_verification,
    }, indent=2, default=str)

    # --- verification/receipts.json
    receipts_doc = json.dumps({
        "signing_method": signer.method,
        "public_key_hex": signer.public_key_hex or "",
        "note": ("Each receipt's authorization_sig covers the canonical "
                 "authorization payload (receipt_id, agent_id, action_name, "
                 "action_category, payload_hash, covenant_hash, decision, "
                 "authorized, parent_receipt_id, created_at) serialized with "
                 "sort_keys=True. Verifiable with the public key alone."),
        "receipts": [{"run_id": r.get("run_id", ""), **r["receipt"]}
                     for r in chain_entries if r.get("receipt")],
    }, indent=2, default=str)

    public_key_pem = _pem_public_key(signer.public_key_hex or "")
    mapping_doc = _load_framework_mapping("sb24-205")

    # --- attachments (deployer-supplied documents ride along, digested and
    # therefore covered by the manifest signature).
    attachments: Dict[str, bytes] = {}
    if attachments_dir and os.path.isdir(attachments_dir):
        for fname in sorted(os.listdir(attachments_dir)):
            fpath = os.path.join(attachments_dir, fname)
            if os.path.isfile(fpath) and not fname.startswith("."):
                with open(fpath, "rb") as f:
                    attachments[f"attachments/{fname}"] = f.read()

    # --- manifest: every bundle file is digested here, so the single
    # manifest signature transitively covers the entire bundle.
    files: Dict[str, str] = {
        "records/actions.jsonl": hashlib.sha256(
            actions_jsonl.encode()).hexdigest(),
        "verification/chain.json": hashlib.sha256(
            chain_doc.encode()).hexdigest(),
        "verification/receipts.json": hashlib.sha256(
            receipts_doc.encode()).hexdigest(),
        "verification/public_key.pem": hashlib.sha256(
            public_key_pem.encode()).hexdigest(),
        "mapping/sb24-205.json": hashlib.sha256(
            mapping_doc.encode()).hexdigest(),
    }
    for name, blob in attachments.items():
        files[name] = hashlib.sha256(blob).hexdigest()

    system = dict(system or {})
    manifest: Dict[str, Any] = {
        "bundle_version": "1.0",
        "bundle_id": str(uuid.uuid4()),
        "created_at": created_at,
        "tenant": tenant,
        "system": {
            "name": system.get("name") or "deployer-supplied",
            "high_risk_rationale": (system.get("high_risk_rationale")
                                    or "deployer-supplied"),
            "deployer": system.get("deployer") or "deployer-supplied",
            "period_covered": {
                "from": min(timestamps) if timestamps else "",
                "to": max(timestamps) if timestamps else "",
            },
        },
        "counts": counts,
        "retention_until": _retention_until(now),
        "retention_note": ("SB 24-205 requires retention for 3 years after "
                           "the system is discontinued; this date assumes "
                           "discontinuation no earlier than export."),
        "frameworks": ["CO-SB24-205"],
        "outcome_monitoring": "deployer-supplied",
        "anchor": anchor_manifest or {"status": "absent"},
        "files": files,
    }

    digest = hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest()
    manifest["signature"] = {
        "alg": signer.method,
        "upgrade_path": "ML-DSA-65",
        "signed_digest": digest,
        "encoding": "hex",
        "value": signer.sign(bytes.fromhex(digest)),
        "public_key_hex": signer.public_key_hex or "",
    }

    bundle_name = f"bundle-{now.strftime('%Y-%m-%d-%H%M%S')}-{tenant}.air-evidence"
    path = os.path.join(output_dir, bundle_name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("records/actions.jsonl", actions_jsonl)
        zf.writestr("verification/chain.json", chain_doc)
        zf.writestr("verification/receipts.json", receipts_doc)
        zf.writestr("verification/public_key.pem", public_key_pem)
        zf.writestr("mapping/sb24-205.json", mapping_doc)
        for name, blob in attachments.items():
            zf.writestr(name, blob)

    logger.info("evidence_bundle_v1_generated path=%s records=%d tenant=%s",
                path, len(chain_entries), tenant)
    return os.path.abspath(path), manifest


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
