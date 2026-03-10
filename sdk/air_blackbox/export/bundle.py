"""
Export engine — generates signed evidence bundles.

Packages compliance scan + AI-BOM + audit chain + stats into
one signed, verifiable JSON document for auditors and insurers.
"""

import json
import hashlib
import hmac
import os
from datetime import datetime
from typing import Optional

from air_blackbox.gateway_client import GatewayClient
from air_blackbox.compliance.engine import run_all_checks
from air_blackbox.aibom.generator import generate_aibom
from air_blackbox.replay.engine import ReplayEngine


def generate_evidence_bundle(gateway_url="http://localhost:8080",
                             runs_dir=None, scan_path=".",
                             signing_key=None) -> dict:
    """Generate a signed evidence bundle.

    Combines all AIR Blackbox data into one auditor-ready document.
    """
    key = (signing_key or os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default"))
    now = datetime.utcnow().isoformat() + "Z"

    # 1. Gateway status
    client = GatewayClient(gateway_url=gateway_url, runs_dir=runs_dir or "./runs")
    status = client.get_status()

    # 2. Compliance scan
    compliance = run_all_checks(status, scan_path)

    # 3. AI-BOM
    aibom = generate_aibom(status)

    # 4. Replay stats + chain verification
    engine = ReplayEngine(runs_dir=client.runs_dir)
    engine.load()
    stats = engine.get_stats()
    chain = engine.verify_chain(signing_key=key)

    # 5. Build the bundle
    bundle = {
        "air_blackbox_evidence_bundle": {
            "version": "1.0.0",
            "generated_at": now,
            "generator": "air-blackbox v1.0.0",
        },
        "gateway": {
            "url": gateway_url,
            "reachable": status.reachable,
            "vault_enabled": status.vault_enabled,
            "guardrails_enabled": status.guardrails_enabled,
            "signing_key_configured": status.trust_signing_key_set,
        },
        "compliance": {
            "framework": "EU AI Act",
            "articles_checked": [9, 10, 11, 12, 14, 15],
            "results": compliance,
            "summary": {
                "total_checks": sum(len(a["checks"]) for a in compliance),
                "passing": sum(1 for a in compliance for c in a["checks"] if c["status"] == "pass"),
                "warnings": sum(1 for a in compliance for c in a["checks"] if c["status"] == "warn"),
                "failing": sum(1 for a in compliance for c in a["checks"] if c["status"] == "fail"),
            }
        },
        "aibom": aibom,
        "audit_trail": {
            "total_records": stats.get("total_records", 0),
            "models": stats.get("models", {}),
            "providers": stats.get("providers", {}),
            "statuses": stats.get("statuses", {}),
            "total_tokens": stats.get("total_tokens", 0),
            "avg_duration_ms": stats.get("avg_duration_ms", 0),
            "pii_alerts": stats.get("pii_alerts", 0),
            "injection_alerts": stats.get("injection_alerts", 0),
            "date_range": stats.get("date_range"),
            "chain_verification": {
                "intact": chain.intact,
                "records_verified": chain.verified_records,
                "total_records": chain.total_records,
            }
        },
    }

    # 6. Sign the bundle
    bundle_bytes = json.dumps(bundle, sort_keys=True).encode()
    signature = hmac.new(key.encode(), bundle_bytes, hashlib.sha256).hexdigest()
    bundle["attestation"] = {
        "algorithm": "HMAC-SHA256",
        "signature": signature,
        "signed_at": now,
        "verification": "To verify: compute HMAC-SHA256 of the bundle (excluding this attestation field) with the signing key.",
    }

    return bundle
