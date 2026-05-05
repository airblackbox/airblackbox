# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.12.0] - 2026-04-28

**Added**
- Feedback-to-retrain pipeline: `air-blackbox feedback` and `air-blackbox retrain` commands
- ML-DSA-65 (FIPS 204) quantum-safe signing with Ed25519 and HMAC-SHA256 fallback
- Self-verifying `.air-evidence` bundles with embedded `verify.py`
- AES-GCM encrypted vault storage (data encrypted at rest)
- Replay-and-diff for incident reconstruction with structured diff output
- Colorado SB 24-205 added to standards crosswalk

**Changed**
- Check count increased from 48 to 51 (3 new Colorado SB 24-205 checks)
- Version standardized to 1.12.0 across all files, CLI, site, and PyPI

**Fixed**
- CLI version reporting (was stuck at 1.8.0)
- CONTRIBUTING.md version reference
- Site check count consistency (48 to 51 everywhere)

## [1.10.0] - 2026-04-14

**Added**
- A2A Transaction Layer for signed agent-to-agent compliance auditing
- Gate policy enforcement engine (air-gate Go reverse proxy)
- Trust layers for LangChain, CrewAI, OpenAI Agents SDK, Google ADK, AutoGen, Haystack
- Unified `air-trust` package consolidating all 7 framework trust layers
- HMAC-SHA256 tamper-evident audit chains with cryptographic verification
- Compliance action for GitHub CI/CD (`airblackbox/compliance-action@v1`)

**Changed**
- Check count increased from 39 to 48
- Consolidated individual framework trust repos into single `air-trust` package

## [1.8.0] - 2026-04-01

**Added**
- Initial public release on PyPI (`pip install air-blackbox`)
- EU AI Act compliance scanner covering Articles 9, 10, 11, 12, 14, 15
- CLI commands: `comply`, `discover`, `replay`, `export`
- GDPR scanning (8 automated checks)
- Bias detection (6 checks)
- Prompt injection detection (20 weighted patterns)
- PDF gap analysis reports
- Pre-commit hook configurations
- MCP server for Claude Desktop and Cursor integration

**Fixed**
- Standards crosswalk dict serialization
- Evidence bundle hash consistency

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
