# AIR Blackbox Governance MCP Server

Governance inside Claude: record every agent action into a tamper-evident
chain, enforce a covenant before acting, and export signed evidence — as a
connector, on your own domain.

## Local (Claude Desktop)

```bash
pip install air-blackbox[mcp]
```

```json
{"mcpServers": {"air-blackbox": {"command": "air-blackbox-mcp",
  "env": {"AIR_COVENANT": "/path/to/recruiting-screener.covenant.yaml"}}}}
```

## Remote (claude.ai custom connector) — tethered to airblackbox.ai

```bash
# from repo root
fly launch --copy-config --no-deploy        # app: air-mcp
fly volumes create air_data --size 1
fly secrets set TRUST_SIGNING_KEY=$(openssl rand -hex 32)

# --- OAuth (pick one) ---
# Production: verify claude.ai tokens against your IdP (Auth0/WorkOS/Okta/...)
fly secrets set AIR_MCP_INTROSPECTION_URL=https://YOUR-IDP/oauth/introspect
fly secrets set AIR_MCP_INTROSPECTION_AUTH="Basic <base64 client:secret>"
# Self-host: one static bearer token per tenant
fly secrets set AIR_MCP_TOKENS="tok-alice:recruiter-alice,tok-bob:recruiter-bob"

fly deploy
fly certs add mcp.airblackbox.ai
# DNS: CNAME mcp.airblackbox.ai -> air-mcp.fly.dev
```

Then in claude.ai: **Settings → Connectors → Add custom connector →**
`https://mcp.airblackbox.ai/mcp`

## OAuth model

The server is an OAuth 2.1 **resource server**: it verifies bearer tokens,
it does not issue them. `/.well-known/oauth-protected-resource` advertises
the auth server so claude.ai can negotiate. No token → `401`.

**Tenant isolation:** the verified token subject keys a per-tenant chain,
so each connected user's records, verification, and evidence bundle are
fully separate — one recruiter's evidence never mixes with another's.

Without `AIR_MCP_INTROSPECTION_URL` or `AIR_MCP_TOKENS` set, the server runs
open (correct for local stdio use, never for a public deployment).

## Tools

| Tool | Purpose |
|------|---------|
| `record_action` | Write a covenant-evaluated action into the chain (forbidden → recorded as blocked; approval-required → instructs Claude to get human sign-off). |
| `check_covenant` | Ask the policy before acting. |
| `verify_chain` | Prove integrity of this tenant's records. |
| `export_evidence` | Package this tenant's session into a signed `.air-evidence` ZIP. |
