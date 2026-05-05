# AIR Blackbox

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![Downloads](https://img.shields.io/pypi/dm/air-blackbox?label=PyPI%20installs)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%209%E2%80%9315%20Ready-green)](https://airblackbox.ai)
[![Post-Quantum](https://img.shields.io/badge/signing-ML--DSA--65%20(FIPS%20204)-purple)](https://csrc.nist.gov/pubs/fips/204/final)
[![Status](https://img.shields.io/badge/status-production-brightgreen)](https://github.com/airblackbox/airblackbox)

**The flight recorder for autonomous AI agents. Record, replay, enforce, audit, with post-quantum signed evidence.**

One proxy swap. Complete coverage. Runs locally.

```python
# Before
client = OpenAI(base_url="https://api.openai.com/v1")

# After, everything else in your code stays identical
client = OpenAI(
    base_url="http://localhost:8080/v1",
    default_headers={"X-Gateway-Key": "your-key"}
)
```

Every LLM call now generates a signed, tamper-evident, replayable audit record. No SDK changes. No refactoring. No performance impact.

## Why post-quantum today

Every other AI audit trail on the market signs with HMAC or RSA. Both will be breakable by quantum computers within the retention window of records you're generating right now. EU AI Act Article 12 requires you to keep these logs for at least six months, often longer. Regulators will accept signatures that are breakable before the retention period ends at their peril. You shouldn't.

AIR Blackbox signs every record with **ML-DSA-65 (FIPS 204 / Dilithium3)**, NIST's standardized post-quantum signature scheme. Keys are generated locally and never leave your machine. The evidence you produce today will still be verifiable, and un-forgeable, in 2035.

## What you get

**Post-quantum audit chain**, every call produces an ML-DSA-65 signed, HMAC-SHA256 chained `.air.json` record, written asynchronously. Tamper with one record and every record after it breaks. FIPS 204 compliant, quantum-safe, locally signed.

**Evidence bundle**, one command packages the audit chain, scan results, and ML-DSA-65 signatures into a self-verifying `.air-evidence` ZIP. An auditor runs `python verify.py` and gets PASS/FAIL in two seconds. No pip install needed on their end. No internet connection needed. No hosted service required.

**EU AI Act gap analysis**, 51+ checks across Articles 9, 10, 11, 12, 13, 14, and 15. Maps to ISO 42001, NIST AI RMF, and Colorado SB 24-205. One scan, four frameworks, one report.

**PII and injection scanning**, 20 weighted patterns across 5 attack categories detected before the prompt reaches the model. Configurable sensitivity. Auto-blocking.

**Replay**, load any past episode from the audit chain, verify the signature, and replay every step with timestamps. Incident reconstruction without guesswork.

**Framework trust layers**, drop-in wrappers for LangChain, CrewAI, OpenAI Agents SDK, Anthropic, AutoGen, Google ADK, and Haystack. Same audit chain, native integration.

## Quickstart

```bash
pip install air-blackbox

# Run your first gap analysis, works on any Python AI project
air-blackbox comply --scan . -v

# Find undeclared model calls hiding in helpers and utilities
air-blackbox discover

# Replay any recorded episode
air-blackbox replay

# Generate a signed evidence package for audit or regulator review
air-blackbox export
```

**Claude Code plugin**, fastest path for developers who live in their editor:

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

**Tamper-evidence**, anyone with write access to your log store can alter a record. HMAC chains make alteration detectable. ML-DSA-65 signatures prove who signed and when, and survive the arrival of cryptographically relevant quantum computers.

**Prompt reconstruction**, most logging captures responses but not the full prompt context, tool calls, and intermediate reasoning. AIR records the complete episode.

**Compliance structure**, EU AI Act Article 12 requires tamper-evident logs with specific retention and audit access guarantees. Raw logs don't satisfy that. Evidence bundles do.

**Secrets leaking into traces**, every team that builds their own logging eventually discovers credentials in their observability backend. AIR strips and vault-encrypts API keys before writing any record.

## Runtime control, air-gate and air-controls

`air-blackbox` scans your code before you ship. Two sibling packages cover what your agents do *after* they're live.

### air-gate, human-in-the-loop gating

Before an agent sends that email, deletes that file, or executes that SQL, `air-gate` pauses, checks a policy, optionally asks a human via Slack, and signs the decision to a tamper-evident audit chain. EU AI Act Article 14 (Human Oversight) in twelve lines of Python.

```bash
pip install air-gate
```

```python
from air_gate import GateClient

gate = GateClient()  # local mode, zero config

result = gate.check(
    agent_id="support-bot",
    action_type="email",
    action="send_email",
    payload={"to": "customer@example.com", "body": "..."},
)

if result["decision"] == "auto_allowed":
    send_the_email()
elif result["decision"] == "blocked":
    log.warning("Blocked by policy:", result["reason"])
# MEDIUM/HIGH-risk actions pause until a human approves in Slack

# Verify the full audit chain anytime
assert gate.verify()
```

Highlights:

- **Risk-tiered YAML policy**, `auto_allow`, `require_approval`, `block`, per-action-type
- **Slack approval flow**, human approves from their phone, callback URL fires back to the agent
- **PII auto-redaction**, 25+ categories across five verticals (universal, finance/PCI-DSS, healthcare/HIPAA, legal, recruiting/EEOC)
- **LangChain and OpenAI function-tool wrappers**, one-line integration
- **Library or server mode**, `GateClient()` for zero config, FastAPI + Slack bot for team workflows

Full repo: [airblackbox/air-gate](https://github.com/airblackbox/air-gate)

### air-controls, runtime visibility

Your agents are making thousands of decisions per day. `air-controls` is the dashboard that makes them legible. Action timeline, cost per call, risk scoring, kill switch. Same HMAC audit chain as `air-blackbox`.

```bash
pip install air-controls
```

```python
# LangChain
from air_controls import ControlsCallback
cb = ControlsCallback(agent_name="sales-bot")
chain.invoke({"input": "..."}, config={"callbacks": [cb]})

# CrewAI
from air_controls import CrewMonitor
mon = CrewMonitor(agent_name="research-crew")
mon.run(crew)

# Any OpenAI / Anthropic agent
from air_controls import monitor

@monitor(agent_name="my-bot")
def process_customer(query):
    return openai.chat.completions.create(...)
```

```bash
air-controls status                 # live dashboard of all agents
air-controls events sales-bot       # event timeline for one agent
air-controls pause sales-bot        # kill switch
air-controls verify                 # verify audit chain integrity
```

Local-first. SQLite backing store. No cloud. No phone-home.

Full repo: [airblackbox/air-controls](https://github.com/airblackbox/air-controls), with an MCP server at [air-controls-mcp](https://github.com/airblackbox/air-controls-mcp) for Cursor, Claude Code, and Windsurf.

## How the pieces compose

```
   Build time                                 Runtime
───────────────────                   ────────────────────────

air-blackbox  ──────────┐       ┌──── air-controls
(scan code,             │       │     (monitor what agents do,
 find gaps,             │       │      action timeline, cost,
 export evidence)       │       │      kill switch)
                        │       │            │
                        │       │            │ escalates to
                        │       │            ▼
                        │       │      air-gate
                        │       │      (pause dangerous actions,
                        │       │       human approval, Slack)
                        │       │
                        ▼       ▼
                  Shared HMAC-SHA256 audit chain
                  Shared ML-DSA-65 post-quantum signatures
                  Shared .air-evidence bundle format

All four deployable as one Docker Compose stack:
    air-platform  (make up, 8 seconds to full stack)
```

## The full ecosystem

`air-blackbox` is the scanner and the entry point. Everything else extends it.

| Package | Stage | What it does |
|---|---|---|
| **[air-blackbox](https://github.com/airblackbox/airblackbox)** | Build-time | EU AI Act scanner, 51+ checks, ML-DSA-65 signed evidence bundles (this repo) |
| [air-trust](https://github.com/airblackbox/air-trust) | Build + runtime | Cryptographic primitives and trust layer wrappers (see repo) |
| [air-controls](https://github.com/airblackbox/air-controls) | Runtime | Live agent visibility, timelines, costs, kill switch |
| [air-gate](https://github.com/airblackbox/air-gate) | Runtime | Pre-execution human-in-the-loop gating with Slack approvals |
| [air-platform](https://github.com/airblackbox/air-platform) | Deployment | Docker Compose full stack in one command |
| [air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp) | IDE | MCP server for Claude Desktop, Cursor, Claude Code |
| [air-controls-mcp](https://github.com/airblackbox/air-controls-mcp) | IDE | MCP server for runtime agent visibility |
| [air-blackbox-plugin](https://github.com/airblackbox/air-blackbox-plugin) | IDE | Claude Code plugin (slash commands for the scanner) |
| [compliance-action](https://github.com/airblackbox/compliance-action) | CI | GitHub Action, run compliance checks on every PR |
| [otel-prompt-vault](https://github.com/airblackbox/otel-prompt-vault) | Infra | OTel processor: offloads sensitive content to external storage |
| [otel-collector-genai](https://github.com/airblackbox/otel-collector-genai) | Infra | OTel processor: redaction, cost/token metrics, loop detection |
| [otel-semantic-normalizer](https://github.com/airblackbox/otel-semantic-normalizer) | Infra | OTel processor: normalizes LLM attributes to `gen_ai.*` schema |

Install any one. They compose when you want them to.

## Validated by

- **Julian Risch** (deepset, Haystack maintainer), public validation on LinkedIn and [GitHub issue #10810](https://github.com/deepset-ai/haystack/issues/10810); response in under 38 minutes
- **Piero Molino** (Ludwig maintainer), merged EU AI Act compliance changes driven by AIR scan results within hours of the issue being opened
- **arXiv AEGIS** (March 2026), independent researchers published the identical interception-layer architecture for AI agent governance
- **McKinsey State of AI Trust 2026**, trust infrastructure named as the critical agentic AI category
- Listed in [EthicalML/awesome-artificial-intelligence-regulation](https://github.com/EthicalML/awesome-artificial-intelligence-regulation) and [GenAI-Gurus/awesome-eu-ai-act](https://github.com/GenAI-Gurus/awesome-eu-ai-act)

## How we compare

| | AIR Blackbox | Document generators (ArcKit, etc.) | Hosted scanners (ark-forge, etc.) |
|---|---|---|---|
| Scans actual code | ✅ | ❌ (generates docs from prompts) | ✅ |
| Pre-execution gating with receipts | ✅ **air-gate** | ❌ | ❌ |
| Post-quantum signatures (ML-DSA-65) | ✅ FIPS 204 | ❌ | ❌ |
| HMAC audit chains | ✅ Local, self-verifiable | ❌ | Partial (usually hosted) |
| Everything runs locally | ✅ | ✅ | ❌ |
| MCP server + Claude Code plugin | ✅ | Partial | ❌ |
| Pricing | Free, Apache 2.0 | Free (docs only) | Free tier + paid signing |

**Use a document generator** for RFPs, business cases, and governance board paperwork.
**Use AIR Blackbox** to prove to an auditor what your AI system actually did, and to guarantee the proof still verifies after quantum computers arrive.

## Philosophy

**AIR is a witness, not a gatekeeper, until you tell it to be.**

- **Non-blocking**, recording or gating failures never break production flow
- **Lossy-safe**, dropped audit records are acceptable; dropped user requests are not
- **Self-degrading**, if the collector is down, spans drop silently; warnings logged, never errors returned

You cannot detect what you cannot see. You cannot prevent what you cannot detect. You cannot trust what you cannot prove. AIR Blackbox is the layer that makes proof possible, today and after quantum.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

False positive on a compliance check? Correct it, your correction flows into training data for the fine-tuned scanner model. The scanner gets smarter with every fix your team submits.

Good first issues: labeled `good first issue`, mostly new compliance checks and framework integrations.

## License

Apache-2.0, [airblackbox.ai](https://airblackbox.ai)

*This is not a certified compliance test. It is a starting point to identify potential gaps.*

---

If this helps you prepare for EU AI Act enforcement, [star the repo](https://github.com/airblackbox/airblackbox), it helps other teams find it.
