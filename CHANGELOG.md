# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.14.0] - 2026-08-04

First release since 1.13.2. Everything below was already merged to `main` but
had never been published: a `pip install air-blackbox` was still getting a
build from before the security review, with no anchoring, no evidence
verification, and no `air-blackbox-mcp` / `air-evidence` commands. Releases are
now gated by CI on the built artifact actually importing and running, so the
published package cannot drift silently from the repo again.

**Added**
- **Public transparency-log anchoring (M2).** Exports can publish the chain head
  to Rekor, Sigstore's public append-only log (`AIR_REKOR=1`, opt-in). The new
  `audit_public_log` tool re-derives the bounded chain head against *every*
  entry ever logged under the tenant's anchoring key, so an operator who
  rewrites history **and** re-anchors it is still caught by the older entries —
  closing the documented gap in the RFC 3161 anchor alone. Entries carry the
  full payload inline, so any auditor can interpret them from the public log
  with nothing but the anchoring public key (ADR 0002).
- **ML-DSA-65 (FIPS 204) receipts are now usable.** The signer persists and
  reloads its keypair, so a tenant's post-quantum public key survives a restart;
  previously it regenerated on every construction and silently broke receipt
  continuity. The post-quantum path now runs the full suite in CI. Ed25519
  remains the default. Closes #63.
- **A runnable proof harness** (`python bench/proof/prove.py`): executes five
  real attacks against a plain log, a bare hash chain, and AIR side by side and
  prints a scorecard. CI asserts both that AIR delivers every guarantee and that
  the bare hash chain still *misses* the operator rewrite, so the comparison
  cannot quietly become a rigged demo.
- **"Audit Day" demo** (`demo/hiring_audit_day.py`) plus a 90-second recording
  script — the operator-rewrite catch dramatized on a fictional hiring pipeline,
  running real product code.
- **Cryptographic posture document** (`docs/security/cryptographic-posture.md`):
  the primitives in use, what each is exposed to (including quantum), how the
  system replaces one without a rewrite, and what is not yet production-ready.
- Scheduled auto-export: every tenant with new records gets a fresh signed
  evidence bundle on an interval, without anyone remembering to ask.
- Static dependency discovery for AI-BOM output from requirements.txt,
  pyproject.toml, package.json and package-lock.json, with configurable
  AI-library classification and CycloneDX 1.6 / SPDX 2.3 JSON output for
  `air-blackbox discover`.

**Security**
- Receipt authenticity anchoring (remaining #57 items): `verify_receipt()` accepts an `expected_public_key` so it can reject a receipt signed by an untrusted key (without it, it only proves self-consistency — an attacker can embed their own key); the evidence bundle verifier now requires every receipt to be signed by the **same** key that signed the manifest; and `verify_chain()` reports its `key_source`, with docs making clear the colocated `.air-signing-key` is a zero-config convenience, not a trust anchor against a runs-dir writer (pair with `verify_anchor`).
- Gate covenant conditions now fail **closed**. An ordering comparison on a non-numeric value (e.g. `amount <= 1000` with `amount="1,000,000"`), an unparseable guard, and a `forbid` whose guarded field is missing previously all defaulted to *allow*; they now deny (and a `forbid` with an indeterminate guard stays active). `Gate.walk_delegation_chain` no longer infinite-loops on a cyclic parent link, and `Gate.verify()` surfaces `authorized`/`decision` so a valid signature on a *denied* action isn't mistaken for permission. Fixes #58.
- `air-evidence verify` now checks the external RFC 3161 anchor (new check 6): it re-derives the key-free chain head over the bundle's records and verifies it against the timestamp authority's countersignature, so a rewritten — even perfectly re-signed — history is **detected** by the same command a regulator runs. An unanchored bundle is reported honestly as not rewrite-protected instead of a bare "VERIFIED", and the bundle's stamped chain verdict is now gated (a broken-at-export chain fails). Closes the evidence-bundle part of #57. (Remaining #57 items — `verify_chain`/`verify_receipt` accepting an expected key instead of a co-located/embedded one — are tracked separately.)
- MCP tenant isolation: the authenticated-subject → tenant-directory mapping is now injective (readable prefix + SHA-256 of the full subject). The previous fold-and-truncate mapping could collide two different subjects onto one tenant (e.g. `alice@corp.com` ≡ `alice_corp_com`, or any two subjects sharing a 64-char prefix), and could route an authenticated subject into the shared `_local` root or the `public-demo` chain. Fixes #56.
- MCP JWT auth now **refuses to start** in JWKS mode unless `AIR_MCP_JWT_AUDIENCE` is set (or `AIR_MCP_JWT_ALLOW_ANY_AUDIENCE=1` is explicitly set). Previously, a JWKS-only config accepted any validly-signed token from the IdP, including one minted for a different API behind the same tenant (confused-deputy replay). Static tokens without an explicit subject now derive it from a hash of the full token instead of a 12-char prefix (prefix-sharing tokens no longer collapse onto one tenant), and malformed empty-token entries are skipped. Part of #59.

**Changed**
- `air-blackbox discover --init-registry` now writes `approved-models.json`; `--approved` continues to accept JSON and existing YAML registries.
- MCP OAuth: JWT/JWKS verification mode (`AIR_MCP_JWKS_URL`, `AIR_MCP_JWT_ISSUER`, `AIR_MCP_JWT_AUDIENCE`) — validates IdP-signed tokens locally against published JWKS (WorkOS AuthKit, Auth0, Okta, Keycloak); `pyjwt` added to the `mcp` extra
- Deploy walkthrough for turning on authentication with a DCR-capable IdP so claude.ai custom connectors can log real users in
- README no longer implies the chain is post-quantum secure today; it states Ed25519 now with an ML-DSA-65 upgrade path, and links the posture document.
- Hosted MCP server monitoring: Fly now runs a health check (none was configured before), `/health` write-probes the runs volume so "ok" means "can record evidence" rather than "process is up" (503 otherwise), and optional Sentry error reporting engages only when `SENTRY_DSN` is set — a no-op for self-hosters. New `monitor` extra.
- `mcp` extra pinned to `mcp>=1.0,<2`: mcp 2.0 removed `mcp.server.fastmcp`, which the server imports.

**Fixed**
- `air-blackbox-comply-strict` was broken in every install: the console script pointed at `air_blackbox.precommit:main`, which was never defined, so running it raised `ImportError` immediately. The entry point now exists (and supports `--help`); the hook itself was fine, only its entry point was missing. Releases now resolve every declared console script, not just import its module, so this class of break cannot ship again.
- MCP tenant resolution now fails closed: with auth enabled, a request without an authenticated subject is denied instead of silently recorded into the shared `_local` chain
- Auto-export logs a warning when tenant discovery or a tenant's export state is unreadable (previously silent)
- MCP JWT rejections now log the reason (never the token). A fleet of 401s caused by an audience or issuer mismatch was previously invisible in logs, making a misconfigured deployment undiagnosable.
- `AIR_MCP_RESOURCE_URL` is set explicitly so OAuth discovery reports this server as the protected resource rather than inheriting the IdP's URL, which broke resource-indicator matching for MCP clients.

## [1.6.1] - 2026-03-28

**Fixed**
- Fix standards_map.py STANDARDS_CROSSWALK dict closing prematurely (blocked GDPR/bias imports)
- Fix evidence_bundle.py hash serialization mismatch between manifest and ZIP (sort_keys consistency)

## [1.6.0] - 2026-03-27

**Added**
- Prompt injection detection: 20 weighted patterns across 5 categories
- GDPR scanner: 8 automated checks (consent, minimization, erasure, retention, cross-border, DPIA, processing records, breach notification)
- Bias/fairness scanner: 6 checks (fairness metrics, bias detection, protected attributes, dataset balance, model card, output monitoring)
- ISO 42001 + NIST AI RMF standards crosswalk mapping (8 categories)
- A2A (Agent-to-Agent) compliance protocol with compliance cards, peer verification, signed handshakes
- Evidence bundle exporter: signed ZIP with SHA-256 manifest for auditors
- Feedback loop MVP: user corrections flow into training data for fine-tuned model
- Pre-commit hooks: 4 configurations (basic, strict, GDPR, full)
- Audit chain specification v1.0 (RFC-style document)
- Training data phase 35: injection and GDPR patterns (15 examples)
## [1.5.0] - 2026-03-26

**Added**
- Haystack trust layer
- Claude Agent SDK trust layer
- MCP server registry listing (air-blackbox-mcp v0.1.6)
- Enhanced CLI with verbose compliance output

## [1.4.0] - 2026-03-20

**Added**
- Google ADK trust layer
- Enterprise air-gapped VPS deployment with fine-tuned model
- OTel tracing + dual pipeline
- Deep scan with fine-tuned compliance model

## [1.3.0] - 2026-03-15

**Added**
- MCP server for Claude Desktop and Cursor
- AI-BOM generation (CycloneDX 1.6)
- Shadow AI detection with approved model registry

## [1.2.0] - 2026-03-10

**Added**
- Compliance engine with 20+ checks across 6 EU AI Act articles
- PDF gap analysis reports
- Replay engine with HMAC verification

## [1.1.0] - 2026-03-05

**Added**
- Trust layer framework (LangChain, CrewAI, AutoGen, OpenAI)
- PII detection in prompts
- Non-blocking callback architecture

## [1.0.0] - 2026-03-01

**Added**
- Python SDK (pip install air-blackbox)
- CLI commands: comply, discover, replay, export
- HMAC-SHA256 audit chain
- Gateway client integration

## [0.1.0] - 2026-02-22

**Added**
- Initial release of AIR Blackbox Gateway
- OpenAI-compatible reverse proxy with full request/response capture
- HMAC-SHA256 tamper-evident audit chain
- OpenTelemetry trace emission
- Prompt vault integration with MinIO
- Docker Compose stack
- GitHub Container Registry publishing via CI
