# AIR Blackbox

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![Downloads](https://img.shields.io/pypi/dm/air-blackbox?label=PyPI%20installs)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%209%E2%80%9315%20Ready-green)](https://airblackbox.ai)
[![Post-Quantum](https://img.shields.io/badge/signing-ML--DSA--65%20(FIPS%20204)-purple)](https://csrc.nist.gov/pubs/fips/204/final)
[![Status](https://img.shields.io/badge/status-production-brightgreen)](https://github.com/airblackbox/airblackbox)

**The flight recorder for autonomous AI agents. Record, replay, enforce, audit — with post-quantum signed evidence.**

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

## Why post-quantum today

Every other "AI audit trail" on the market signs with HMAC or RSA. Both will be breakable by quantum computers within the retention window of records you're generating right now. EU AI Act Article 12 requires you to keep these logs for at least six months, often longer. Regulators will accept signatures that are breakable before the retention period ends at their peril — you shouldn't.

AIR Blackbox signs every record with **ML-DSA-65 (FIPS 204 / Dilithium3)**, NIST's standardized post-quantum signature scheme. Keys are generated locally and never leave your machine. The evidence you produce today will still be verifiable — and un-forgeable — in 2035.

## What you get

**Post-quantum audit chain** — every call produces an ML-DSA-65 signed, HMAC-SHA256 chained `.air.json` record, written asynchronously. Tamper with one record and every record after it breaks. FIPS 204 compliant, quantum-safe, locally signed.

**Evidence bundle** — one command packages the audit chain, scan results, and ML-DSA-65 signatures into a self-verifying `.air-evidence` ZIP. An auditor runs `python verify.py` and gets PASS/FAIL in two seconds. No pip install needed on their end. No internet connection needed. No hosted service required.

**EU AI Act gap analysis** — 51+ checks across Articles 9, 10, 11, 12, 13, 14, and 15. Maps to ISO 42001, NIST AI RMF, and Colorado SB 24-205. One scan, four frameworks, one report.

**PII and injection scanning** — 20 weighted patterns across 5 attack categories detected before the prompt reaches the model. Configurable sensitivity. Auto-blocking.

**Replay** — load any past episode from the audit chain, verify the signature, and replay every step with timestamps. Incident reconstruction without guesswork.

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

**Claude Code plugin** — fastest path for developers who live in their editor:

```
/plugin marketplace add airblackbox/air-blackbox-plugin
/plugin install air-blackbox@air-blackbox
```

**Full stack** (Gateway + Episode Store + Policy Engine + observability):

```bash
git clone https://github.com/airblackbox/air-platform.git
cd air-platform
cp .env.example .env      # add OPENAI_API_KEY
make up                   # running in ~8 seconds
```

- Traces: `localhost:16686` (Jaeger)
- Metrics: `localhost:9091` (Prometheus)
- Episodes: `localhost:8081` (Episode Store API)

## How it fits your stack

```
Your Agent
    │
    ▼
AIR Gateway                    ← swap base_url here
    │
    ├── PII + injection scan   (before prompt reaches model)
    ├── HMAC audit record      (async, zero latency impact)
    └── ML-DSA-65 signing      (keys never leave your machine)
    │
    ▼
LLM Provider                   ← OpenAI / Anthropic / Azure / local
    │
    ▼
AIR Record                     ← tamper-evident .air.json
    │
    ▼
Evidence Bundle                ← self-verifying .air-evidence ZIP
```

Works with any OpenAI-compatible API. Same format, same integration, regardless of provider.

## Why not just log everything?

You probably already have logging. The problems logging doesn't solve:

**Tamper-evidence** — anyone with write access to your log store can alter a record. HMAC chains make alteration detectable. ML-DSA-65 signatures prove who signed and when, and survive the arrival of cryptographically relevant quantum computers.

**Prompt reconstruction** — most logging captures responses but not the full prompt context, tool calls, and intermediate reasoning. AIR records the complete episode.

**Compliance structure** — EU AI Act Article 12 requires tamper-evident logs with specific retention and audit access guarantees. Raw logs don't satisfy that. Evidence bundles do.

**Secrets leaking into traces** — every team that builds their own logging eventually discovers credentials in their observability backend. AIR strips and vault-encrypts API keys before writing any record.

## Gate — pre-execution policy enforcement

Gate is a bilateral receipt system that governs what your AI agents are **allowed** to do and proves what they **actually did**. Every action goes through a covenant (policy), produces an Ed25519-signed receipt, and chains into a tamper-evident audit trail.

### Covenants — declare what's allowed

Write your agent's policy in YAML before it runs:

```yaml
# covenant.yaml
agent: loan-processor
version: "1.0"
rules:
  - permit: read_credit_score
  - permit: approve_loan
    when: "amount <= 50000"
  - require_approval: approve_loan
    when: "amount > 50000"
  - forbid: delete_records
  - forbid: modify_credit_score
```

Precedence: `forbid` > `require_approval` > `permit` > default deny.

### Bilateral receipts — two-phase proof

Every action produces a receipt with two cryptographic phases:

```python
from air_blackbox.gate import Gate, Covenant

covenant = Covenant.from_yaml("covenant.yaml")
gate = Gate(covenant=covenant)

# Phase 1: Authorization — checks covenant, signs decision
receipt = gate.authorize(
    agent_id="loan-processor",
    action_name="approve_loan",
    payload={"applicant": "jane@example.com", "amount": 75000},
    context={"amount": 75000},
)

if receipt.authorized:
    result = process_loan(...)

    # Phase 2: Seal — binds result to the authorization
    gate.seal(receipt, result=result, status="success")

# Third party can verify without the signing key
print(gate.verify(receipt))
# {'authorization_valid': True, 'seal_valid': True, 'overall': True}
```

**What the receipt proves:**

- The covenant hash locks which rules were active at decision time
- Ed25519 signatures (HMAC-SHA256 fallback) provide non-repudiation
- The seal covers the authorization signature, binding the full lifecycle
- Payloads are SHA-256 hashed — raw data never stored in the receipt

### Delegation chains — multi-agent traceability

When one agent delegates to another, the receipts chain together:

```python
# Parent agent authorizes its action
parent_receipt = gate.authorize("orchestrator", "delegate_task", ...)

# Child agent links back to the parent
child_receipt = gate.authorize(
    "notifier-agent", "send_confirmation",
    parent_receipt=parent_receipt,
)

# Walk the full chain
chain = gate.walk_delegation_chain(child_receipt)
# [orchestrator receipt, notifier receipt]
```

### Install

```bash
pip install air-blackbox[gate]   # includes Ed25519 via cryptography
```

### Gate vs air-gate

`Gate` (in `air-blackbox`) is the **policy primitive** — covenants, bilateral receipts, delegation chains. Use it when you need programmatic, deterministic authorization with cryptographic receipts.

[`air-gate`](https://github.com/airblackbox/air-gate) is the **human-in-the-loop layer** built on top — Slack approvals, PII auto-redaction across 25+ categories (HIPAA, PCI-DSS, GDPR), risk-tiered policies, and a FastAPI server for team approval workflows. Use it when a covenant rule says `require_approval` and a human needs to actually see and decide.

The two compose. Gate handles the cryptographic receipt. air-gate handles the human decision that produces it.

## Ecosystem

`air-blackbox` is the scanner and core runtime. The rest of the stack extends it.

```
Your AI Agent
       │
       ├── air-blackbox scan     →  finds compliance gaps  (Articles 9–15)
       ├── air-blackbox gate     →  pre-execution covenants + bilateral receipts
       ├── air-gate              →  human-in-the-loop approvals with PII redaction
       ├── air-trust             →  cryptographic primitives  (HMAC + Ed25519 + ML-DSA-65)
       └── air-blackbox-mcp      →  all of the above inside Claude Desktop / Cursor
```

| Package | What it does |
|---|---|
| **[air-blackbox](https://github.com/airblackbox/airblackbox)** | Scanner, Gate, CLI — the core runtime (this repo) |
| [air-trust](https://github.com/airblackbox/air-trust) | Tamper-evident audit chain + Ed25519 + ML-DSA-65 primitives |
| [air-gate](https://github.com/airblackbox/air-gate) | Human-in-the-loop approvals with PII auto-redaction |
| [air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp) | MCP server for Claude Desktop, Cursor, Claude Code |
| [air-blackbox-plugin](https://github.com/airblackbox/air-blackbox-plugin) | Claude Code plugin |
| [air-platform](https://github.com/airblackbox/air-platform) | Docker Compose — full stack in one command |
| [compliance-action](https://github.com/airblackbox/compliance-action) | GitHub Action — checks on every pull request |

## Validated by

- **Julian Risch** (deepset, Haystack maintainer) — public validation on LinkedIn and [GitHub issue #10810](https://github.com/deepset-ai/haystack/issues/10810); response in under 38 minutes
- **Piero Molino** (Ludwig maintainer) — merged EU AI Act compliance changes driven by AIR scan results within hours of the issue being opened
- **arXiv AEGIS** (March 2026) — independent researchers published the identical interception-layer architecture for AI agent governance
- **McKinsey State of AI Trust 2026** — trust infrastructure named as the critical agentic AI category
- Listed in [EthicalML/awesome-artificial-intelligence-regulation](https://github.com/EthicalML/awesome-artificial-intelligence-regulation) and [GenAI-Gurus/awesome-eu-ai-act](https://github.com/GenAI-Gurus/awesome-eu-ai-act)

## How we compare

| | AIR Blackbox | Document generators (ArcKit, etc.) | Hosted scanners (ark-forge, etc.) |
|---|---|---|---|
| Scans actual code | ✅ | ❌ (generates docs from prompts) | ✅ |
| Pre-execution policy + bilateral receipts | ✅ **Gate** | ❌ | ❌ |
| Post-quantum signatures (ML-DSA-65) | ✅ FIPS 204 | ❌ | ❌ |
| HMAC audit chains | ✅ Local, self-verifiable | ❌ | Partial (usually hosted) |
| Everything runs locally | ✅ | ✅ | ❌ |
| MCP server + Claude Code plugin | ✅ | Partial | ❌ |
| Pricing | Free, Apache 2.0 | Free (docs only) | Free tier + paid signing |

**Use a document generator** for RFPs, business cases, and governance board paperwork.
**Use AIR Blackbox** to prove to an auditor what your AI system actually did — and to guarantee the proof still verifies after quantum computers arrive.

## Philosophy

**AIR is a witness, not a gatekeeper — until you tell it to be.**

- **Non-blocking** — recording or gating failures never break production flow
- **Lossy-safe** — dropped audit records are acceptable; dropped user requests are not
- **Self-degrading** — if the collector is down, spans drop silently; warnings logged, never errors returned

You cannot detect what you cannot see. You cannot prevent what you cannot detect. You cannot trust what you cannot prove. AIR Blackbox is the layer that makes proof possible — today and after quantum.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

False positive on a compliance check? Correct it — your correction flows into training data for the fine-tuned scanner model. The scanner gets smarter with every fix your team submits.

Good first issues: labeled `good first issue` — mostly new compliance checks and framework integrations.

## License

Apache-2.0 — [airblackbox.ai](https://airblackbox.ai)

*This is not a certified compliance test. It is a starting point to identify potential gaps.*

---

If this helps you prepare for EU AI Act enforcement, [star the repo](https://github.com/airblackbox/airblackbox) — it helps other teams find it.
