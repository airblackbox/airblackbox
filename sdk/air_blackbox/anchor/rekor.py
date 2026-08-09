"""Public transparency-log anchoring (M2): publish the chain head to Rekor.

The RFC 3161 timestamp anchor (tsa.py) binds the chain head to an external
authority's clock - but its documented limit is the re-anchored rewrite: an
attacker who rewrites history AND obtains a fresh timestamp for the new head
produces a self-consistent bundle. This module closes that gap with Sigstore's
Rekor (https://docs.sigstore.dev/logging/overview/), a public APPEND-ONLY log:

  - At export, the chain head (with its sequence bound) is signed and
    published. Once integrated, the entry cannot be removed - not by us, not
    by the operator, not by Sigstore.
  - At audit, the verifier fetches EVERY anchor ever logged under the
    tenant's anchoring key and recomputes the bounded chain head
    (compute_head(runs, up_to_seq)) for each. A rewritten history - even one
    freshly re-anchored - still fails against the OLD entries, because those
    cannot be taken back.

The anchoring key is a per-tenant Ed25519 key (Rekor verifies Ed25519, not
yet ML-DSA - same reason the Go checkpoints are dual-signed, see
pkg/trust/anchor.go). The key is an index handle, not a root of trust: the
security property comes from the log's append-onlyness, not from who holds
this key. An attacker who anchors lies under it only publishes permanent,
timestamped evidence of the conflict.

Wire format mirrors the working Go client (pkg/trust/anchor.go): "rekord"
entries, because Ed25519 is not a pre-hash scheme so Rekor must see the full
payload to verify the signature.
"""

import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_REKOR_SERVER = "https://rekor.sigstore.dev"

PAYLOAD_FORMAT = "air-chain-anchor-v1"


def anchor_payload_bytes(head_hex: str, seq_max: int, anchored_at: str) -> bytes:
    """Canonical signed payload: commits to the head AND the sequence bound,
    so a verifier can recompute exactly the history this anchor covered."""
    return json.dumps({
        "format": PAYLOAD_FORMAT,
        "chain_head": head_hex,
        "chain_seq_max": seq_max,
        "anchored_at": anchored_at,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pem_ed25519(pub_raw: bytes) -> bytes:
    """Raw Ed25519 public key -> SubjectPublicKeyInfo PEM (what Rekor wants)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PublicKey,
    )
    return Ed25519PublicKey.from_public_bytes(pub_raw).public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)


@dataclass
class RekorAnchor:
    """Receipt for an entry accepted by (or already present in) the log."""
    server: str = ""
    uuid: str = ""
    log_index: int = -1
    integrated_time: int = 0
    already_existed: bool = False
    payload_b64: str = ""        # what was logged, for offline re-derivation
    signature_hex: str = ""
    public_key_hex: str = ""     # raw Ed25519 anchoring public key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server": self.server, "uuid": self.uuid,
            "log_index": self.log_index,
            "integrated_time": self.integrated_time,
            "already_existed": self.already_existed,
            "payload_b64": self.payload_b64,
            "signature_hex": self.signature_hex,
            "public_key_hex": self.public_key_hex,
        }


class RekorClient:
    """Minimal Rekor API client over urllib - no new dependencies."""

    def __init__(self, server: str = DEFAULT_REKOR_SERVER, timeout: int = 30):
        self.server = server.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str,
                 body: Optional[dict] = None) -> tuple[int, bytes, dict]:
        req = urllib.request.Request(
            self.server + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"} if body is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def publish(self, payload: bytes, signature: bytes,
                public_key_raw: bytes) -> RekorAnchor:
        """Publish a signed payload as a rekord entry. Raises RuntimeError on
        anything other than 201 (created) / 409 (identical entry exists)."""
        entry = {
            "apiVersion": "0.0.1",
            "kind": "rekord",
            "spec": {
                "data": {"content": base64.b64encode(payload).decode()},
                "signature": {
                    "format": "x509",
                    "content": base64.b64encode(signature).decode(),
                    "publicKey": {"content": base64.b64encode(
                        _pem_ed25519(public_key_raw)).decode()},
                },
            },
        }
        status, body, headers = self._request(
            "POST", "/api/v1/log/entries", entry)
        base = RekorAnchor(
            server=self.server,
            payload_b64=base64.b64encode(payload).decode(),
            signature_hex=signature.hex(),
            public_key_hex=public_key_raw.hex())
        if status == 201:
            uuid, fields = _first_entry(body)
            base.uuid = uuid
            base.log_index = int(fields.get("logIndex", -1))
            base.integrated_time = int(fields.get("integratedTime", 0))
            return base
        if status == 409:
            loc = headers.get("Location", "") or headers.get("location", "")
            base.uuid = loc.rsplit("/", 1)[-1] if loc else ""
            base.already_existed = True
            return base
        raise RuntimeError(
            f"rekor returned HTTP {status}: {body[:300].decode(errors='replace')}")

    def fetch_entry(self, uuid: str) -> Dict[str, Any]:
        """Fetch a logged entry by UUID. Raises RuntimeError if absent."""
        status, body, _ = self._request(
            "GET", f"/api/v1/log/entries/{uuid}")
        if status != 200:
            raise RuntimeError(f"rekor returned HTTP {status} for entry {uuid}")
        _, fields = _first_entry(body)
        return fields

    def search_by_public_key(self, public_key_raw: bytes) -> List[str]:
        """All entry UUIDs logged under this anchoring key. This is what makes
        the log a detection tool, not just a receipt: old anchors cannot be
        removed, so they are all discoverable."""
        status, body, _ = self._request("POST", "/api/v1/index/retrieve", {
            "publicKey": {
                "format": "x509",
                "content": base64.b64encode(_pem_ed25519(public_key_raw)).decode(),
            }})
        if status != 200:
            raise RuntimeError(f"rekor search returned HTTP {status}")
        return list(json.loads(body.decode()))


def _first_entry(body: bytes) -> tuple[str, Dict[str, Any]]:
    """Rekor responses are {uuid: {fields...}} maps with one entry."""
    doc = json.loads(body.decode())
    for uuid, fields in doc.items():
        return uuid, fields
    raise RuntimeError("rekor returned an empty entry map")


def decode_logged_payload(entry_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse the air-chain-anchor payload from a fetched rekord
    entry. Raises ValueError if the entry is not one of ours."""
    body = json.loads(base64.b64decode(entry_fields["body"]).decode())
    if body.get("kind") != "rekord":
        raise ValueError(f"not a rekord entry: {body.get('kind')}")
    content = base64.b64decode(body["spec"]["data"]["content"])
    payload = json.loads(content.decode())
    if payload.get("format") != PAYLOAD_FORMAT:
        raise ValueError(f"not an AIR chain anchor: {payload.get('format')}")
    return payload


def anchor_head_to_rekor(head_hex: str, seq_max: int,
                         signing_seed: bytes,
                         server: str = DEFAULT_REKOR_SERVER,
                         client: Optional[RekorClient] = None) -> RekorAnchor:
    """Sign the (head, seq_max) payload with the tenant's Ed25519 anchoring
    key and publish it. Returns the anchor receipt for the bundle manifest."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    key = Ed25519PrivateKey.from_private_bytes(signing_seed)
    pub_raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    anchored_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = anchor_payload_bytes(head_hex, seq_max, anchored_at)
    signature = key.sign(payload)
    return (client or RekorClient(server)).publish(payload, signature, pub_raw)


# ---------------------------------------------------------------------------
# Verification: the check that actually closes the re-anchored-rewrite gap.
# ---------------------------------------------------------------------------

@dataclass
class LogAuditResult:
    """Outcome of auditing a runs directory against every logged anchor."""
    anchors_checked: int = 0
    consistent: int = 0
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    unparseable: int = 0

    @property
    def rewrite_detected(self) -> bool:
        return bool(self.mismatches)


def _ed25519_payload_ok(payload_b64: str, sig_hex: str, pub_hex: str) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            bytes.fromhex(sig_hex), base64.b64decode(payload_b64))
        return True
    except Exception:
        return False


def verify_bundle_anchor(runs_head_at: Dict[int, str],
                         anchor: Dict[str, Any]) -> tuple[bool, str]:
    """Offline check of one embedded Rekor anchor receipt against recomputed
    heads. runs_head_at maps a seq bound -> recomputed head at that bound.

    Offline it proves consistency (the embedded, signed payload matches the
    records); pass the receipt to a RekorClient.fetch_entry to also prove the
    entry is really in the public log.
    """
    try:
        payload = json.loads(base64.b64decode(anchor["payload_b64"]).decode())
    except Exception as e:
        return False, f"embedded anchor payload unparseable: {e}"
    if payload.get("format") != PAYLOAD_FORMAT:
        return False, f"embedded payload is not an AIR chain anchor"
    if not _ed25519_payload_ok(anchor.get("payload_b64", ""),
                               anchor.get("signature_hex", ""),
                               anchor.get("public_key_hex", "")):
        return False, "embedded anchor signature INVALID for its public key"
    seq = int(payload.get("chain_seq_max", -1))
    want = payload.get("chain_head", "")
    got = runs_head_at.get(seq)
    if got is None:
        return False, f"cannot recompute head at logged seq bound {seq}"
    if got != want:
        return False, (f"REWRITE DETECTED: recomputed head at seq {seq} is "
                       f"{got[:16]}..., but the logged anchor committed to "
                       f"{str(want)[:16]}...")
    return True, f"anchor consistent: head at seq {seq} matches the logged payload"


def verify_anchor_in_log(anchor: Dict[str, Any],
                         client: Optional[RekorClient] = None,
                         server: str = DEFAULT_REKOR_SERVER
                         ) -> tuple[bool, str]:
    """Confirm the claimed entry is really in the public log and says the
    same thing the bundle says it says.

    verify_bundle_anchor() checks the embedded receipt's signature against a
    public key the receipt itself carries, so offline it establishes
    self-consistency and nothing more: anyone can mint a key, sign a payload
    over any head they like, and attach a plausible-looking uuid and log
    index. This is the check that the entry exists.

    Even this does not establish authority. A public log accepts writes from
    anyone, so membership proves the commitment was published at that index
    and can never be retracted - not who published it. Pin the anchoring key
    and sweep every entry under it (audit_runs_against_log) for that.
    """
    uuid = anchor.get("uuid")
    if not uuid:
        return False, "anchor carries no rekor uuid"
    try:
        embedded = json.loads(base64.b64decode(anchor["payload_b64"]).decode())
    except Exception as e:
        return False, f"embedded anchor payload unparseable: {e}"
    try:
        fields = (client or RekorClient(server)).fetch_entry(uuid)
    except (RuntimeError, OSError) as e:
        return False, f"could not fetch rekor entry {uuid[:16]}...: {e}"
    try:
        logged = decode_logged_payload(fields)
    except (ValueError, KeyError) as e:
        return False, f"logged entry {uuid[:16]}... is not an AIR anchor: {e}"

    for field in ("chain_head", "chain_seq_max", "anchored_at"):
        if str(logged.get(field)) != str(embedded.get(field)):
            return False, (
                f"the bundle's embedded anchor disagrees with the logged "
                f"entry on {field}: bundle says {embedded.get(field)!r}, the "
                f"public log says {logged.get(field)!r}")

    # -1 is the "publisher never learned the index" sentinel (RekorAnchor
    # defaults to it when the publish response carries no logIndex), so it is
    # an absence, not a disagreement. Comparing it would reject bundles the
    # log itself confirms.
    claimed = anchor.get("log_index")
    actual = fields.get("logIndex")
    if (claimed is not None and actual is not None
            and int(claimed) >= 0 and int(claimed) != int(actual)):
        return False, (f"log index mismatch: the bundle claims {claimed}, the "
                       f"entry is at {actual}")
    return True, (f"entry {uuid[:16]}... found in the public log at index "
                  f"{actual if actual is not None else claimed}, committing "
                  "to the same head")


def audit_runs_against_log(runs_dir: str, public_key_raw: bytes,
                           client: RekorClient) -> LogAuditResult:
    """Fetch EVERY anchor logged under the anchoring key and recompute the
    bounded chain head for each. This is the M2 guarantee: a rewritten
    history - even one freshly re-anchored - fails against the old entries,
    because a public append-only log cannot un-say them.
    """
    from air_blackbox.anchor.head import compute_head

    result = LogAuditResult()
    for uuid in client.search_by_public_key(public_key_raw):
        try:
            fields = client.fetch_entry(uuid)
            payload = decode_logged_payload(fields)
        except (RuntimeError, ValueError, KeyError):
            # Entries under this key that are not AIR anchors are not ours to
            # judge - but count them so a flooded key is visible.
            result.unparseable += 1
            continue
        result.anchors_checked += 1
        seq = int(payload["chain_seq_max"])
        want = payload["chain_head"]
        got = compute_head(runs_dir, up_to_seq=seq)
        if got == want:
            result.consistent += 1
        else:
            result.mismatches.append({
                "uuid": uuid, "logged_seq_max": seq,
                "logged_head": want, "recomputed_head": got,
                "integrated_time": fields.get("integratedTime"),
            })
    return result
