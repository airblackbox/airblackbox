"""AIR Blackbox MCP server - governance inside Claude itself.

Connect this to Claude (Desktop or claude.ai custom connector) and every
agent action Claude takes can be declared, recorded, and proven:

- record_action: writes a chained, tamper-evident AIR record for an action
  (covenant-evaluated first when one is loaded). This is the flight
  recorder for Claude-native workflows the gateway cannot see.
- check_covenant: ask before acting - permit / forbid / require_approval.
- verify_chain: live integrity check over everything recorded so far.
- export_evidence: package the session into a signed .air-evidence ZIP.

Storage: records land in AIR_RUNS_DIR (default ~/.air-blackbox/runs), the
same format the gateway writes, so lake export, replay, and evidence
tooling all apply unchanged.

Run:  python -m air_blackbox.mcp_server
Claude Desktop config:
  {"mcpServers": {"air-blackbox": {"command": "python",
    "args": ["-m", "air_blackbox.mcp_server"]}}}
"""

import contextlib
import glob
import hashlib
import hmac
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

try:                      # POSIX only; the server ships in a Linux container.
    import fcntl
except ImportError:       # pragma: no cover - Windows dev boxes
    fcntl = None

logger = logging.getLogger("air_blackbox.mcp")

from mcp.server.fastmcp import FastMCP

from air_blackbox.gate.covenant import Covenant
from air_blackbox.gate.receipt import (
    HAS_MLDSA65 as _HAS_MLDSA,
    ActionReceipt,
    ReceiptSigner,
    hash_payload,
)
from air_blackbox.mcp_auth import build_auth
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.trust.chain import AuditChain

RUNS_DIR = os.environ.get(
    "AIR_RUNS_DIR", os.path.expanduser("~/.air-blackbox/runs"))
COVENANT_PATH = os.environ.get("AIR_COVENANT", "")

_INSTRUCTIONS = """AIR Blackbox is active: this conversation is governed and
its agent actions are recorded into a tamper-evident audit chain.

While this connector is enabled you MUST:
1. Before any consequential or externally-visible action (reading a person's
   profile, drafting or sending outreach, scoring/advancing/rejecting a
   candidate, writing to another system), call record_action with a short
   action name (snake_case) and a one-line detail.
2. If record_action says BLOCKED, do not perform the action. Tell the user
   the policy blocked it.
3. If record_action says REQUIRES HUMAN APPROVAL, stop and ask the user to
   explicitly approve. Only proceed after they clearly say yes, then call
   record_action with action "human_approval" and a detail naming what was
   approved (e.g. "reject_candidate for Dana Okafor, approved by user").
4. When unsure whether something is allowed, call check_covenant first.
5. When the user asks for proof, a report, or an audit trail, call
   verify_chain (records unaltered), verify_receipts (who authorized each
   action), and verify_anchor (an external authority countersigned the
   history, so even a re-signed rewrite is detectable), then export_evidence.

This is not optional bookkeeping: the recorded chain is the user's
compliance evidence. Unrecorded actions do not exist for audit purposes."""

_covenant: Optional[Covenant] = (
    Covenant.from_yaml(COVENANT_PATH) if COVENANT_PATH else None)


def _covenant_vocabulary(covenant: Covenant) -> str:
    """The covenant is default-deny: an action name with no rule is forbidden.
    Claude therefore needs the exact vocabulary, or every natural-language
    action description silently reads as forbid."""
    by_action: dict = {"permit": [], "require_approval": [], "forbid": []}
    for rule in covenant.rules:
        by_action.setdefault(rule.action.value, []).append(rule.target)
    lines = [f"\nActive covenant: '{covenant.agent}'. It is DEFAULT-DENY and "
             "matches EXACT action names only - always use these snake_case "
             "names with record_action/check_covenant, never free-text "
             "descriptions:"]
    for kind in ("permit", "require_approval", "forbid"):
        if by_action.get(kind):
            lines.append(f"  {kind}: {', '.join(sorted(set(by_action[kind])))}")
    lines.append("Unlisted actions are treated as forbidden by default; use "
                 "check_covenant to test a name before relying on it.")
    return "\n".join(lines)


if _covenant:
    _INSTRUCTIONS += "\n" + _covenant_vocabulary(_covenant)

def _transport_security():
    """DNS-rebinding protection trusts only localhost by default, which
    rejects the real hostname behind a proxy (Fly, a load balancer, etc.).
    List the public host(s) in AIR_MCP_ALLOWED_HOSTS (comma-separated); the
    issuer host is trusted automatically. Set AIR_MCP_ALLOWED_HOSTS=* to
    disable the check (only behind a trusted proxy that sets Host)."""
    from urllib.parse import urlparse

    from mcp.server.transport_security import TransportSecuritySettings

    raw = os.environ.get("AIR_MCP_ALLOWED_HOSTS", "").strip()
    if raw == "*":
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    hosts = {h.strip() for h in raw.split(",") if h.strip()}
    issuer = os.environ.get("AIR_MCP_ISSUER_URL", "")
    if issuer:
        host = urlparse(issuer).netloc
        if host:
            hosts.add(host)
    hosts.update({"localhost", "127.0.0.1"})
    if not hosts:
        return None
    # Trust both bare host and host:port, and matching origins.
    expanded = set()
    for h in hosts:
        expanded.add(h)
        expanded.add(f"{h}:{os.environ.get('AIR_MCP_PORT', '8085')}")
    origins = {f"https://{h}" for h in hosts} | {f"http://{h}" for h in hosts}
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(expanded),
        allowed_origins=sorted(origins),
    )


_auth_verifier, _auth_settings = build_auth()
app = FastMCP("air-blackbox", instructions=_INSTRUCTIONS,
              token_verifier=_auth_verifier, auth=_auth_settings,
              transport_security=_transport_security())


@app.custom_route("/health", methods=["GET"])
async def _health(request):
    """Unauthenticated health probe for load balancers / Fly health checks.

    "ok" means the server can actually do its job - record evidence - not
    merely that the process exists, so the probe write-tests the runs root
    (the volume in production). 503 turns an invisible full/unmounted/
    read-only volume into a failing check the platform acts on.
    """
    from starlette.responses import JSONResponse
    try:
        os.makedirs(RUNS_DIR, exist_ok=True)
        probe = os.path.join(RUNS_DIR, ".health-probe")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
    except OSError as exc:
        logger.error("health probe cannot write runs dir %s: %s", RUNS_DIR, exc)
        return JSONResponse(
            {"status": "degraded", "service": "air-blackbox-mcp",
             "detail": "runs storage not writable"},
            status_code=503)
    return JSONResponse({"status": "ok", "service": "air-blackbox-mcp"})


def _asset(name: str) -> bytes:
    with open(os.path.join(os.path.dirname(__file__), "mcp_assets", name),
              "rb") as f:
        return f.read()


@app.custom_route("/favicon.svg", methods=["GET"])
async def _favicon_svg(request):
    """Brand mark (compact, ground-on-ink). claude.ai and other clients
    resolve the connector icon from the server origin's favicon."""
    from starlette.responses import Response
    return Response(_asset("favicon.svg"), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.custom_route("/favicon.ico", methods=["GET"])
async def _favicon_ico(request):
    from starlette.responses import Response
    return Response(_asset("logo.png"), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.custom_route("/logo.png", methods=["GET"])
async def _logo_png(request):
    from starlette.responses import Response
    return Response(_asset("logo.png"), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


# --- Public demo audit endpoint -------------------------------------------
# Lets the airblackbox.ai demo candidate page record page accesses on a REAL
# tamper-evident chain with zero client setup (works from any surface,
# including Claude in Chrome, which cannot mount MCP connectors). Privacy:
# no visitor data is recorded - only that an access occurred, when. The
# in-memory throttle map is transient and never written to the chain.
_DEMO_TENANT = "public-demo"
_DEMO_CORS = {
    "Access-Control-Allow-Origin": "https://airblackbox.ai",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}
_demo_seen: dict = {}   # client key -> monotonic seconds of last recorded view
_DEMO_MIN_INTERVAL = 20.0
_DEMO_MAX_RECORDS = 5000  # stop growing the public chain past this


def _demo_chain_state() -> dict:
    engine = ReplayEngine(runs_dir=_tenant_runs_dir(_DEMO_TENANT))
    total = engine.load()
    result = engine.verify_chain()
    return {"records": total,
            "chain_intact": bool(result.intact),
            "tenant": _DEMO_TENANT}


@app.custom_route("/demo/view", methods=["POST", "OPTIONS"])
async def _demo_view(request):
    """Record a demo-page access on the public-demo chain and return the
    resulting chain hash. Throttled per client; over-throttle requests get
    the current chain state without a new record."""
    import time as _time

    from starlette.responses import JSONResponse, Response
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=_DEMO_CORS)

    client = (request.client.host if request.client else "unknown")
    now = _time.monotonic()
    if len(_demo_seen) > 4096:
        _demo_seen.clear()  # transient throttle map; never persisted
    last = _demo_seen.get(client, 0.0)
    state = _demo_chain_state()
    if now - last < _DEMO_MIN_INTERVAL or state["records"] >= _DEMO_MAX_RECORDS:
        return JSONResponse({**state, "recorded": False}, headers=_DEMO_CORS)
    _demo_seen[client] = now

    out = _record_event(
        action="read_profile",
        detail="public demo: candidate profile page accessed "
               "(airblackbox.ai/demo/candidate; no visitor data recorded)",
        category="demo",
        tenant=_DEMO_TENANT)
    chain_hash = out.rsplit("chain_hash=", 1)[-1].rstrip(".")
    state = _demo_chain_state()
    return JSONResponse({**state, "recorded": True,
                         "chain_hash": chain_hash}, headers=_DEMO_CORS)


@app.custom_route("/demo/status", methods=["GET"])
async def _demo_status(request):
    """Current public-demo chain state (records + integrity verdict)."""
    from starlette.responses import JSONResponse
    return JSONResponse(_demo_chain_state(), headers=_DEMO_CORS)


# ---------------------------------------------------------------------------
# Ingest - server-to-server intake for apps that cannot own the chain.
#
# AuditChain is a single-writer design: its lock is a threading.Lock and
# resume() replays the whole history to recover prev_hash. A serverless app
# (Vercel functions, Lambda) violates both assumptions - the filesystem is
# ephemeral, and concurrent invocations would each resume from the same
# prev_hash and claim the same chain_seq, forking the chain into something
# that can never verify. That failure is silent, which makes it worse than a
# crash.
#
# So the app keeps a durable outbox and POSTs batches here, and THIS process
# is the single writer. Two properties make that safe:
#
#   Idempotency - an outbox retries (timeouts, cold starts mid-flush), so the
#   same event_id will arrive more than once. A redelivered duplicate would
#   append a phantom record and still verify clean. Every event therefore
#   carries a client-generated event_id; a repeat returns the original
#   receipt_id and writes nothing.
#
#   Exclusivity - a second writer process (extra worker, second machine on a
#   shared volume) is refused with 409 rather than allowed to fork the chain.
#   A client outbox retries a 409 cleanly; a forked chain is unrecoverable.
# ---------------------------------------------------------------------------

#: Cap on one flush so a runaway outbox cannot hold the writer lock forever.
_INGEST_MAX_EVENTS = 100

_ingest_locks: dict = {}          # tenant -> threading.Lock
_ingest_locks_guard = threading.Lock()
_ingest_index_cache: dict = {}    # tenant -> {event_id: receipt_id}


class _ChainBusy(Exception):
    """Another process holds this tenant's write lock."""


def _ingest_tokens() -> dict:
    """Parse AIR_INGEST_TOKENS ("token:tenant,token2:tenant2") -> {token: tenant}.

    Tokens are bound to a tenant here rather than trusting the tenant in the
    request body, so a leaked token cannot write into another tenant's chain.
    """
    out = {}
    for pair in os.environ.get("AIR_INGEST_TOKENS", "").split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        token, tenant = pair.split(":", 1)
        if token.strip() and tenant.strip():
            out[token.strip()] = tenant.strip()
    return out


def _ingest_auth(request):
    """-> (tenant, None) on success, or (None, (status, message))."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None, (401, "missing bearer token")
    presented = header[7:].strip()
    tokens = _ingest_tokens()
    if not tokens:
        # Unconfigured is a deployment state, not a bad credential: say so
        # plainly instead of making the caller debug their token.
        return None, (503, "ingest is not configured on this server")
    matched = None
    for token, tenant in tokens.items():
        # compare_digest on every candidate: no early exit, so response time
        # does not leak which prefix was right.
        if hmac.compare_digest(token, presented):
            matched = tenant
    if matched is None:
        return None, (401, "invalid token")
    return matched, None


def _ingest_index(tenant: str) -> dict:
    """{event_id: receipt_id} for everything already ingested for a tenant.

    Rebuilt from the records themselves rather than a side index, so it can
    never drift from the chain it is supposed to describe. Read once per
    tenant per process, then kept current in memory by the writer.
    """
    index = _ingest_index_cache.get(tenant)
    if index is None:
        index = {}
        pattern = os.path.join(_tenant_runs_dir(tenant), "*.air.json")
        for path in glob.glob(pattern):
            try:
                with open(path) as f:
                    record = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            event_id = record.get("event_id")
            if event_id:
                index[event_id] = (record.get("receipt") or {}).get(
                    "receipt_id", "")
        _ingest_index_cache[tenant] = index
    return index


@contextlib.contextmanager
def _ingest_writer_lock(tenant: str):
    """Serialize writes to one tenant's chain.

    Threads queue on the in-process lock; a competing PROCESS is refused
    outright (409) rather than queued, because a writer that waits behind an
    unknown holder is indistinguishable from one that is about to fork the
    chain. Fail closed: the client still holds the events.
    """
    with _ingest_locks_guard:
        lock = _ingest_locks.setdefault(tenant, threading.Lock())
    with lock:
        runs = _tenant_runs_dir(tenant)
        os.makedirs(runs, exist_ok=True)
        if fcntl is None:                     # pragma: no cover
            yield
            return
        handle = open(os.path.join(runs, ".air-ingest.lock"), "w")
        try:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise _ChainBusy()
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            handle.close()


def _ingest_write(tenant: str, event: dict):
    """Chain one ingested event. Returns (receipt_id, chain_hash).

    occurred_at is preserved separately from the server's write timestamp:
    with an outbox those genuinely differ, and the audit story needs when the
    decision was MADE, not when it happened to drain.
    """
    action = str(event.get("action") or "").strip() or "agent_action"
    detail = str(event.get("detail") or "")
    category = str(event.get("category") or "")

    decision = "permit"
    if _covenant:
        decision = _covenant.evaluate(action, {
            "model": "", "tokens_total": 0,
            "category": category, "detail": detail}).value

    record = {
        "run_id": str(uuid.uuid4()),
        "event_id": str(event["event_id"]).strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "occurred_at": str(event.get("occurred_at") or ""),
        "type": "agent_action",
        "source": "ingest",
        "action": action,
        "detail": detail[:2000],
        "model": "",
        "status": "blocked" if decision == "forbid" else "success",
        "covenant_decision": decision,
        "tokens": {"total": 0},
    }
    # Pass structured blocks through untouched. screening is what the
    # evidence bundle categorizes on; attributes is the caller's own
    # vocabulary, which this server deliberately does not interpret.
    for key in ("screening", "attributes"):
        if isinstance(event.get(key), dict):
            record[key] = event[key]
    if _covenant:
        record["covenant_hash"] = _covenant.hash
    record["receipt"] = _sign_receipt(tenant, action, decision, detail,
                                      category)
    chain_hash = _tenant_chain(tenant).write(record)
    return record["receipt"].get("receipt_id", ""), chain_hash


@app.custom_route("/ingest", methods=["POST"])
async def _ingest(request):
    """Accept a batch of events from an application and chain them.

    Body: {"tenant": ..., "events": [{"event_id", "action", "detail",
    "category", "occurred_at", "screening"?, "attributes"?}, ...]}
    Returns: {"results": [{"event_id", "receipt_id", "chain_hash",
    "duplicate"?}, ...]} in request order.
    """
    from starlette.responses import JSONResponse

    tenant_for_token, err = _ingest_auth(request)
    if err:
        return JSONResponse({"error": err[1]}, status_code=err[0])

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "body must be JSON"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "body must be a JSON object"},
                            status_code=400)

    tenant = str(body.get("tenant") or "").strip()
    if not tenant:
        return JSONResponse({"error": "tenant is required"}, status_code=400)
    if tenant != tenant_for_token:
        return JSONResponse(
            {"error": "token is not valid for this tenant"}, status_code=403)

    events = body.get("events")
    if not isinstance(events, list) or not events:
        return JSONResponse({"error": "events must be a non-empty array"},
                            status_code=400)
    if len(events) > _INGEST_MAX_EVENTS:
        return JSONResponse(
            {"error": f"batch too large (max {_INGEST_MAX_EVENTS} events)"},
            status_code=413)
    # Validate the whole batch before writing any of it, so a malformed
    # tail cannot leave a half-written flush the client must reconcile.
    for event in events:
        if not isinstance(event, dict):
            return JSONResponse({"error": "each event must be an object"},
                                status_code=400)
        if not str(event.get("event_id") or "").strip():
            return JSONResponse(
                {"error": "every event needs an event_id (idempotency key)"},
                status_code=400)

    results = []
    try:
        with _ingest_writer_lock(tenant):
            index = _ingest_index(tenant)
            for event in events:
                event_id = str(event["event_id"]).strip()
                if event_id in index:
                    results.append({"event_id": event_id,
                                    "receipt_id": index[event_id],
                                    "duplicate": True})
                    continue
                receipt_id, chain_hash = _ingest_write(tenant, event)
                index[event_id] = receipt_id
                results.append({"event_id": event_id,
                                "receipt_id": receipt_id,
                                "chain_hash": chain_hash})
    except _ChainBusy:
        return JSONResponse(
            {"error": "chain unavailable: another writer holds this tenant"},
            status_code=409)

    logger.info("ingest tenant=%s events=%d written=%d", tenant, len(events),
                sum(1 for r in results if not r.get("duplicate")))
    return JSONResponse({"results": results})


@app.custom_route("/ingest/status", methods=["GET"])
async def _ingest_status(request):
    """Chain state for the authenticated tenant, so a caller's own health
    endpoint can confirm events are actually landing here."""
    from starlette.responses import JSONResponse

    tenant, err = _ingest_auth(request)
    if err:
        return JSONResponse({"error": err[1]}, status_code=err[0])
    engine = ReplayEngine(runs_dir=_tenant_runs_dir(tenant))
    total = engine.load()
    result = engine.verify_chain()
    ingested = len(_ingest_index(tenant))
    return JSONResponse({
        "tenant": tenant,
        "records": total,
        "ingested_events": ingested,
        "chain_intact": bool(result.intact),
        "single_writer": fcntl is not None,
    })


def _rule_exists(action: str, context: dict) -> bool:
    """True if any covenant rule targets this action name at all - used to
    distinguish an explicit policy decision from a default-deny vocabulary
    miss, which must never masquerade as corroboration."""
    return any(rule.matches(action, context) for rule in _covenant.rules)

# Per-tenant chains, keyed by the authenticated OAuth subject. Without auth
# every request shares the single "_local" tenant.
_chains: dict = {}


def _safe_tenant(subject: str) -> str:
    """Map an authenticated subject to a filesystem-safe, INJECTIVE tenant id.

    The mapping must be injective: two different subjects must never share a
    tenant, or one tenant could read/write another's audit records. Folding
    non-alphanumerics to '_' and truncating (the previous approach) is NOT
    injective - 'alice@corp.com' and 'alice_corp_com' collide, and any two
    subjects agreeing on their first N chars collide under truncation.

    We take a readable-but-lossy prefix only for debuggability and append a
    hash of the FULL subject; uniqueness comes entirely from the hash. The
    hash suffix also guarantees the result can never equal a reserved tenant
    name (_local, the demo tenant), so no authenticated subject can land in
    the shared/unauthenticated stores.
    """
    digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]
    readable = "".join(c if c.isalnum() or c in "-" else "_" for c in subject)
    readable = readable.strip("_")[:32].strip("_") or "t"
    return f"{readable}-{digest}"


def _current_tenant() -> str:
    """Resolve the authenticated subject for this request.

    Auth disabled: everything is the single "_local" tenant. Auth enabled:
    the subject MUST resolve - a request that reaches a tool without an
    authenticated subject is denied, never silently written into a shared
    chain. Evidence that can't say whose it is is worse than no evidence.
    """
    if _auth_verifier is None:
        return "_local"
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token
        token = get_access_token()
    except Exception as exc:
        raise PermissionError(
            "auth is enabled but no authenticated subject is available "
            "for this request") from exc
    if token and token.subject:
        return _safe_tenant(token.subject)
    raise PermissionError(
        "auth is enabled but this request carries no authenticated subject")


def _tenant_runs_dir(tenant: str) -> str:
    return RUNS_DIR if tenant == "_local" else os.path.join(RUNS_DIR, tenant)


def _tenant_chain(tenant: str) -> AuditChain:
    chain = _chains.get(tenant)
    if chain is None:
        # resume=True: a server restart continues the tenant's existing chain
        # instead of starting a second genesis-rooted chain in the same
        # directory (which could never verify as one).
        chain = AuditChain(runs_dir=_tenant_runs_dir(tenant), resume=True)
        _chains[tenant] = chain
    return chain


# Per-tenant Gate receipt signers. Ed25519 (or ML-DSA-65 if available) gives
# every action a non-repudiable signature that anyone can verify with the
# PUBLIC key alone - no shared secret, unlike the HMAC chain. This is the Gate
# "bilateral receipt": the chain proves nothing was altered, the receipt
# proves who authorized it.
_signers: dict = {}


def _load_tenant_key(key_path: str):
    """Parse a persisted tenant key file. Returns ("ed25519", seed_bytes),
    ("ML-DSA-65", (pub, secret)), or None if absent/unreadable.

    Two formats:
      - legacy: bare hex of a 32-byte Ed25519 seed (pre-#63 tenants). Honored
        forever so an existing tenant's public key never changes.
      - v2 JSON: {"algorithm": ..., plus hex key fields}, which can carry the
        ML-DSA-65 keypair (the secret alone cannot re-derive the public key,
        so both are stored).
    """
    try:
        with open(key_path) as f:
            raw = f.read().strip()
    except OSError:
        return None
    if raw.startswith("{"):
        try:
            doc = json.loads(raw)
            alg = doc.get("algorithm", "")
            if alg == "ML-DSA-65":
                return (alg, (bytes.fromhex(doc["public_key"]),
                              bytes.fromhex(doc["secret_key"])))
            if alg == "ed25519":
                return (alg, bytes.fromhex(doc["seed"]))
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
        return None
    try:
        seed = bytes.fromhex(raw)
        return ("ed25519", seed) if len(seed) == 32 else None
    except ValueError:
        return None


def _persist_tenant_key(key_path: str, doc: dict) -> None:
    """Write a v2 key file (0600). Failure is non-fatal but the tenant's
    public key will then change on restart - warn, don't refuse service."""
    try:
        with open(key_path, "w") as f:
            json.dump(doc, f)
        os.chmod(key_path, 0o600)
    except OSError:
        logger.warning(
            "could not persist receipt key at %s; public key will not "
            "be stable across restarts", key_path)


def _tenant_signer(tenant: str) -> ReceiptSigner:
    signer = _signers.get(tenant)
    if signer is None:
        runs = _tenant_runs_dir(tenant)
        os.makedirs(runs, exist_ok=True)
        key_path = os.path.join(runs, ".air-receipt-key")
        hmac_key = os.environ.get("TRUST_SIGNING_KEY")
        # Own the key so the tenant's public key is stable across restarts.
        loaded = _load_tenant_key(key_path)
        if loaded is not None and loaded[0] == "ML-DSA-65" and _HAS_MLDSA:
            signer = ReceiptSigner(mldsa_keypair=loaded[1], hmac_key=hmac_key)
        elif loaded is not None and loaded[0] == "ed25519":
            # Includes every pre-#63 tenant: their identity is Ed25519 and
            # stays Ed25519. Migrating would rotate their public key.
            signer = ReceiptSigner(private_key=loaded[1], hmac_key=hmac_key)
        elif _HAS_MLDSA:
            # New tenant with the pqc extra installed: post-quantum from
            # day one, persisted so it survives restarts (#63).
            signer = ReceiptSigner(hmac_key=hmac_key)
            pub, secret = signer.mldsa_keypair
            _persist_tenant_key(key_path, {
                "algorithm": "ML-DSA-65",
                "public_key": pub.hex(),
                "secret_key": secret.hex(),
            })
        else:
            # New tenant, classical: fresh Ed25519 seed.
            priv = os.urandom(32)
            _persist_tenant_key(key_path, {
                "algorithm": "ed25519", "seed": priv.hex(),
            })
            signer = ReceiptSigner(private_key=priv, hmac_key=hmac_key)
        _signers[tenant] = signer
    return signer


def _sign_receipt(tenant: str, action: str, decision: str, detail: str,
                  category: str) -> dict:
    """Produce a signed Gate receipt for an action and return it as a dict to
    embed in the chained record. The signature covers the action, decision,
    and covenant hash - independently verifiable from the record alone."""
    receipt = ActionReceipt(
        agent_id=tenant,
        action_name=action,
        action_category=category or "",
        payload_hash=hash_payload(detail) if detail else "",
        covenant_hash=_covenant.hash if _covenant else "",
        decision=decision,
        authorized=(decision == "permit"),
    )
    _tenant_signer(tenant).sign_authorization(receipt)
    return receipt.to_dict()


def _record_event(action: str, detail: str = "", model: str = "",
                  tokens_total: int = 0, category: str = "",
                  extra: dict | None = None,
                  tenant: str | None = None) -> str:
    """Shared core for record_action and log_screening_decision: evaluate
    the covenant, build the record (plus any structured extra fields), sign
    the receipt, and chain it. tenant overrides the auth-derived tenant
    (used by the public demo endpoint, which has no auth context)."""
    tenant = tenant or _current_tenant()
    decision = "permit"
    no_rule = False
    if _covenant:
        context = {"model": model, "tokens_total": tokens_total,
                   "category": category, "detail": detail}
        no_rule = not _rule_exists(action, context)
        decision = _covenant.evaluate(action, context).value

    record = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "agent_action",
        "action": action,
        "detail": detail[:2000],
        "model": model,
        "status": "blocked" if decision == "forbid" else "success",
        "covenant_decision": decision,
        "tokens": {"total": tokens_total},
    }
    if extra:
        record.update(extra)
    if _covenant:
        record["covenant_hash"] = _covenant.hash
    # Attach a signed Gate receipt: the record now carries a non-repudiable
    # signature verifiable with the tenant's public key, chained for
    # tamper-evidence.
    record["receipt"] = _sign_receipt(tenant, action, decision, detail, category)
    chain_hash = _tenant_chain(tenant).write(record)

    if decision == "forbid":
        if no_rule:
            return (
                f"NO RULE MATCHED: the covenant has no rule named "
                f"'{action}' and is default-deny, so this was recorded as "
                f"blocked (chain_hash={chain_hash}). This is a vocabulary "
                f"miss, NOT an explicit policy decision. Re-record using one "
                f"of the covenant's exact action names (see check_covenant "
                f"or the server instructions), or ask the user how to "
                f"classify this action.")
        return (f"BLOCKED by covenant rule (recorded, chain_hash={chain_hash}). "
                f"Do not perform this action.")
    if decision == "require_approval":
        return (f"Recorded (chain_hash={chain_hash}) but this action "
                f"REQUIRES HUMAN APPROVAL before you proceed. Ask the user "
                f"to explicitly approve, then record the approval.")
    return f"Recorded, chain_hash={chain_hash}"


@app.tool()
def record_action(action: str, detail: str = "", model: str = "",
                  tokens_total: int = 0, category: str = "") -> str:
    """Record an agent action into the tamper-evident audit chain.

    Call this for every consequential step you take (profile read,
    outreach draft, decision, message sent). If a covenant is loaded and
    forbids the action, it is recorded as BLOCKED and you must not
    proceed with it.
    """
    return _record_event(action=action, detail=detail, model=model,
                         tokens_total=tokens_total, category=category)


@app.tool()
def check_covenant(action: str, category: str = "") -> str:
    """Check what the loaded covenant says about an action name before doing
    it. Uses EXACT matching against the covenant's snake_case action names -
    free-text descriptions will report 'no rule' (default-deny)."""
    if not _covenant:
        return "No covenant loaded (set AIR_COVENANT). Default: unrestricted."
    context = {"category": category}
    decision = _covenant.evaluate(action, context)
    if not _rule_exists(action, context):
        return (f"Covenant '{_covenant.agent}': no rule named '{action}' - "
                f"default-deny applies (forbid). This reflects the covenant's "
                f"vocabulary, not a judgment about the action itself."
                + _covenant_vocabulary(_covenant))
    return f"Covenant '{_covenant.agent}': {action} -> {decision.value} (explicit rule)"


@app.tool()
def verify_chain() -> str:
    """Verify the integrity of everything recorded so far for this tenant."""
    engine = ReplayEngine(runs_dir=_tenant_runs_dir(_current_tenant()))
    total = engine.load()
    result = engine.verify_chain()
    if not result.intact:
        return (f"CHAIN BROKEN at record {result.first_break_at} "
                f"(run {result.first_break_run_id}). "
                f"{result.verified_records} of {total} verified before the break.")
    if total == 0:
        return "No records yet: nothing to verify."
    if result.verified_records < total:
        # Never say INTACT when part of the evidence is outside the chain.
        unchained = total - result.records_with_hash
        return (f"PARTIAL: {result.verified_records} of {total} records "
                f"verified; {unchained} carry no chain hash and CANNOT be "
                f"verified for tampering. The verifiable portion is intact, "
                f"but this store is not fully attestable - tell the user.")
    return (f"CHAIN INTACT: all {result.verified_records} records verified. "
            f"No tampering detected.")


@app.tool()
def verify_receipts() -> str:
    """Verify the Ed25519 signature on every recorded action for this tenant.

    Unlike verify_chain (which proves records were not altered, using the
    shared HMAC key), this proves WHO authorized each action using public-key
    signatures - anyone can verify with the public key, no secret needed."""
    import json as _json

    tenant = _current_tenant()
    signer = _tenant_signer(tenant)
    engine = ReplayEngine(runs_dir=_tenant_runs_dir(tenant))
    engine.load()

    checked = valid = 0
    for raw in engine._raw_records:
        r = raw.get("receipt")
        if not r:
            continue
        checked += 1
        if signer.verify_authorization(_receipt_from_dict(r)):
            valid += 1

    pub = signer.public_key_hex or "(hmac fallback - no public key)"
    if checked == 0:
        return f"No signed receipts yet. Signing method: {signer.method}."
    if valid == checked:
        return (f"ALL RECEIPTS VALID: {valid}/{checked} signatures verified "
                f"({signer.method}). Public key: {pub}. Anyone can verify these "
                f"with the public key alone - no shared secret required.")
    return (f"RECEIPT FAILURE: only {valid} of {checked} signatures verified "
            f"({signer.method}). {checked - valid} receipt(s) do not match - "
            f"tell the user.")


def _receipt_from_dict(d: dict) -> ActionReceipt:
    """Reconstruct an ActionReceipt from a stored record for verification."""
    from air_blackbox.gate.receipt import ReceiptStatus
    r = ActionReceipt(
        receipt_id=d.get("receipt_id", ""),
        agent_id=d.get("agent_id", ""),
        action_name=d.get("action_name", ""),
        action_category=d.get("action_category", ""),
        payload_hash=d.get("payload_hash", ""),
        covenant_hash=d.get("covenant_hash", ""),
        decision=d.get("decision", ""),
        authorized=d.get("authorized", False),
        parent_receipt_id=d.get("parent_receipt_id"),
        authorization_sig=d.get("authorization_sig", ""),
        created_at=d.get("created_at", ""),
        signing_method=d.get("signing_method", ""),
        signing_public_key=d.get("signing_public_key", ""),
    )
    return r


@app.tool()
def export_evidence() -> str:
    """Package all recorded actions into a signed .air-evidence bundle
    (v1 layout: manifest.json, records/, verification/, mapping/,
    attachments/) aligned to SB 26-189 deployer documentation duties.
    The bundle supports an impact assessment and is audit-ready; it is
    not a legal compliance determination."""
    return _export_tenant(_current_tenant())


def _export_tenant(tenant: str) -> str:
    """Core evidence export for one tenant. Called by the export_evidence
    tool and by the auto-export scheduler - evidence must never depend on
    a busy human remembering to ask for it."""
    from dataclasses import asdict

    from air_blackbox.export.evidence_bundle import generate_evidence_bundle_v1
    runs = _tenant_runs_dir(tenant)
    engine = ReplayEngine(runs_dir=runs)
    total = engine.load()

    # The bundle must never quietly attest a broken or partial chain: verify
    # first and stamp the result INTO the signed payload, so a downstream
    # auditor sees the integrity verdict before anything else.
    verification = engine.verify_chain()
    fully_intact = verification.intact and verification.verified_records == total

    # Anchor the head at an external TSA BEFORE packaging, so the timestamp
    # token travels inside the signed bundle (verifiable offline by a stranger).
    anchor_note, anchor_manifest = _anchor_current_head(tenant)

    # Deployer-supplied register info and attachments. Missing values are
    # exported as "deployer-supplied" so gaps are explicit, never hidden.
    system = {
        "name": os.environ.get("AIR_SYSTEM_NAME", ""),
        "high_risk_rationale": os.environ.get("AIR_HIGH_RISK_RATIONALE", ""),
        "deployer": os.environ.get("AIR_SYSTEM_DEPLOYER", ""),
    }
    attachments_dir = os.environ.get(
        "AIR_ATTACHMENTS_DIR", os.path.join(runs, "attachments"))

    path, manifest = generate_evidence_bundle_v1(
        chain_entries=engine._raw_records,
        tenant=tenant,
        signer=_tenant_signer(tenant),
        chain_verification={"fully_intact": fully_intact,
                            **asdict(verification)},
        system=system,
        attachments_dir=attachments_dir,
        anchor_manifest=anchor_manifest,
        output_dir=runs)

    if not verification.intact:
        return (f"WARNING - BROKEN CHAIN EXPORTED: {path}. The chain fails "
                f"verification at record {verification.first_break_at} (run "
                f"{verification.first_break_run_id}); the bundle is signed and "
                f"its manifest records the failure, so it attests a broken "
                f"chain - it is NOT clean compliance evidence. Tell the user.")
    if not fully_intact:
        unchained = total - verification.records_with_hash
        return (f"WARNING - PARTIAL CHAIN EXPORTED: {path}. "
                f"{verification.verified_records} of {total} records verified; "
                f"{unchained} carry no chain hash. The manifest records this. "
                f"Tell the user.")
    gaps = manifest["counts"]["screening_decisions_missing_reviewer"]
    gap_note = ""
    if gaps:
        gap_note = (f" NOTE: {gaps} screening decision(s) carry no "
                    f"human_reviewer - flagged in the manifest as review-"
                    f"protocol gaps; tell the user.")
    return (f"Evidence bundle written: {path} ({total} records, chain fully "
            f"verified at export time; verification stamped into the signed "
            f"manifest; verify independently with 'air-evidence verify "
            f"<bundle>'). {anchor_note}{gap_note}")


def _anchor_dir(tenant: str) -> str:
    d = os.path.join(_tenant_runs_dir(tenant), "anchors")
    os.makedirs(d, exist_ok=True)
    return d


def _anchor_current_head(tenant: str):
    """Timestamp the current chain head at an external TSA and persist the
    token. An unreachable TSA is recorded as a gap, never silently dropped.
    Returns (note, manifest_dict) - the manifest goes into the signed bundle."""
    import base64
    import json as _json

    from air_blackbox.anchor import compute_head, timestamp_head

    runs = _tenant_runs_dir(tenant)
    engine = ReplayEngine(runs_dir=runs)
    engine.load()
    seq_max = max((r.get("chain_seq") or 0 for r in engine._raw_records), default=0)
    head = compute_head(runs)
    if not head:
        return "Anchor: no chained records to anchor.", {"anchored": False,
                                                         "reason": "no records"}

    result = timestamp_head(head, _tsa_urls())
    if not result.ok:
        # An anchor gap is itself evidence - record it, do not hide it.
        with open(os.path.join(_anchor_dir(tenant), "gaps.log"), "a") as f:
            f.write(_json.dumps({"seq_max": seq_max, "head": head,
                                 "error": result.error}) + "\n")
        note = (f"Anchor: GAP - no external timestamp obtained ({result.error}). "
                f"Recorded as a gap; the head is not externally bound this export.")
        manifest = {"anchored": False, "head": head, "seq_max": seq_max,
                    "error": result.error}
    else:
        manifest = {"anchored": True, "head": head, "seq_max": seq_max,
                    "tsa_url": result.tsa_url, "timestamp": result.timestamp,
                    "tsr_b64": base64.b64encode(result.tsr).decode()}
        note = (f"Anchor: head bound to {result.tsa_url} at {result.timestamp}. "
                f"A rewritten history cannot inherit this timestamp.")

    # M2: also publish the head to the public transparency log (opt-in).
    # The two rails fail independently: a TSA gap does not block the log
    # anchor, and vice versa - each is recorded honestly on its own.
    rekor_server = _rekor_server()
    if rekor_server:
        from air_blackbox.anchor.rekor import anchor_head_to_rekor
        try:
            rk = anchor_head_to_rekor(head, seq_max, _anchor_key(tenant),
                                      server=rekor_server)
            manifest["rekor"] = rk.to_dict()
            note += (f" Public log: entry {rk.uuid[:16]}... at index "
                     f"{rk.log_index} - permanent; a re-anchored rewrite is "
                     f"still detectable against it.")
        except Exception as e:  # unreachable log = a gap, never a crash
            with open(os.path.join(_anchor_dir(tenant), "gaps.log"), "a") as f:
                f.write(_json.dumps({"seq_max": seq_max, "head": head,
                                     "rekor_error": str(e)}) + "\n")
            manifest["rekor"] = {"anchored": False, "error": str(e)}
            note += f" Public log: GAP ({e}); recorded, not hidden."

    if manifest.get("anchored"):
        with open(os.path.join(_anchor_dir(tenant),
                               f"anchor-{seq_max:012d}.json"), "w") as f:
            _json.dump(manifest, f)
    return note, manifest


def _tsa_urls():
    urls = os.environ.get("AIR_TSA_URLS", "")
    return [u.strip() for u in urls.split(",") if u.strip()] or None


def _rekor_server() -> Optional[str]:
    """Public transparency-log anchoring is opt-in: AIR_REKOR_SERVER names a
    server explicitly, or AIR_REKOR=1 uses the public Sigstore instance.
    Returns None (off) otherwise - anchoring publishes the chain HEAD (a
    hash, no record content) to a public log, so it is a deliberate choice."""
    server = os.environ.get("AIR_REKOR_SERVER", "").strip()
    if server:
        return server
    if os.environ.get("AIR_REKOR", "") == "1":
        from air_blackbox.anchor.rekor import DEFAULT_REKOR_SERVER
        return DEFAULT_REKOR_SERVER
    return None


def _anchor_key(tenant: str) -> bytes:
    """Per-tenant Ed25519 anchoring seed (.air-anchor-key). Separate from the
    receipt key: receipts may be ML-DSA-65, which public logs cannot verify
    yet, and the anchor key is an index handle - the security property comes
    from the log's append-onlyness, not from who holds this key."""
    path = os.path.join(_tenant_runs_dir(tenant), ".air-anchor-key")
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


@app.tool()
def verify_anchor() -> str:
    """Verify the external timestamp anchor for this tenant.

    verify_chain and verify_receipts prove records were not altered and who
    signed them - but the operator holds those keys and could rewrite and
    re-sign the whole history. This checks the RFC 3161 timestamp: an external
    authority countersigned the chain head at a past time with a key the
    operator does not control, so a rewritten head no longer matches it."""
    import base64
    import glob as _glob
    import json as _json

    from air_blackbox.anchor import compute_head, verify_anchor_bytes

    tenant = _current_tenant()
    anchors = sorted(_glob.glob(os.path.join(_anchor_dir(tenant), "anchor-*.json")))
    if not anchors:
        gaps = os.path.join(_anchor_dir(tenant), "gaps.log")
        if os.path.exists(gaps):
            return ("NO ANCHOR: the head has never been externally timestamped "
                    "(anchor gaps recorded). Run export_evidence with a reachable "
                    "TSA. Until then, a rewritten history would NOT be detectable "
                    "by anchoring - tell the user.")
        return "NO ANCHOR yet: run export_evidence to timestamp the chain head."

    with open(anchors[-1]) as f:
        m = _json.load(f)
    tsr = base64.b64decode(m["tsr_b64"])
    # Re-derive the head over exactly the records the anchor covered. A rewrite
    # of any of those records changes this head and breaks the match.
    head_now = compute_head(_tenant_runs_dir(tenant), up_to_seq=m["seq_max"])
    ok, detail = verify_anchor_bytes(head_now, tsr, ca_pem=os.environ.get("AIR_TSA_CACERT"))
    if ok:
        return (f"ANCHOR VALID: an external authority ({m['tsa_url']}) "
                f"countersigned this history's head at {m['timestamp']}. The "
                f"records up to sequence {m['seq_max']} have not been rewritten "
                f"since - verifiable by a third party against the TSA, no secret "
                f"of ours required.")
    return (f"ANCHOR BROKEN: {detail}. The history covered by the timestamp from "
            f"{m['timestamp']} has been altered since it was anchored - tell the user.")


@app.tool()
def audit_public_log() -> str:
    """Audit this tenant's history against EVERY anchor ever published to the
    public transparency log (M2 - the strongest tamper check available).

    verify_anchor checks the latest RFC 3161 timestamp, but an attacker who
    rewrites history can obtain a FRESH timestamp for the new head. They
    cannot, however, remove old entries from a public append-only log. This
    fetches every anchor logged under this tenant's anchoring key and
    recomputes the bounded chain head for each - a rewritten history fails
    against the old entries, even if it was freshly re-anchored."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    from air_blackbox.anchor.rekor import RekorClient, audit_runs_against_log

    server = _rekor_server()
    if not server:
        return ("Public-log anchoring is not enabled. Set AIR_REKOR=1 (public "
                "Sigstore Rekor) or AIR_REKOR_SERVER, then export_evidence to "
                "publish anchors. Until then, only the RFC 3161 rail applies "
                "- and its documented limit is the re-anchored rewrite.")
    tenant = _current_tenant()
    pub_raw = Ed25519PrivateKey.from_private_bytes(
        _anchor_key(tenant)).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    try:
        audit = audit_runs_against_log(_tenant_runs_dir(tenant), pub_raw,
                                       RekorClient(server))
    except Exception as e:
        return (f"Public log unreachable ({e}). No verdict - the audit needs "
                f"the log. Try again with network access to {server}.")
    if audit.anchors_checked == 0:
        return ("No anchors found in the public log for this tenant's key. "
                "Run export_evidence (with AIR_REKOR enabled) to publish the "
                "first one.")
    if audit.rewrite_detected:
        worst = audit.mismatches[0]
        return (f"REWRITE DETECTED: {len(audit.mismatches)} of "
                f"{audit.anchors_checked} logged anchors do NOT match this "
                f"history (first: entry {worst['uuid'][:16]}... committed to "
                f"head {worst['logged_head'][:16]}... at seq "
                f"{worst['logged_seq_max']}, but the records re-derive "
                f"{str(worst['recomputed_head'])[:16]}...). The log entry is "
                f"permanent - this history cannot be squared with what was "
                f"published. Tell the user immediately.")
    return (f"PUBLIC LOG CONSISTENT: all {audit.anchors_checked} anchors ever "
            f"published for this tenant match the current history. Even an "
            f"attacker with every local key could not have rewritten these "
            f"records without breaking this check.")


@app.tool()
def log_screening_decision(candidate: str, decision: str,
                           rationale: str = "",
                           decision_type: str = "",
                           human_reviewer: str = "",
                           review_action: str = "",
                           covenant_check_ref: str = "") -> str:
    """REQUIRED whenever you evaluate, rank, advance, reject, or recommend
    an outcome for a candidate - even informally in conversation. Call this
    BEFORE stating the decision to the user.

    decision must be one of: advance, reject, score, rank, shortlist, hold.
    Candidate-affecting decisions are automated decision-making under GDPR
    Art 22 / EU AI Act Art 14: if this returns REQUIRES HUMAN APPROVAL, stop
    and get the user's explicit yes before finalizing anything.

    Human-review-protocol fields (SB 26-189 deployer documentation - fill
    whenever a human was involved; decisions recorded without a
    human_reviewer are flagged as gaps in the exported evidence bundle):
      decision_type      - advance | reject | rank | recommend
      human_reviewer     - identity of the person who reviewed the output
      review_action      - approved | overridden | modified
      covenant_check_ref - chain hash of the check_covenant / record_action
                           result that gated this decision
    """
    action_map = {
        "advance": "advance_candidate", "reject": "reject_candidate",
        "score": "score_candidate", "rank": "rank_candidates",
        "shortlist": "rank_candidates", "hold": "score_candidate",
    }
    d = decision.strip().lower()
    action = action_map.get(d, "score_candidate")
    if not decision_type:
        # Derive the SB 26-189 decision_type from the decision verb so every
        # screening record is categorizable even when the caller omits it.
        decision_type = {"advance": "advance", "reject": "reject",
                         "rank": "rank", "shortlist": "rank"}.get(d, "recommend")
    screening = {"decision_type": decision_type}
    if human_reviewer:
        screening["human_reviewer"] = human_reviewer[:100]
    if review_action:
        screening["review_action"] = review_action.strip().lower()[:20]
    if covenant_check_ref:
        screening["covenant_check_ref"] = covenant_check_ref[:128]
    return _record_event(
        action=action,
        detail=f"candidate={candidate[:100]}; decision={decision}; "
               f"rationale={rationale[:300]}",
        category="screening",
        extra={"screening": screening},
    )


@app.prompt()
def governed_sourcing(role: str = "the open role") -> str:
    """Start a recorded, policy-governed candidate sourcing session."""
    return f"""You are helping me source and screen candidates for {role}.
This session is governed by AIR Blackbox: record every consequential step
with record_action (profile reads, summaries, drafts, and especially any
send/score/advance/reject decision), honor BLOCKED decisions, and pause for
my explicit approval whenever an action requires it. At the end of the
session, run verify_chain and export_evidence so I have the signed audit
trail. Begin by asking me for the candidates or search criteria."""


@app.prompt()
def compliance_report() -> str:
    """Verify the audit chain and produce the evidence bundle."""
    return """Please verify the integrity of my recorded agent activity and
produce my compliance evidence: call verify_chain, summarize what it shows
in plain language (what was recorded, whether anything was blocked or
required approval), then call export_evidence and tell me where the signed
bundle is."""


# --- Auto-export: evidence must not depend on a busy human asking --------
# With AIR_AUTO_EXPORT_INTERVAL_HOURS set, every tenant with new records
# since its last bundle gets a fresh signed .air-evidence written to its
# runs directory on the interval. Records and bundles live wherever the
# deployer mounts AIR_RUNS_DIR (a volume, S3-backed mount, NFS - storage
# the org controls), so evidence accumulates with zero user action.
_AUTO_EXPORT_STATE = ".air-auto-export.json"


def _tenants_on_disk() -> list:
    """Every tenant that has chained records: the root dir ("_local") plus
    one subdirectory per authenticated tenant."""
    import glob as _glob
    tenants = []
    if _glob.glob(os.path.join(RUNS_DIR, "*.air.json")):
        tenants.append("_local")
    try:
        for name in sorted(os.listdir(RUNS_DIR)):
            sub = os.path.join(RUNS_DIR, name)
            if os.path.isdir(sub) and _glob.glob(os.path.join(sub, "*.air.json")):
                tenants.append(name)
    except OSError as exc:
        # Tenant discovery is degraded, not fatal: sweep whoever we found.
        logger.warning("auto_export cannot list %s: %s", RUNS_DIR, exc)
    return tenants


def _auto_export_once() -> int:
    """Export a fresh bundle for every tenant with records newer than its
    last export. Returns the number of bundles written. Never raises: one
    tenant's failure must not starve the others."""
    import glob as _glob
    import json as _json
    exported = 0
    for tenant in _tenants_on_disk():
        runs = _tenant_runs_dir(tenant)
        count = len(_glob.glob(os.path.join(runs, "*.air.json")))
        state_path = os.path.join(runs, _AUTO_EXPORT_STATE)
        last = 0
        try:
            with open(state_path) as f:
                last = int(_json.load(f).get("exported_records", 0))
        except (OSError, ValueError) as exc:
            # Missing on first sweep is normal; anything else means the
            # high-water mark reset to 0 and this sweep re-exports.
            if not isinstance(exc, FileNotFoundError):
                logger.warning(
                    "auto_export state unreadable for tenant=%s, "
                    "resetting to 0: %s", tenant, exc)
        if count <= last:
            continue
        try:
            _export_tenant(tenant)
            with open(state_path, "w") as f:
                _json.dump({"exported_records": count,
                            "exported_at": datetime.now(timezone.utc).isoformat()}, f)
            exported += 1
            logger.info("auto_export tenant=%s records=%d", tenant, count)
        except Exception:
            logger.exception("auto_export failed tenant=%s", tenant)
    return exported


def _start_auto_export():
    """Start the daemon scheduler when AIR_AUTO_EXPORT_INTERVAL_HOURS > 0."""
    try:
        hours = float(os.environ.get("AIR_AUTO_EXPORT_INTERVAL_HOURS", "0") or 0)
    except ValueError:
        logger.warning("invalid AIR_AUTO_EXPORT_INTERVAL_HOURS; auto-export off")
        return None
    if hours <= 0:
        return None
    import threading
    import time as _time

    def _loop():
        while True:
            _time.sleep(hours * 3600)
            try:
                _auto_export_once()
            except Exception:
                logger.exception("auto_export sweep failed")

    t = threading.Thread(target=_loop, daemon=True, name="air-auto-export")
    t.start()
    logger.info("auto_export enabled: every %.2fh", hours)
    return t


def _init_error_tracking():
    """Optional Sentry error tracking, engaged only when SENTRY_DSN is set.

    A no-op for self-hosters (no DSN, no dependency needed). For the hosted
    deployment it is the "know before the customer does" layer: unhandled
    exceptions are reported with stack traces instead of dying silently in
    ephemeral platform logs. Records/prompts are never attached - Sentry
    sees exceptions, not tenant data.
    """
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "pip install 'air-blackbox[monitor]'. Continuing without it.")
        return
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0,
                    send_default_pii=False)
    logger.info("sentry error tracking enabled")


def main():
    """Run over stdio (Claude Desktop) or HTTP (claude.ai custom connector).

    AIR_MCP_TRANSPORT=http serves streamable HTTP on AIR_MCP_HOST:AIR_MCP_PORT
    (default 0.0.0.0:8085, endpoint /mcp) - put it behind TLS at e.g.
    https://mcp.airblackbox.ai/mcp and add it in claude.ai as a custom
    connector. Default is stdio for local Claude Desktop use.
    """
    _init_error_tracking()
    _start_auto_export()
    if os.environ.get("AIR_MCP_TRANSPORT", "stdio") == "http":
        app.settings.host = os.environ.get("AIR_MCP_HOST", "0.0.0.0")
        app.settings.port = int(os.environ.get("AIR_MCP_PORT", "8085"))
        app.run(transport="streamable-http")
    else:
        app.run()


if __name__ == "__main__":
    main()
