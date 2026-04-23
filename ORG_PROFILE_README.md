# AIR Blackbox

**The flight recorder for autonomous AI agents. Record, replay, enforce, audit, with post-quantum signed evidence.**

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![Downloads](https://img.shields.io/pypi/dm/air-blackbox?label=PyPI%20installs)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/airblackbox/airblackbox/blob/main/LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%209%E2%80%9315%20Ready-green)](https://airblackbox.ai)
[![Post-Quantum](https://img.shields.io/badge/signing-ML--DSA--65%20(FIPS%20204)-purple)](https://csrc.nist.gov/pubs/fips/204/final)

One proxy swap. Complete coverage. Runs locally.

```bash
pip install air-blackbox
air-blackbox comply --scan . -v
```

51+ compliance checks across EU AI Act Articles 9, 10, 11, 12, 13, 14, and 15. Maps to ISO 42001, NIST AI RMF, and Colorado SB 24-205. ML-DSA-65 post-quantum signed, HMAC-SHA256 tamper-evident audit chains. Self-verifying evidence bundles. Trust layers for 7 frameworks.

## The Ecosystem

| Package | What it does |
|---|---|
| **[air-blackbox](https://github.com/airblackbox/airblackbox)** | EU AI Act scanner, 51+ checks, ML-DSA-65 signed evidence bundles |
| [air-trust](https://github.com/airblackbox/air-trust) | Cryptographic primitives and trust layer wrappers for 7 frameworks |
| [air-gate](https://github.com/airblackbox/air-gate) | Pre-execution human-in-the-loop gating with Slack approvals |
| [air-controls](https://github.com/airblackbox/air-controls) | Live agent visibility, timelines, cost tracking, kill switch |
| [air-platform](https://github.com/airblackbox/air-platform) | Docker Compose full stack in one command |
| [air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp) | MCP server for Claude Desktop, Cursor, Claude Code |
| [air-controls-mcp](https://github.com/airblackbox/air-controls-mcp) | MCP server for runtime agent visibility |
| [air-blackbox-plugin](https://github.com/airblackbox/air-blackbox-plugin) | Claude Code plugin (slash commands for the scanner) |
| [compliance-action](https://github.com/airblackbox/compliance-action) | GitHub Action for compliance checks on every PR |

Plus 3 OTel processors ([otel-prompt-vault](https://github.com/airblackbox/otel-prompt-vault), [otel-collector-genai](https://github.com/airblackbox/otel-collector-genai), [otel-semantic-normalizer](https://github.com/airblackbox/otel-semantic-normalizer)) for redaction, cost metrics, and schema normalization.

## Why Post-Quantum

Every other AI audit trail signs with HMAC or RSA. Both will be breakable by quantum computers within the retention window of records being generated right now. AIR Blackbox signs every record with ML-DSA-65 (FIPS 204), NIST's standardized post-quantum signature scheme. Keys generated locally, never leave your machine.

## Framework Support

Trust layers for LangChain, CrewAI, OpenAI Agents SDK, Anthropic Claude Agent SDK, Google ADK, AutoGen, and Haystack. Same audit chain, native integration.

## Quickstart

```bash
pip install air-blackbox

# Gap analysis
air-blackbox comply --scan . -v

# Find undeclared model calls
air-blackbox discover

# Generate signed evidence package
air-blackbox export
```

Full stack (Gateway + Episode Store + Policy Engine + observability):

```bash
git clone https://github.com/airblackbox/air-platform.git
cd air-platform && make up    # running in ~8 seconds
```

## Links

- [airblackbox.ai](https://airblackbox.ai) -- website and docs
- [airblackbox.ai/console](https://airblackbox.ai/console) -- web UI (coming June 2026)
- [airblackbox.ai/demo](https://airblackbox.ai/demo) -- interactive demos
- [PyPI](https://pypi.org/project/air-blackbox/) -- 14,000+ downloads

Apache 2.0. EU AI Act high-risk deadline: August 2, 2026.
