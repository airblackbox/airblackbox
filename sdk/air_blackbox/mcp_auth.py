"""OAuth token verification for the AIR Blackbox MCP server.

The server acts as an OAuth 2.1 *resource server*: it does not issue tokens,
it verifies bearer tokens presented by claude.ai on each request. Two modes,
selected by environment:

- Introspection (production): set AIR_MCP_INTROSPECTION_URL to an RFC 7662
  endpoint on your identity provider (Auth0, WorkOS, Okta, Keycloak...).
  claude.ai obtains a token from that IdP; every MCP request's token is
  introspected. AIR_MCP_INTROSPECTION_AUTH optionally sets a Bearer/Basic
  header for the introspection call itself.

- Static tokens (self-host / dev): set AIR_MCP_TOKENS to a comma-separated
  list of `token:subject:scope1|scope2` triples. Simple, no IdP required,
  and still gives per-tenant isolation via subject.

The verified subject is what isolates tenants: each subject records into its
own chain, so one recruiter's evidence never mixes with another's.
"""

import os
import time
from typing import Optional

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl


class StaticTokenVerifier(TokenVerifier):
    """Verify against a fixed token->subject map from AIR_MCP_TOKENS."""

    def __init__(self, spec: str):
        self._tokens = {}
        for entry in spec.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":")
            token = parts[0]
            subject = parts[1] if len(parts) > 1 and parts[1] else token[:12]
            scopes = parts[2].split("|") if len(parts) > 2 and parts[2] else []
            self._tokens[token] = (subject, scopes)

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        entry = self._tokens.get(token)
        if not entry:
            return None
        subject, scopes = entry
        return AccessToken(token=token, client_id=subject, subject=subject,
                           scopes=scopes, expires_at=None)


class IntrospectionTokenVerifier(TokenVerifier):
    """Verify via RFC 7662 token introspection against an external IdP."""

    def __init__(self, url: str, auth_header: Optional[str] = None):
        self._url = url
        self._auth_header = auth_header

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self._auth_header:
            headers["Authorization"] = self._auth_header
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self._url, data={"token": token},
                                         headers=headers)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("active"):
            return None
        exp = data.get("exp")
        if exp and exp < time.time():
            return None
        scopes = data.get("scope", "")
        subject = data.get("sub") or data.get("client_id") or "unknown"
        return AccessToken(
            token=token,
            client_id=data.get("client_id", subject),
            subject=subject,
            scopes=scopes.split() if isinstance(scopes, str) else list(scopes),
            expires_at=int(exp) if exp else None,
        )


def build_auth():
    """Return (verifier, AuthSettings) if OAuth is configured, else (None, None).

    OAuth engages when AIR_MCP_INTROSPECTION_URL or AIR_MCP_TOKENS is set.
    Unset means the server runs open (fine for local Claude Desktop / stdio).
    """
    introspection = os.environ.get("AIR_MCP_INTROSPECTION_URL", "")
    static = os.environ.get("AIR_MCP_TOKENS", "")
    if not introspection and not static:
        return None, None

    if introspection:
        verifier = IntrospectionTokenVerifier(
            introspection, os.environ.get("AIR_MCP_INTROSPECTION_AUTH") or None)
    else:
        verifier = StaticTokenVerifier(static)

    issuer = os.environ.get("AIR_MCP_ISSUER_URL", "https://mcp.airblackbox.ai")
    resource = os.environ.get("AIR_MCP_RESOURCE_URL", issuer)
    required = os.environ.get("AIR_MCP_REQUIRED_SCOPES", "")
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=AnyHttpUrl(resource),
        required_scopes=[s for s in required.split(",") if s] or None,
    )
    return verifier, settings
