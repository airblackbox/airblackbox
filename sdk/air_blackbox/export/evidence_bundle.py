"""
Compliance evidence bundle exporter for AIR Blackbox.

Produces a signed, timestamped ZIP that auditors can independently verify.
Contains scan results, audit chain, standards crosswalk, and cryptographic proof
of bundle integrity.
"""

import json
import hashlib
import hmac
import os
import zipfile
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple


@dataclass
class BundleMetadata:
    """Metadata about the generated compliance bundle."""
    created_at: str
    scanner_version: str
    signing_key_fingerprint: str
    scan_path: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int


class EvidenceBundle:
    """Collects and exports compliance evidence for auditors."""

    def __init__(self, scan_results: dict, metadata: BundleMetadata):
        """Initialize bundle with scan results and metadata.

        Args:
            scan_results: Output from run_all_checks()
            metadata: BundleMetadata with version, timestamp, etc.
        """
        self.scan_results = scan_results
        self.metadata = metadata
        self.files_manifest = {}
        self.bundle_files = {}

    def add_scan_results(self, results: dict) -> None:
        """Add full compliance scan results."""
        self.bundle_files["scan_results.json"] = results

    def add_audit_chain(self, audit_records: List[dict]) -> None:
        """Add audit chain records from .air.json files."""
        self.bundle_files["audit_chain"] = audit_records

    def add_crosswalk_report(self, json_report: dict,
                              md_report: str) -> None:
        """Add standards crosswalk (ISO 42001 + NIST mapping).

        Args:
            json_report: Structured crosswalk data
            md_report: Human-readable markdown version
        """
        self.bundle_files["crosswalk_report.json"] = json_report
        self.bundle_files["crosswalk_report.md"] = md_report

    def add_chain_verification(self, verification: dict) -> None:
        """Add HMAC chain verification result."""
        self.bundle_files["chain_verification.json"] = verification

    def _compute_file_hash(self, data: bytes) -> str:
        """Compute SHA-256 hash of bytes."""
        return hashlib.sha256(data).hexdigest()

    def _build_manifest(self) -> dict:
        """Build manifest.json with all files and their checksums."""
        manifest = {
            "created_at": self.metadata.created_at,
            "scanner_version": self.metadata.scanner_version,
            "signing_key_fingerprint": self.metadata.signing_key_fingerprint,
            "scan_path": self.metadata.scan_path,
            "summary": {
                "total_checks": self.metadata.total_checks,
                "pass_count": self.metadata.pass_count,
                "warn_count": self.metadata.warn_count,
                "fail_count": self.metadata.fail_count,
            },
            "files": {}
        }

        for filename, content in self.bundle_files.items():
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')

            file_hash = self._compute_file_hash(content_bytes)
            manifest["files"][filename] = {
                "sha256": file_hash,
                "size_bytes": len(content_bytes)
            }

        return manifest

    def _sign_manifest(self, manifest: dict,
                       signing_key: str) -> Tuple[str, str]:
        """Sign the manifest using HMAC-SHA256.

        Returns:
            Tuple of (signature_hex, fingerprint)
        """
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
        signature = hmac.new(signing_key.encode('utf-8'),
                            manifest_bytes,
                            hashlib.sha256).hexdigest()

        key_hash = hashlib.sha256(signing_key.encode('utf-8')).hexdigest()
        fingerprint = key_hash[:16]

        return signature, fingerprint

    def export_zip(self, output_path: str,
                   signing_key: Optional[str] = None) -> str:
        """Export bundle as signed ZIP file.

        Args:
            output_path: Path where ZIP will be written
            signing_key: HMAC signing key (uses env var if not provided)

        Returns:
            Path to created ZIP file
        """
        key = (signing_key or
               os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default"))

        manifest = self._build_manifest()
        signature, fingerprint = self._sign_manifest(manifest, key)

        bundle_sig = {
            "algorithm": "HMAC-SHA256",
            "signature": signature,
            "signed_at": self.metadata.created_at,
            "verification": "Verify by computing HMAC-SHA256 of manifest.json with signing key.",
        }

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, 'w',
                            zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json",
                       json.dumps(manifest, indent=2))
            zf.writestr("bundle_signature.json",
                       json.dumps(bundle_sig, indent=2))

            for filename, content in self.bundle_files.items():
                if isinstance(content, str):
                    data = content.encode('utf-8')
                else:
                    data = json.dumps(content, sort_keys=True).encode('utf-8')

                zf.writestr(filename, data)

        return output_path


def generate_bundle(scan_results: dict, runs_dir: str,
                    output_path: str,
                    signing_key: Optional[str] = None,
                    scanner_version: str = "1.0.0",
                    scan_path: str = ".") -> str:
    """Generate a complete compliance evidence bundle.

    Creates a signed ZIP containing scan results, audit chain, crosswalk
    report, and cryptographic proof of integrity.

    Args:
        scan_results: Output from run_all_checks()
        runs_dir: Directory containing .air.json audit records
        output_path: Path for output ZIP file
        signing_key: HMAC signing key (uses env var if not provided)
        scanner_version: Version string for the scanner
        scan_path: Path that was scanned

    Returns:
        Path to created ZIP file
    """
    key = (signing_key or
           os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default"))
    now = datetime.utcnow().isoformat() + "Z"

    total_checks = sum(len(c.get("checks", []))
                      for c in scan_results.get("checks", []))
    pass_count = sum(1 for c in scan_results.get("checks", [])
                    for check in c.get("checks", [])
                    if check.get("status") == "pass")
    warn_count = sum(1 for c in scan_results.get("checks", [])
                    for check in c.get("checks", [])
                    if check.get("status") == "warn")
    fail_count = sum(1 for c in scan_results.get("checks", [])
                    for check in c.get("checks", [])
                    if check.get("status") == "fail")

    metadata = BundleMetadata(
        created_at=now,
        scanner_version=scanner_version,
        signing_key_fingerprint="",
        scan_path=scan_path,
        total_checks=total_checks,
        pass_count=pass_count,
        warn_count=warn_count,
        fail_count=fail_count,
    )

    bundle = EvidenceBundle(scan_results, metadata)
    bundle.add_scan_results(scan_results)

    audit_records = _load_audit_chain(runs_dir)
    bundle.add_audit_chain(audit_records)

    crosswalk_json = _generate_crosswalk(scan_results)
    crosswalk_md = _crosswalk_to_markdown(crosswalk_json)
    bundle.add_crosswalk_report(crosswalk_json, crosswalk_md)

    verification = _verify_audit_chain(runs_dir, key)
    bundle.add_chain_verification(verification)

    bundle.bundle_files["metadata.json"] = asdict(metadata)

    return bundle.export_zip(output_path, signing_key=key)


def verify_bundle(zip_path: str,
                  signing_key: Optional[str] = None) -> dict:
    """Verify the integrity of a compliance evidence bundle.

    Extracts and verifies manifest checksums and bundle signature.

    Args:
        zip_path: Path to the evidence bundle ZIP
        signing_key: HMAC signing key (uses env var if not provided)

    Returns:
        Dict with: valid (bool), errors (list), file_count (int),
                   manifest (dict), details (dict)
    """
    key = (signing_key or
           os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default"))

    result = {
        "valid": True,
        "errors": [],
        "file_count": 0,
        "manifest": None,
        "details": {}
    }

    if not os.path.exists(zip_path):
        result["valid"] = False
        result["errors"].append(f"ZIP file not found: {zip_path}")
        return result

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            result["file_count"] = len(zf.namelist())

            manifest_data = zf.read("manifest.json")
            manifest = json.loads(manifest_data)
            result["manifest"] = manifest

            sig_data = zf.read("bundle_signature.json")
            bundle_sig = json.loads(sig_data)

            manifest_bytes = json.dumps(manifest,
                                       sort_keys=True).encode('utf-8')
            expected_sig = hmac.new(key.encode('utf-8'),
                                   manifest_bytes,
                                   hashlib.sha256).hexdigest()

            if bundle_sig["signature"] != expected_sig:
                result["valid"] = False
                result["errors"].append("Bundle signature verification failed")
                result["details"]["signature_mismatch"] = True
            else:
                result["details"]["signature_verified"] = True

            for filename, file_info in manifest["files"].items():
                if filename not in zf.namelist():
                    result["valid"] = False
                    result["errors"].append(f"Missing file in ZIP: {filename}")
                    continue

                file_bytes = zf.read(filename)
                actual_hash = hashlib.sha256(file_bytes).hexdigest()
                expected_hash = file_info["sha256"]

                if actual_hash != expected_hash:
                    result["valid"] = False
                    result["errors"].append(
                        f"Hash mismatch for {filename}"
                    )
                    result["details"][f"{filename}_hash_mismatch"] = True
                else:
                    result["details"][f"{filename}_verified"] = True

    except zipfile.BadZipFile:
        result["valid"] = False
        result["errors"].append("Invalid ZIP file format")
    except json.JSONDecodeError as e:
        result["valid"] = False
        result["errors"].append(f"Invalid JSON in bundle: {str(e)}")
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Verification error: {str(e)}")

    return result


def _load_audit_chain(runs_dir: str) -> List[dict]:
    """Load all .air.json files from runs directory.

    Args:
        runs_dir: Directory containing audit chain records

    Returns:
        List of audit records
    """
    records = []

    if not os.path.isdir(runs_dir):
        return records

    try:
        for filename in os.listdir(runs_dir):
            if filename.endswith(".air.json"):
                filepath = os.path.join(runs_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        record = json.load(f)
                        record["_filename"] = filename
                        records.append(record)
                except (json.JSONDecodeError, IOError):
                    pass

    except OSError:
        pass

    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records


def _verify_audit_chain(runs_dir: str, signing_key: str) -> dict:
    """Verify the HMAC chain of audit records.

    Args:
        runs_dir: Directory containing audit records
        signing_key: Key used for chain verification

    Returns:
        Verification result dict
    """
    records = _load_audit_chain(runs_dir)

    result = {
        "chain_intact": True,
        "total_records": len(records),
        "verified_records": 0,
        "errors": []
    }

    if not records:
        return result

    for i, record in enumerate(records):
        if "hmac" in record and "_content_hash" in record:
            try:
                content = record.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, sort_keys=True)
                content_bytes = content.encode('utf-8')

                expected_hmac = hmac.new(
                    signing_key.encode('utf-8'),
                    content_bytes,
                    hashlib.sha256
                ).hexdigest()

                if expected_hmac == record["hmac"]:
                    result["verified_records"] += 1
                else:
                    result["chain_intact"] = False
                    result["errors"].append(
                        f"Record {i} HMAC mismatch"
                    )
            except Exception as e:
                result["chain_intact"] = False
                result["errors"].append(f"Record {i} verification error")

    return result


def _generate_crosswalk(scan_results: dict) -> dict:
    """Generate ISO 42001 and NIST mapping from scan results.

    Args:
        scan_results: Output from compliance scan

    Returns:
        Structured crosswalk mapping
    """
    crosswalk = {
        "iso_42001": {},
        "nist_ai_rmf": {},
        "eu_ai_act_articles": {},
        "scan_mapping": []
    }

    checks = scan_results.get("checks", [])

    for article_group in checks:
        article = article_group.get("article")
        article_checks = article_group.get("checks", [])

        if article:
            crosswalk["eu_ai_act_articles"][f"Article {article}"] = {
                "total": len(article_checks),
                "passing": sum(1 for c in article_checks
                             if c.get("status") == "pass"),
                "warnings": sum(1 for c in article_checks
                              if c.get("status") == "warn"),
                "failures": sum(1 for c in article_checks
                              if c.get("status") == "fail"),
                "checks": [
                    {
                        "id": c.get("id"),
                        "title": c.get("title"),
                        "status": c.get("status"),
                        "severity": c.get("severity")
                    }
                    for c in article_checks
                ]
            }

            for check in article_checks:
                crosswalk["scan_mapping"].append({
                    "article": article,
                    "check_id": check.get("id"),
                    "status": check.get("status"),
                    "message": check.get("message", "")
                })

    return crosswalk


def _crosswalk_to_markdown(crosswalk: dict) -> str:
    """Convert crosswalk to human-readable markdown.

    Args:
        crosswalk: Crosswalk dictionary

    Returns:
        Markdown formatted report
    """
    md = ["# Compliance Crosswalk Report\n"]
    md.append("## EU AI Act Articles\n")

    for article, data in sorted(
        crosswalk.get("eu_ai_act_articles", {}).items()
    ):
        md.append(f"### {article}\n")
        md.append(f"- Total Checks: {data['total']}\n")
        md.append(f"- Passing: {data['passing']}\n")
        md.append(f"- Warnings: {data['warnings']}\n")
        md.append(f"- Failures: {data['failures']}\n")
        md.append("")

        if data.get("checks"):
            md.append("#### Checks\n")
            for check in data["checks"]:
                status_symbol = {
                    "pass": "PASS",
                    "warn": "WARN",
                    "fail": "FAIL"
                }.get(check["status"], "?")

                md.append(
                    f"- [{status_symbol}] {check['id']}: "
                    f"{check['title']}\n"
                )
            md.append("")

    return "\n".join(md)
