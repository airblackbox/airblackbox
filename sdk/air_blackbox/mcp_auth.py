"""OAuth token verification for the AIR Blackbox MCP server.

The server acts as an OAuth 2.1 *resource server*: it does not issue tokens,
it verifies bearer tokens presented by claude.ai on each request. Three modes,
selected by environment (first match wins: JWKS, introspection, static):

- JWT / JWKS (production, most IdPs): set AIR_MCP_JWKS_URL to your identity
  provider's JWKS endpoint (WorkOS AuthKit, Auth0, Okta, Keycloak all publish
  one). Tokens are validated locally against the IdP's published signing
  keys - no per-request network call. AIR_MCP_JWT_ISSUER and
  AIR_MCP_JWT_AUDIENCE pin the expected iss/aud claims; set both in
  production so a token minted for another API can't be replayed here.

- Introspection (RFC 7662): set AIR_MCP_INTROSPECTION_URL to an
  introspection endpoint (Keycloak, or any IdP offering opaque tokens).
  Every MCP request's token is introspected. AIR_MCP_INTROSPECTION_AUTH
  optionally sets a Bearer/Basic header for the introspection call itself.

- Static tokens (self-host / dev): set AIR_MCP_TOKENS to a comma-separated
  list of `token:subject:scope1|scope2` triples. Simple, no IdP required,
  and still gives per-tenant isolation via subject.

Note for claude.ai custom connectors: claude.ai speaks OAuth as a client and
discovers the authorization server through this server's protected-resource
metadata, so AIR_MCP_ISSUER_URL must point at an IdP that supports Dynamic
Client Registration (WorkOS AuthKit and Auth0 do). Static tokens work for
programmatic clients and self-hosted setups, not the claude.ai connector UI.

The verified subject is what isolates tenants: each subject records into its
own chain, so one recruiter's evidence never mixes with another's.
"""

import hashlib
import logging
import os
import time
from typing import Optional

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

logger = logging.getLogger("air_blackbox.mcp_auth")


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
            if not token:
                # A malformed entry like ":sub" or "::" would otherwise
                # register an empty-string token that authenticates.
                continue
            # When no explicit subject is given, derive it from a hash of the
            # FULL token, never a prefix: two tokens sharing a brand/product
            # prefix (a common generation pattern) must not collapse onto the
            # same tenant.
            if len(parts) > 1 and parts[1]:
                subject = parts[1]
            else:
                subject = "tok-" + hashlib.sha256(
                    token.encode("utf-8")).hexdigest()[:16]
            scopes = parts[2].split("|") if len(parts) > 2 and parts[2] else []
            self._tokens[token] = (subject, scopes)

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        entry = self._tokens.get(token)
        if not entry:
            return None
        subject, scopes = entry
        return AccessToken(token=token, client_id=subject, subject=subject,
                           scopes=scopes, expires_at=None)


class JwtTokenVerifier(TokenVerifier):
    """Validate signed JWTs against an IdP's published JWKS.

    This is the mode real identity providers use: the IdP signs access
    tokens, publishes its public keys at a JWKS URL, and we verify locally.
    Requires PyJWT (installed with the `mcp` extra).
    """

    _ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

    def __init__(self, jwks_url: str, issuer: Optional[str] = None,
                 audience: Optional[str] = None):
        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError as exc:  # pragma: no cover - env misconfiguration
            raise RuntimeError(
                "AIR_MCP_JWKS_URL is set but PyJWT is not installed; "
                "pip install 'air-blackbox[mcp]'") from exc
        self._jwt = jwt
        # PyJWKClient caches fetched keys, so steady-state verification makes
        # no network calls; an unknown kid triggers one refetch.
        self._jwks = PyJWKClient(jwks_url, cache_keys=True)
        self._issuer = issuer
        self._audience = audience

    def _verify(self, token: str) -> Optional[AccessToken]:
        signing_key = self._jwks.get_signing_key_from_jwt(token)
        claims = self._jwt.decode(
            token,
            signing_key.key,
            algorithms=self._ALGORITHMS,
            issuer=self._issuer,
            audience=self._audience,
            options={
                "require": ["exp"],
                "verify_iss": self._issuer is not None,
                "verify_aud": self._audience is not None,
            },
        )
        subject = claims.get("sub") or claims.get("client_id") or "unknown"
        scopes = claims.get("scope", "")
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", subject),
            subject=subject,
            scopes=scopes.split() if isinstance(scopes, str) else list(scopes),
            expires_at=int(claims["exp"]),
        )

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        import anyio
        try:
            # PyJWKClient does blocking I/O on a JWKS cache miss; keep it off
            # the event loop.
            return await anyio.to_thread.run_sync(self._verify, token)
        except Exception:
            # Malformed token, bad signature, expired, wrong iss/aud, JWKS
            # unreachable - all are "not authenticated", never a crash.
            return None


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

    OAuth engages when AIR_MCP_JWKS_URL, AIR_MCP_INTROSPECTION_URL, or
    AIR_MCP_TOKENS is set (in that order of precedence). Unset means the
    server runs open (fine for local Claude Desktop / stdio).
    """
    jwks = os.environ.get("AIR_MCP_JWKS_URL", "")
    introspection = os.environ.get("AIR_MCP_INTROSPECTION_URL", "")
    static = os.environ.get("AIR_MCP_TOKENS", "")
    if not jwks and not introspection and not static:
        return None, None

    if jwks:
        audience = os.environ.get("AIR_MCP_JWT_AUDIENCE") or None
        issuer = os.environ.get("AIR_MCP_JWT_ISSUER") or None
        allow_any_aud = os.environ.get(
            "AIR_MCP_JWT_ALLOW_ANY_AUDIENCE", "").lower() in ("1", "true", "yes")
        if audience is None and not allow_any_aud:
            # Without an audience, any validly-signed token from the IdP is
            # accepted - including a token minted for a DIFFERENT API behind
            # the same IdP tenant (confused-deputy replay). Refuse to run
            # rather than default to that hole: the operator must either pin
            # the audience or explicitly opt into accepting any.
            raise RuntimeError(
                "AIR_MCP_JWKS_URL is set but AIR_MCP_JWT_AUDIENCE is not. "
                "Without an audience, a token issued for another API behind "
                "the same IdP is replayable against this server. Set "
                "AIR_MCP_JWT_AUDIENCE to this server's resource identifier "
                "(e.g. https://mcp.airblackbox.ai), or set "
                "AIR_MCP_JWT_ALLOW_ANY_AUDIENCE=1 to explicitly accept any "
                "audience (not recommended).")
        if audience is None:
            logger.warning(
                "AIR_MCP_JWT_ALLOW_ANY_AUDIENCE is set: accepting tokens for "
                "ANY audience from the IdP. A token minted for another API "
                "behind the same IdP is replayable against this server.")
        if issuer is None:
            logger.warning(
                "AIR_MCP_JWT_ISSUER is not set: the token issuer is not "
                "pinned. Set it to your IdP's issuer URL.")
        verifier = JwtTokenVerifier(jwks, issuer=issuer, audience=audience)
    elif introspection:
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
