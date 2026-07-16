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

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP

from air_blackbox.gate.covenant import Covenant
from air_blackbox.mcp_auth import build_auth
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.trust.chain import AuditChain

RUNS_DIR = os.environ.get(
    "AIR_RUNS_DIR", os.path.expanduser("~/.air-blackbox/runs"))
COVENANT_PATH = os.environ.get("AIR_COVENANT", "")

_auth_verifier, _auth_settings = build_auth()
app = FastMCP("air-blackbox",
              token_verifier=_auth_verifier, auth=_auth_settings)
_covenant: Optional[Covenant] = (
    Covenant.from_yaml(COVENANT_PATH) if COVENANT_PATH else None)

# Per-tenant chains, keyed by the authenticated OAuth subject. Without auth
# every request shares the single "_local" tenant.
_chains: dict = {}


def _safe_tenant(subject: str) -> str:
    # Keep tenant ids filesystem-safe; never let a subject escape RUNS_DIR.
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in subject)[:64]


def _current_tenant() -> str:
    """Resolve the authenticated subject for this request, or the local tenant."""
    if _auth_verifier is None:
        return "_local"
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token
        token = get_access_token()
        if token and token.subject:
            return _safe_tenant(token.subject)
    except Exception:
        # Any failure to read the auth context (no request scope, middleware
        # not active) intentionally falls back to the isolated local tenant.
        pass
    return "_local"


def _tenant_runs_dir(tenant: str) -> str:
    return RUNS_DIR if tenant == "_local" else os.path.join(RUNS_DIR, tenant)


def _tenant_chain(tenant: str) -> AuditChain:
    chain = _chains.get(tenant)
    if chain is None:
        chain = AuditChain(runs_dir=_tenant_runs_dir(tenant))
        _chains[tenant] = chain
    return chain


@app.tool()
def record_action(action: str, detail: str = "", model: str = "",
                  tokens_total: int = 0, category: str = "") -> str:
    """Record an agent action into the tamper-evident audit chain.

    Call this for every consequential step you take (profile read,
    outreach draft, decision, message sent). If a covenant is loaded and
    forbids the action, it is recorded as BLOCKED and you must not
    proceed with it.
    """
    tenant = _current_tenant()
    decision = "permit"
    if _covenant:
        context = {"model": model, "tokens_total": tokens_total,
                   "category": category, "detail": detail}
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
    if _covenant:
        record["covenant_hash"] = _covenant.hash
    chain_hash = _tenant_chain(tenant).write(record)

    if decision == "forbid":
        return (f"BLOCKED by covenant (recorded, chain_hash={chain_hash}). "
                f"Do not perform this action.")
    if decision == "require_approval":
        return (f"Recorded (chain_hash={chain_hash}) but this action "
                f"REQUIRES HUMAN APPROVAL before you proceed. Ask the user "
                f"to explicitly approve, then record the approval.")
    return f"Recorded, chain_hash={chain_hash}"


@app.tool()
def check_covenant(action: str, category: str = "") -> str:
    """Check what the loaded covenant says about an action before doing it."""
    if not _covenant:
        return "No covenant loaded (set AIR_COVENANT). Default: unrestricted."
    decision = _covenant.evaluate(action, {"category": category})
    return f"Covenant '{_covenant.agent}': {action} -> {decision.value}"


@app.tool()
def verify_chain() -> str:
    """Verify the integrity of everything recorded so far for this tenant."""
    engine = ReplayEngine(runs_dir=_tenant_runs_dir(_current_tenant()))
    total = engine.load()
    result = engine.verify_chain()
    if result.intact:
        return (f"CHAIN INTACT: {result.verified_records} of {total} records "
                f"verified. No tampering detected.")
    return (f"CHAIN BROKEN at record {result.first_break_at} "
            f"(run {result.first_break_run_id}).")


@app.tool()
def export_evidence() -> str:
    """Package all recorded actions into a signed .air-evidence ZIP."""
    from air_blackbox.export.evidence_bundle import generate_evidence_zip
    tenant = _current_tenant()
    runs = _tenant_runs_dir(tenant)
    engine = ReplayEngine(runs_dir=runs)
    engine.load()
    key = os.environ.get("TRUST_SIGNING_KEY", "air-blackbox-default")
    path = generate_evidence_zip(
        chain_entries=engine._raw_records,
        scan_results={"source": "air-blackbox MCP server", "tenant": tenant,
                      "records": len(engine._raw_records)},
        signing_key=key, output_dir=runs)
    return f"Evidence bundle written: {path} ({len(engine._raw_records)} records)"


def main():
    """Run over stdio (Claude Desktop) or HTTP (claude.ai custom connector).

    AIR_MCP_TRANSPORT=http serves streamable HTTP on AIR_MCP_HOST:AIR_MCP_PORT
    (default 0.0.0.0:8085, endpoint /mcp) - put it behind TLS at e.g.
    https://mcp.airblackbox.ai/mcp and add it in claude.ai as a custom
    connector. Default is stdio for local Claude Desktop use.
    """
    if os.environ.get("AIR_MCP_TRANSPORT", "stdio") == "http":
        app.settings.host = os.environ.get("AIR_MCP_HOST", "0.0.0.0")
        app.settings.port = int(os.environ.get("AIR_MCP_PORT", "8085"))
        app.run(transport="streamable-http")
    else:
        app.run()


if __name__ == "__main__":
    main()
