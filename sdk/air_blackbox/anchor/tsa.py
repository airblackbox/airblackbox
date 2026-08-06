"""RFC 3161 timestamp anchoring via the openssl CLI (no new Python deps).

Key-agnostic by design (see ADR 0001): the TSA signs the head with ITS key,
so our Ed25519-vs-Rekor incompatibility never enters the picture. Multiple TSA
URLs are tried in order and the responder is recorded; an anchor that cannot be
obtained is reported as a gap, never silently dropped.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Optional

# httpx is imported lazily inside the functions that POST/GET, so the module
# loads - and offline verification with a provided CA works - without it.

# Public RFC 3161 timestamp authorities, tried in order.
DEFAULT_TSA_URLS = [
    "https://freetsa.org/tsr",
    "https://timestamp.sigstore.dev/api/v1/timestamp",
    "http://timestamp.digicert.com",
]

# CA cert chains for the TSAs above, for offline verification. FreeTSA's is the
# one we bundle by default; operators can supply their own via ca_pem.
FREETSA_CACERT_URL = "https://freetsa.org/files/cacert.pem"


@dataclass
class AnchorResult:
    """The outcome of anchoring a head. On success, `tsr` is the DER RFC 3161
    token and `tsa_url` names the responder; on failure, `error` explains the
    gap (which the caller must record, not swallow)."""
    ok: bool
    head: str
    tsr: Optional[bytes] = None
    tsa_url: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


def _openssl(args: List[str], stdin: Optional[bytes] = None) -> subprocess.CompletedProcess:
    return subprocess.run(["openssl"] + args, input=stdin,
                          capture_output=True, timeout=30)


def make_query(head_hex: str) -> bytes:
    """Build an RFC 3161 timestamp query (TSQ) over a 32-byte head."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "req.tsq")
        r = _openssl(["ts", "-query", "-digest", head_hex, "-sha256",
                      "-cert", "-out", out])
        if r.returncode != 0:
            raise RuntimeError(f"ts -query failed: {r.stderr.decode(errors='replace')}")
        with open(out, "rb") as f:
            return f.read()


def timestamp_head(head_hex: str,
                   tsa_urls: Optional[List[str]] = None,
                   timeout: float = 20.0) -> AnchorResult:
    """Obtain an RFC 3161 timestamp over the head from the first reachable TSA.

    timeout is PER URL, and the default list holds three, so a caller that
    must answer an interactive request should pass a smaller value: an
    unreachable TSA otherwise costs timeout x len(urls) before returning.
    An anchor gap is recorded honestly by the caller, so failing fast costs
    nothing but the anchor itself.
    """
    if not head_hex:
        return AnchorResult(ok=False, head=head_hex, error="no chain head to anchor")
    import httpx

    urls = tsa_urls or DEFAULT_TSA_URLS
    try:
        tsq = make_query(head_hex)
    except Exception as e:  # noqa: BLE001 - report as a gap, never crash export
        return AnchorResult(ok=False, head=head_hex, error=str(e))

    last_err = "no TSA reachable"
    for url in urls:
        try:
            resp = httpx.post(url, content=tsq, timeout=timeout,
                              headers={"Content-Type": "application/timestamp-query"})
        except httpx.HTTPError as e:
            last_err = f"{url}: {e}"
            continue
        if resp.status_code != 200 or not resp.content:
            last_err = f"{url}: HTTP {resp.status_code}"
            continue
        tsr = resp.content
        ts = _extract_time(tsr)
        return AnchorResult(ok=True, head=head_hex, tsr=tsr, tsa_url=url, timestamp=ts)

    return AnchorResult(ok=False, head=head_hex, error=last_err)


def _extract_time(tsr: bytes) -> Optional[str]:
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "resp.tsr")
        with open(p, "wb") as f:
            f.write(tsr)
        r = _openssl(["ts", "-reply", "-in", p, "-text"])
        for line in r.stdout.decode(errors="replace").splitlines():
            if line.strip().startswith("Time stamp:"):
                return line.split("Time stamp:", 1)[1].strip()
    return None


def verify_anchor_bytes(head_hex: str, tsr: bytes,
                        ca_pem: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Verify a TSR commits to head_hex, against a TSA CA chain.

    Returns (ok, detail). This is the operation that makes a rewritten history
    detectable: recompute the current head, and if it differs from what the TSR
    countersigned, verification fails with a message-imprint mismatch.
    """
    if not tsr:
        return False, "no timestamp token"
    with tempfile.TemporaryDirectory() as d:
        tsr_path = os.path.join(d, "resp.tsr")
        with open(tsr_path, "wb") as f:
            f.write(tsr)

        ca_path = ca_pem
        if ca_path is None:
            # Fetch FreeTSA's CA when no local CA was supplied. Offline
            # verification (ca_pem provided) needs no network and no httpx.
            import httpx
            try:
                ca = httpx.get(FREETSA_CACERT_URL, timeout=15.0).content
                ca_path = os.path.join(d, "cacert.pem")
                with open(ca_path, "wb") as f:
                    f.write(ca)
            except httpx.HTTPError as e:
                return False, f"could not obtain TSA CA chain: {e}"

        r = _openssl(["ts", "-verify", "-digest", head_hex, "-in", tsr_path,
                      "-CAfile", ca_path, "-no_check_time"])
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode == 0 and "Verification: OK" in out:
            return True, "anchor commits to the current head"
        if "message imprint mismatch" in out:
            return False, "message imprint mismatch: the current head does not " \
                          "match what the timestamp countersigned (history was rewritten)"
        return False, out.strip().splitlines()[-1] if out.strip() else "verification failed"
