"""One path from a runs directory to a signed, anchored .air-evidence bundle.

Before this module, `generate_evidence_bundle_v1` had exactly one caller: the
MCP server. Everything else - the CLI, the sandbox, the passport - produced
the legacy self-verifying ZIP, whose bundled `verify.py` needs the operator's
signing key. So the only format a third party can check without being handed a
secret was reachable only by running a chat connector, and `air-blackbox
export` could not produce it at all.

That is backwards for a product whose claim is "hand this to your auditor".
Key persistence, anchoring, and bundle assembly live here so the CLI and the
MCP server take the same path and cannot drift apart. The MCP server's
existing helpers delegate to these.

Anchoring defaults ON. The external timestamp is the only thing in the format
that an operator cannot forge for themselves, so making it opt-in made the
one load-bearing property optional. An unreachable TSA is recorded as a gap in
the signed manifest and the export still succeeds - a gap is evidence too, and
refusing to export offline would just teach people to pass --no-anchor.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("air_blackbox.export.air_evidence")

#: The tenant name a single-machine install writes under. The MCP server uses
#: the same value so a CLI export and a connector export of the same runs
#: directory produce bundles for the same tenant.
DEFAULT_TENANT = "_local"

RECEIPT_KEY_FILE = ".air-receipt-key"
ANCHOR_KEY_FILE = ".air-anchor-key"


# ---------------------------------------------------------------------------
# Signing key persistence
# ---------------------------------------------------------------------------

def load_signing_key(key_path: str):
    """Parse a persisted signing key file.

    Returns ("ed25519", seed_bytes), ("ML-DSA-65", (pub, secret)), or None if
    absent or unreadable.

    Two formats, and the legacy one is honoured forever: a bare hex 32-byte
    Ed25519 seed. Rewriting those installs to a new format would rotate their
    public key, which is the identity an auditor pins with --expect-key.
    """
    try:
        with open(key_path) as f:
            raw = f.read().strip()
    except OSError:
        return None
    if not raw:
        return None
    if not raw.startswith("{"):
        try:
            seed = bytes.fromhex(raw)
        except ValueError:
            return None
        return ("ed25519", seed) if len(seed) == 32 else None
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        return None
    alg = doc.get("algorithm")
    try:
        if alg == "ML-DSA-65":
            return alg, (bytes.fromhex(doc["public_key"]),
                         bytes.fromhex(doc["secret_key"]))
        if alg == "ed25519":
            seed = bytes.fromhex(doc["seed"])
            return (alg, seed) if len(seed) == 32 else None
    except (KeyError, ValueError):
        return None
    return None


def persist_signing_key(key_path: str, doc: dict) -> None:
    """Write a key file 0600. Failure is non-fatal but the public key will
    then change on the next run - warn, do not refuse to sign."""
    try:
        with open(key_path, "w") as f:
            json.dump(doc, f)
        os.chmod(key_path, 0o600)
    except OSError:
        logger.warning(
            "could not persist signing key at %s; the public key auditors "
            "pin will not be stable across runs", key_path)


def signer_for(runs_dir: str, hmac_key: Optional[str] = None):
    """Return the persistent ReceiptSigner for a runs directory.

    The key is owned by the directory, not by the process, so the fingerprint
    an auditor pins survives restarts and is the same whether the bundle came
    from the CLI or the connector.
    """
    from air_blackbox.gate.receipt import HAS_MLDSA65, ReceiptSigner

    os.makedirs(runs_dir, exist_ok=True)
    key_path = os.path.join(runs_dir, RECEIPT_KEY_FILE)
    if hmac_key is None:
        hmac_key = os.environ.get("TRUST_SIGNING_KEY")
    loaded = load_signing_key(key_path)

    if loaded is not None and loaded[0] == "ML-DSA-65" and HAS_MLDSA65:
        return ReceiptSigner(mldsa_keypair=loaded[1], hmac_key=hmac_key)
    if loaded is not None and loaded[0] == "ed25519":
        # An existing install's identity is Ed25519 and stays Ed25519.
        # Migrating would rotate the public key out from under its auditors.
        return ReceiptSigner(private_key=loaded[1], hmac_key=hmac_key)
    if HAS_MLDSA65:
        signer = ReceiptSigner(hmac_key=hmac_key)
        pub, secret = signer.mldsa_keypair
        persist_signing_key(key_path, {"algorithm": "ML-DSA-65",
                                       "public_key": pub.hex(),
                                       "secret_key": secret.hex()})
        return signer
    priv = os.urandom(32)
    persist_signing_key(key_path, {"algorithm": "ed25519", "seed": priv.hex()})
    return ReceiptSigner(private_key=priv, hmac_key=hmac_key)


def anchor_key_for(runs_dir: str) -> bytes:
    """Per-directory Ed25519 anchoring seed, separate from the receipt key.

    Receipts may be ML-DSA-65, which public logs cannot verify yet, and this
    key is an index handle: the security property comes from the log being
    append-only, not from who holds the key.
    """
    path = os.path.join(runs_dir, ANCHOR_KEY_FILE)
    try:
        with open(path) as f:
            seed = bytes.fromhex(f.read().strip())
            if len(seed) == 32:
                return seed
    except (OSError, ValueError):
        pass
    seed = os.urandom(32)
    try:
        with open(path, "w") as f:
            f.write(seed.hex())
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("could not persist anchor key at %s", path)
    return seed


def signer_fingerprint(signer) -> str:
    """The identity an auditor pins with --expect-key.

    Matches evidence_verify._fingerprint so the value printed at export is
    exactly the value the verifier prints and compares.
    """
    import hashlib
    pub = signer.public_key_hex or ""
    if not pub:
        return signer.method
    return f"{signer.method}:{hashlib.sha256(bytes.fromhex(pub)).hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# Anchoring
# ---------------------------------------------------------------------------

def anchor_dir_for(runs_dir: str) -> str:
    d = os.path.join(runs_dir, "anchors")
    os.makedirs(d, exist_ok=True)
    return d


def anchor_head(runs_dir: str, *, tsa_urls=None, timeout: float = 20.0,
                rekor_server: Optional[str] = None,
                persist: bool = True) -> Tuple[str, Dict[str, Any]]:
    """Timestamp the current chain head at an external TSA.

    Returns (note, manifest). An unreachable authority is recorded as a gap in
    the returned manifest and appended to anchors/gaps.log - never silently
    dropped, because "we could not get a witness that day" is itself something
    an auditor is entitled to see.
    """
    import base64

    from air_blackbox.anchor import compute_head, timestamp_head
    from air_blackbox.replay.engine import ReplayEngine

    engine = ReplayEngine(runs_dir=runs_dir)
    engine.load()
    seq_max = max((r.get("chain_seq") or 0
                   for r in engine._raw_records), default=0)
    head = compute_head(runs_dir)
    if not head:
        return "Anchor: no chained records to anchor.", {
            "anchored": False, "reason": "no records"}

    adir = anchor_dir_for(runs_dir)
    result = timestamp_head(head, tsa_urls, timeout=timeout)
    if not result.ok:
        try:
            with open(os.path.join(adir, "gaps.log"), "a") as f:
                f.write(json.dumps({"seq_max": seq_max, "head": head,
                                    "error": result.error}) + "\n")
        except OSError:
            pass
        manifest = {"anchored": False, "head": head, "seq_max": seq_max,
                    "error": result.error}
        note = (f"Anchor: GAP - no external timestamp obtained "
                f"({result.error}). Recorded as a gap; this bundle carries no "
                f"external witness and an operator rewrite would not be "
                f"detectable.")
    else:
        manifest = {"anchored": True, "head": head, "seq_max": seq_max,
                    "tsa_url": result.tsa_url, "timestamp": result.timestamp,
                    "tsr_b64": base64.b64encode(result.tsr).decode()}
        note = (f"Anchor: head bound to {result.tsa_url} at "
                f"{result.timestamp}. A rewritten history cannot inherit "
                f"this timestamp.")

    if rekor_server:
        from air_blackbox.anchor.rekor import anchor_head_to_rekor
        try:
            rk = anchor_head_to_rekor(head, seq_max, anchor_key_for(runs_dir),
                                      server=rekor_server)
            manifest["rekor"] = rk.to_dict()
            note += (f" Public log: entry {rk.uuid[:16]}... at index "
                     f"{rk.log_index}.")
        except Exception as exc:              # an unreachable log is a gap
            try:
                with open(os.path.join(adir, "gaps.log"), "a") as f:
                    f.write(json.dumps({"seq_max": seq_max, "head": head,
                                        "rekor_error": str(exc)}) + "\n")
            except OSError:
                pass
            manifest["rekor"] = {"anchored": False, "error": str(exc)}
            note += f" Public log: GAP ({exc}); recorded, not hidden."

    if persist and manifest.get("anchored"):
        try:
            with open(os.path.join(adir, f"anchor-{seq_max}.json"), "w") as f:
                json.dump(manifest, f)
        except OSError:
            pass
    return note, manifest


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@dataclass
class ExportResult:
    path: str
    manifest: Dict[str, Any]
    fingerprint: str
    anchor_note: str = ""
    records: int = 0
    notes: list = field(default_factory=list)

    @property
    def anchored(self) -> bool:
        return bool((self.manifest.get("anchor") or {}).get("anchored"))


def export_air_evidence(runs_dir: str, *, tenant: str = DEFAULT_TENANT,
                        output_dir: str = ".", anchor: bool = True,
                        tsa_urls=None, anchor_timeout: float = 20.0,
                        rekor_server: Optional[str] = None,
                        system: Optional[Dict[str, Any]] = None,
                        attachments_dir: Optional[str] = None,
                        signing_key: Optional[str] = None,
                        signer=None) -> ExportResult:
    """Package a runs directory as a signed .air-evidence v1 bundle.

    This is the format `air-evidence verify` reads and the only one a third
    party can check without being handed the operator's key.
    """
    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    from air_blackbox.replay.engine import ReplayEngine

    engine = ReplayEngine(runs_dir=runs_dir)
    total = engine.load()
    records = list(getattr(engine, "_raw_records", []))
    if not records:
        raise ValueError(
            f"no records found in {runs_dir} - nothing to evidence. Route "
            "traffic through the AIR gateway or a trust layer first.")

    # Verify before packaging and stamp the verdict INTO the signed payload,
    # so a bundle never quietly attests a broken chain. The chain must be
    # checked with the key it was WRITTEN with - explicit, then
    # TRUST_SIGNING_KEY, then the gateway's generated keyfile - or every
    # export would report a perfectly good chain as broken.
    hmac_key = signing_key or os.environ.get("TRUST_SIGNING_KEY")
    if not hmac_key:
        try:
            with open(os.path.join(runs_dir, ".air-signing-key")) as f:
                hmac_key = f.read().strip() or None
        except OSError:
            hmac_key = None
    verification = (engine.verify_chain(signing_key=hmac_key) if hmac_key
                    else engine.verify_chain())
    chain_verification = {
        "intact": verification.intact,
        "verified_records": verification.verified_records,
        "fully_intact": (verification.intact
                         and verification.verified_records == total),
    }

    if signer is None:
        signer = signer_for(runs_dir, hmac_key=hmac_key)

    anchor_note, anchor_manifest = "", None
    if anchor:
        anchor_note, anchor_manifest = anchor_head(
            runs_dir, tsa_urls=tsa_urls, timeout=anchor_timeout,
            rekor_server=rekor_server)
    else:
        anchor_note = ("Anchor: SKIPPED by request. This bundle has no "
                       "external witness, so an operator rewrite would not be "
                       "detectable and the verifier will report it as "
                       "UNWITNESSED.")

    if attachments_dir is None:
        attachments_dir = os.path.join(runs_dir, "attachments")

    path, manifest = generate_evidence_bundle_v1(
        chain_entries=records,
        tenant=tenant,
        signer=signer,
        chain_verification=chain_verification,
        system=system,
        attachments_dir=(attachments_dir
                         if os.path.isdir(attachments_dir) else None),
        anchor_manifest=anchor_manifest,
        output_dir=output_dir,
    )

    notes = []
    if not chain_verification["fully_intact"]:
        notes.append(
            f"Chain NOT fully intact: {verification.verified_records}/{total} "
            "records verified. The bundle records this honestly rather than "
            "refusing to export.")
    return ExportResult(path=path, manifest=manifest,
                        fingerprint=signer_fingerprint(signer),
                        anchor_note=anchor_note, records=len(records),
                        notes=notes)
