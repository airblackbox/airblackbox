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
   record_action again with action "human_approved_<original_action>".
4. When unsure whether something is allowed, call check_covenant first.
5. When the user asks for proof, a report, or an audit trail, call
   verify_chain and export_evidence.

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

_auth_verifier, _auth_settings = build_auth()
app = FastMCP("air-blackbox", instructions=_INSTRUCTIONS,
              token_verifier=_auth_verifier, auth=_auth_settings)


def _rule_exists(action: str, context: dict) -> bool:
    """True if any covenant rule targets this action name at all - used to
    distinguish an explicit policy decision from a default-deny vocabulary
    miss, which must never masquerade as corroboration."""
    return any(rule.matches(action, context) for rule in _covenant.rules)

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
        # resume=True: a server restart continues the tenant's existing chain
        # instead of starting a second genesis-rooted chain in the same
        # directory (which could never verify as one).
        chain = AuditChain(runs_dir=_tenant_runs_dir(tenant), resume=True)
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
    if _covenant:
        record["covenant_hash"] = _covenant.hash
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


@app.tool()
def log_screening_decision(candidate: str, decision: str,
                           rationale: str = "") -> str:
    """REQUIRED whenever you evaluate, rank, advance, reject, or recommend
    an outcome for a candidate - even informally in conversation. Call this
    BEFORE stating the decision to the user.

    decision must be one of: advance, reject, score, rank, shortlist, hold.
    Candidate-affecting decisions are automated decision-making under GDPR
    Art 22 / EU AI Act Art 14: if this returns REQUIRES HUMAN APPROVAL, stop
    and get the user's explicit yes before finalizing anything.
    """
    action_map = {
        "advance": "advance_candidate", "reject": "reject_candidate",
        "score": "score_candidate", "rank": "rank_candidates",
        "shortlist": "rank_candidates", "hold": "score_candidate",
    }
    action = action_map.get(decision.strip().lower(), "score_candidate")
    return record_action(
        action=action,
        detail=f"candidate={candidate[:100]}; decision={decision}; "
               f"rationale={rationale[:300]}",
        category="screening",
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
