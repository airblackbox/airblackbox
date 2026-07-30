# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

**Security**
- MCP tenant isolation: the authenticated-subject → tenant-directory mapping is now injective (readable prefix + SHA-256 of the full subject). The previous fold-and-truncate mapping could collide two different subjects onto one tenant (e.g. `alice@corp.com` ≡ `alice_corp_com`, or any two subjects sharing a 64-char prefix), and could route an authenticated subject into the shared `_local` root or the `public-demo` chain. Fixes #56.
- MCP JWT auth now **refuses to start** in JWKS mode unless `AIR_MCP_JWT_AUDIENCE` is set (or `AIR_MCP_JWT_ALLOW_ANY_AUDIENCE=1` is explicitly set). Previously, a JWKS-only config accepted any validly-signed token from the IdP, including one minted for a different API behind the same tenant (confused-deputy replay). Static tokens without an explicit subject now derive it from a hash of the full token instead of a 12-char prefix (prefix-sharing tokens no longer collapse onto one tenant), and malformed empty-token entries are skipped. Part of #59.

**Added**
- Add static dependency discovery for AI-BOM output from requirements.txt, pyproject.toml, package.json, and package-lock.json.
- Add configurable AI-library dependency classification.
- Add CycloneDX 1.6 and SPDX 2.3 JSON output for `air-blackbox discover`.

**Changed**
- `air-blackbox discover --init-registry` now writes `approved-models.json`; `--approved` continues to accept JSON and existing YAML registries.
- MCP OAuth: JWT/JWKS verification mode (`AIR_MCP_JWKS_URL`, `AIR_MCP_JWT_ISSUER`, `AIR_MCP_JWT_AUDIENCE`) — validates IdP-signed tokens locally against published JWKS (WorkOS AuthKit, Auth0, Okta, Keycloak); `pyjwt` added to the `mcp` extra
- Deploy walkthrough for turning on authentication with a DCR-capable IdP so claude.ai custom connectors can log real users in

**Fixed**
- MCP tenant resolution now fails closed: with auth enabled, a request without an authenticated subject is denied instead of silently recorded into the shared `_local` chain
- Auto-export logs a warning when tenant discovery or a tenant's export state is unreadable (previously silent)

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
