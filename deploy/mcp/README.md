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

## Integrating an application (not a Claude session)

A hosted product writes receipts through `POST /ingest` instead of the MCP
tools: it keeps a durable outbox and this server is the single writer, because
a serverless app cannot own a single-writer audit chain without forking it.

    fly secrets set AIR_INGEST_TOKENS="$(openssl rand -hex 32):acme-corp"

Full contract, client requirements, and failure semantics:
[docs/guides/ingest-integration.md](../../docs/guides/ingest-integration.md)

## Remote (claude.ai custom connector) — tethered to airblackbox.ai

```bash
# from repo root
fly launch --copy-config --no-deploy        # app: air-mcp
fly volumes create air_data --size 1
fly secrets set TRUST_SIGNING_KEY=$(openssl rand -hex 32)

# --- OAuth (pick one; see "Turning on authentication" below) ---
# Production (JWKS): validate IdP-signed JWTs locally
fly secrets set AIR_MCP_JWKS_URL=https://YOUR-IDP/.well-known/jwks.json
fly secrets set AIR_MCP_JWT_ISSUER=https://YOUR-IDP
fly secrets set AIR_MCP_JWT_AUDIENCE=https://mcp.airblackbox.ai
# Alternative (RFC 7662): introspect opaque tokens per request
fly secrets set AIR_MCP_INTROSPECTION_URL=https://YOUR-IDP/oauth/introspect
fly secrets set AIR_MCP_INTROSPECTION_AUTH="Basic <base64 client:secret>"
# Self-host: one static bearer token per tenant (programmatic clients only)
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

Without `AIR_MCP_JWKS_URL`, `AIR_MCP_INTROSPECTION_URL`, or `AIR_MCP_TOKENS`
set, the server runs open (correct for local stdio use, never for a public
deployment). With auth enabled, a request that cannot be attributed to an
authenticated subject is **denied** — it is never recorded into a shared
chain, because evidence that can't say whose it is is worse than no evidence.

## Turning on authentication

claude.ai custom connectors speak OAuth as a client: they read this server's
`/.well-known/oauth-protected-resource`, register themselves with the
authorization server it names (**Dynamic Client Registration — the IdP must
support it**), and run the browser login flow. So real-user auth needs an
IdP; WorkOS AuthKit and Auth0 both support DCR and publish JWKS.

Walkthrough (WorkOS AuthKit shown; Auth0 is analogous):

1. Create an AuthKit environment; note the issuer URL
   (`https://<slug>.authkit.app`). Enable Dynamic Client Registration
   (Applications → Configuration).
2. Point this server at it:
   ```bash
   fly secrets set \
     AIR_MCP_JWKS_URL=https://<slug>.authkit.app/oauth2/jwks \
     AIR_MCP_JWT_ISSUER=https://<slug>.authkit.app \
     AIR_MCP_JWT_AUDIENCE=https://mcp.airblackbox.ai \
     AIR_MCP_ISSUER_URL=https://<slug>.authkit.app
   ```
   (`AIR_MCP_ISSUER_URL` is what `/.well-known/oauth-protected-resource`
   advertises — it must name the IdP, not this server.)
3. `fly deploy`, then add the connector in claude.ai. The connector prompts
   the user to log in; every request thereafter carries a JWT whose `sub`
   claim becomes the tenant id.
4. Verify isolation: two different logins → two subdirectories under
   `/data/runs`, separate chains, separate evidence bundles.

Each user's identity in the evidence is the IdP subject — which is exactly
what an auditor wants: "who did this" answered by a system the operator
doesn't control.

## Tools

| Tool | Purpose |
|------|---------|
| `record_action` | Write a covenant-evaluated action into the chain (forbidden → recorded as blocked; approval-required → instructs Claude to get human sign-off). |
| `check_covenant` | Ask the policy before acting. |
| `verify_chain` | Prove integrity of this tenant's records. |
| `export_evidence` | Package this tenant's session into a signed `.air-evidence` ZIP. |
