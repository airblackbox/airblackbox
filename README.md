# AIR Blackbox

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![Downloads](https://img.shields.io/pypi/dm/air-blackbox?label=PyPI%20installs)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%20Ready-green)](https://airblackbox.ai)
[![Status](https://img.shields.io/badge/status-production-brightgreen)](https://github.com/airblackbox/airblackbox)

**The flight recorder for autonomous AI agents. Record, replay, enforce, audit.**

One proxy swap. Complete coverage. Runs locally.

```python
# Before
client = OpenAI(base_url="https://api.openai.com/v1")

# After — everything else in your code stays identical
client = OpenAI(
    base_url="http://localhost:8080/v1",
    default_headers={"X-Gateway-Key": "your-key"}
)
```

Every LLM call now generates a signed, tamper-evident, replayable audit record. No SDK changes. No refactoring. No performance impact.

## What You Get

**Audit chain** — every call produces an HMAC-SHA256 chained `.air.json` record, written asynchronously. Tamper with one record and every record after it breaks.

**Quantum-safe signing** — the chain is signed with ML-DSA-65 (FIPS 204 / Dilithium3). Keys are generated locally and never leave your machine. Post-quantum secure today.

**Evidence bundle** — one command packages the audit chain, scan results, and ML-DSA-65 signatures into a self-verifying `.air-evidence` ZIP. An auditor runs `python verify.py` and gets PASS/FAIL in two seconds. No pip install needed on their end.

**PII and injection scanning** — 20 weighted patterns across 5 attack categories detected before the prompt reaches the model. Configurable sensitivity. Auto-blocking.

**EU AI Act gap analysis** — 51+ checks across Articles 9, 10, 11, 12, 13, 14, 15. Maps to ISO 42001, NIST AI RMF, and Colorado SB 24-205. One scan, four frameworks, one report.

**Replay** — load any past episode from the audit chain, verify the HMAC signature, and replay every step with timestamps. Incident reconstruction without guesswork.

**Framework trust layers** — drop-in wrappers for LangChain, CrewAI, OpenAI Agents SDK, Anthropic, AutoGen, Google ADK, and Haystack. Same audit chain, native integration.

## Quickstart

```bash
pip install air-blackbox

# Run your first gap analysis — works on any Python AI project
air-blackbox comply --scan . -v

# Find undeclared model calls hiding in helpers and utilities
air-blackbox discover

# Replay any recorded episode
air-blackbox replay

# Generate a signed evidence package for audit or regulator review
air-blackbox export
```

Full stack (Gateway + Episode Store + Policy Engine + observability):

```bash
git clone https://github.com/airblackbox/air-platform.git
cd air-platform
cp .env.example .env      # add OPENAI_API_KEY
make up                   # running in ~8 seconds
```

* Traces: `localhost:16686` (Jaeger)
* Metrics: `localhost:9091` (Prometheus)
* Episodes: `localhost:8081` (Episode Store API)

## How It Fits Your Stack

```
Your Agent
    |
    v
AIR Gateway          <- swap base_url here
    |
    |-- PII + injection scan      (before prompt reaches model)
    |-- HMAC audit record         (async, zero latency impact)
    |-- ML-DSA-65 signing         (keys never leave your machine)
    |
    v
LLM Provider         <- OpenAI / Anthropic / Azure / local
    |
    v
AIR Record           <- tamper-evident .air.json
    |
    v
Evidence Bundle      <- self-verifying .air-evidence ZIP
```

Works with any OpenAI-compatible API. Same format, same integration, regardless of provider.

## Why Not Just Log Everything?

You probably already have logging. The problems logging doesn't solve:

**Tamper-evidence** — anyone with write access to your log store can alter a record. HMAC chains make alteration detectable. ML-DSA-65 signatures prove who signed and when.

**Prompt reconstruction** — most logging captures responses but not the full prompt context, tool calls, and intermediate reasoning. AIR records the complete episode.

**Compliance structure** — EU AI Act Article 12 requires tamper-evident logs with specific retention and audit access guarantees. Raw logs don't satisfy that. Evidence bundles do.

**Secrets leaking into traces** — every team that builds their own logging eventually discovers credentials in their observability backend. AIR strips and vault-encrypts API keys before writing any record.

## Ecosystem

`air-blackbox` is the scanner. `air-trust` is the cryptographic proof layer underneath.

```
Your AI Agent
       |
       |-- air-blackbox scan     ->  finds compliance gaps
       |-- air-trust             ->  proves what happened (HMAC + Ed25519)
       |-- air-gate              ->  human approval before dangerous tool calls
       +-- air-blackbox-mcp      ->  all of the above inside Claude Desktop / Cursor
```

| Package | What It Does |
|---------|-------------|
| [air-trust](https://github.com/airblackbox/air-trust) | Tamper-evident audit chain + Ed25519 signed handoffs |
| [air-gate](https://github.com/airblackbox/air-gate) | Human-in-the-loop tool gating (Article 14) |
| [air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp) | MCP server for Claude Desktop, Cursor, Claude Code |
| [air-platform](https://github.com/airblackbox/air-platform) | Docker Compose — full stack in one command |
| [compliance-action](https://github.com/airblackbox/compliance-action) | GitHub Action — checks on every pull request |

## Validated By

* **Julian Risch** (deepset) — public validation on LinkedIn and GitHub issue #10810
* **Piero Molino** (Ludwig maintainer) — merged EU AI Act compliance changes driven by AIR scan results
* **arXiv AEGIS** (March 2026) — independent researchers published the identical interception-layer architecture for AI agent governance
* **McKinsey State of AI Trust 2026** — trust infrastructure named as the critical agentic AI category

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

False positive on a compliance check? Correct it — your correction flows into training data for the fine-tuned scanner model. The scanner gets smarter with every fix your team submits.

Good first issues: labeled `good first issue` — mostly new compliance checks and framework integrations.

## License

Apache-2.0 — [airblackbox.ai](https://airblackbox.ai)

*This is not a certified compliance test. It is a starting point to identify potential gaps.*

---

If this helps you prepare for EU AI Act enforcement, [star the repo](https://github.com/airblackbox/airblackbox) — it helps other teams find it.
