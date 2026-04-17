# air-blackbox

**EU AI Act compliance scanner for Python AI agents.**

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![Downloads](https://img.shields.io/badge/PyPI_Downloads-14%2C294%2B-brightgreen)](https://pypi.org/project/air-blackbox/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

```bash
pip install air-blackbox
air-blackbox scan agent.py
```

## Highlights

- **39 compliance checks** across 6 EU AI Act articles (9, 10, 11, 12, 14, 15)
- **GDPR scanner** — 8 checks for consent, minimization, erasure, retention, DPIA
- **Bias & fairness** — 6 checks for demographic parity, equalized odds, calibration
- **Prompt injection detection** — 20 weighted patterns across 5 attack categories
- **Standards crosswalk** — one scan maps to EU AI Act + ISO 42001 + NIST AI RMF
- **Evidence bundles** — signed ZIP exports for auditors (SHA-256 manifest + HMAC)
- **7 framework trust layers** — drop-in compliance for LangChain, CrewAI, OpenAI, and more
- **No cloud, no API keys** — everything runs on your machine

## Quick Start

Scan your codebase:

```bash
pip install air-blackbox
air-blackbox scan agent.py          # 39 EU AI Act checks
air-blackbox comply -v              # per-article breakdown
```

Wrap your client for runtime tracing:

```python
from air_blackbox import AirBlackbox

air = AirBlackbox()
client = air.wrap(openai.OpenAI())
response = client.chat.completions.create(...)  # traced + scanned
```

Drop-in framework trust layer (no code changes):

```python
from air_blackbox.trust.langchain import AirLangChainHandler

chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})
```

## What It Checks

| Area | Checks | What It Finds |
|---|---|---|
| **EU AI Act** (Arts 9–15) | 39 | Risk management, data governance, record-keeping, human oversight, robustness |
| **GDPR** | 8 | Consent, minimization, erasure, retention, DPIA, breach notification |
| **Bias & Fairness** | 6 | Demographic parity, equalized odds, calibration, explainability |
| **Prompt Injection** | 20 patterns | Role override, delimiter injection, privilege escalation, data exfiltration |
| **Standards** | 3 frameworks | Maps to EU AI Act + ISO 42001 + NIST AI RMF simultaneously |

## CLI

```bash
air-blackbox scan [file]          # Full compliance scan
air-blackbox comply -v            # EU AI Act articles 9–15
air-blackbox scan-injection       # Prompt injection detection
air-blackbox scan-gdpr            # GDPR gap analysis
air-blackbox scan-bias            # Fairness checks
air-blackbox standards [file]     # Cross-framework mapping
air-blackbox evidence-export      # Signed ZIP for auditors
air-blackbox demo                 # Interactive walkthrough
```

## Trust Layers

Drop-in compliance for your existing agent code. Non-blocking — logs to `.air.json` audit records.

| Framework | Install |
|---|---|
| LangChain / LangGraph | `pip install "air-blackbox[langchain]"` |
| CrewAI | `pip install "air-blackbox[crewai]"` |
| AutoGen | `pip install "air-blackbox[autogen]"` |
| OpenAI Agents SDK | `pip install "air-blackbox[openai]"` |
| Google ADK | `pip install "air-blackbox[google]"` |
| Haystack | `pip install "air-blackbox[haystack]"` |
| Claude Agent SDK | `pip install "air-blackbox[claude]"` |

Or install everything: `pip install "air-blackbox[all]"`

## Evidence Bundles

Export everything an auditor needs as a cryptographically signed ZIP:

```bash
air-blackbox evidence-export

# Creates: audit_2026-04-11.zip
# ├── compliance_report.json   (EU AI Act + GDPR + Bias)
# ├── audit_chain.hmac         (tamper-proof record chain)
# ├── aibom.json               (CycloneDX AI Bill of Materials)
# ├── manifest.sha256          (file hashes)
# └── signature.hmac           (bundle-level HMAC)
```

## How It Fits Together

air-blackbox is the scanner. **[air-trust](https://github.com/airblackbox/air-trust)** is the cryptographic proof layer underneath.

```
Your AI Agent
       │
       ├── air-blackbox scan     →  finds compliance gaps
       ├── air-trust             →  proves what happened (HMAC + Ed25519)
       ├── air-gate              →  human approval before dangerous tool calls
       └── air-blackbox-mcp      →  all of the above inside Claude Desktop / Cursor
```

| Package | What It Does |
|---|---|
| **[air-trust](https://github.com/airblackbox/air-trust)** | Tamper-evident audit chain + Ed25519 signed handoffs |
| **[air-gate](https://github.com/airblackbox/air-gate)** | Human-in-the-loop tool gating (Article 14) |
| **[air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp)** | MCP server for Claude Desktop, Cursor, Claude Code |
| **[air-platform](https://github.com/airblackbox/air-platform)** | Docker Compose — full stack in one command |
| **[compliance-action](https://github.com/airblackbox/compliance-action)** | GitHub Action — checks on every pull request |

## Who Made This

Built by [Jason Shotwell](mailto:jason@airblackbox.ai). EU AI Act enforcement begins August 2, 2026 — this is the scanner that tells you where you stand.

## Learn More

- **[airblackbox.ai](https://airblackbox.ai)** — project homepage
- **[Interactive demo](https://airblackbox.ai/demo/signed-handoff)** — signed handoffs in action
- **[PyPI](https://pypi.org/project/air-blackbox/)** — package page
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the ecosystem fits together
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — how to help

## License

Apache-2.0. See [LICENSE](LICENSE).

---

If this helps your team prepare for EU AI Act enforcement, **[star the repo](https://github.com/airblackbox/gateway)** — it helps other teams find it.
