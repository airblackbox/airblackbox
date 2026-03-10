# AIR Blackbox

**AI governance control plane — compliance, inventory, incident response, and audit for AI agents.**

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![CI](https://github.com/airblackbox/gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/airblackbox/gateway/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-enabled-blueviolet?logo=opentelemetry)](https://opentelemetry.io)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://pypi.org/project/air-blackbox/)
[![Go 1.22+](https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go&logoColor=white)](https://go.dev)

```
pip install air-blackbox
```

**Four commands. One product. 90% automated compliance.**

```bash
air-blackbox comply      # EU AI Act compliance from live traffic
air-blackbox discover    # Shadow AI inventory + AI-BOM generation
air-blackbox replay      # Incident reconstruction from audit chain
air-blackbox export      # Signed evidence bundle for auditors
```

> **August 2, 2026** — EU AI Act high-risk enforcement deadline. Penalties up to €35M or 7% of global turnover.

---

## 30-Second Demo

No Docker. No config. No API keys.

```bash
pip install air-blackbox
air-blackbox demo
```

You'll see:
- 10 sample AI agent records generated (4 models, 3 providers)
- EU AI Act compliance check across Articles 9-15
- RISK_ASSESSMENT.md and DATA_GOVERNANCE.md templates created

Then explore:

```bash
air-blackbox comply -v                          # Full compliance with fix hints
air-blackbox discover                           # Models, providers, tools detected
air-blackbox discover --format=cyclonedx -o aibom.json  # CycloneDX AI-BOM
air-blackbox replay                             # Audit trail timeline
air-blackbox replay --verify                    # HMAC chain integrity check
air-blackbox export                             # Signed evidence bundle
```

---

## What It Does

| Command | What You Get |
|---------|-------------|
| `comply` | 20 checks across EU AI Act Articles 9-15. 90% auto-detected from gateway traffic. Per-article status with fix hints. |
| `discover` | AI Bill of Materials (CycloneDX 1.6) from observed traffic. Shadow AI detection against approved model registry. Tool and provider inventory. |
| `replay` | Full incident reconstruction from tamper-proof audit chain. HMAC-SHA256 verification. Filter by time, model, status. Detail view per run. |
| `export` | Signed evidence bundle: compliance scan + AI-BOM + audit trail + HMAC attestation. One JSON file for your auditor or insurer. |

---

## How It Works

AIR Blackbox is a reverse proxy + Python SDK. Route your AI traffic through it and every call is recorded, analyzed, and compliance-checked automatically.

```
Your AI Agent → AIR Blackbox Gateway → LLM Provider
                      │
                      ├── HMAC-signed audit record (.air.json)
                      ├── PII detection + prompt injection scanning
                      ├── AI-BOM generation (models, tools, providers)
                      ├── EU AI Act compliance mapping (Articles 9-15)
                      └── Evidence export for auditors
```

**The gateway is a witness, not a gatekeeper.** It cannot cause your AI system to fail. Recording is best-effort; proxying is guaranteed.

---

## Quick Start

### Option 1: Python SDK (fastest)

```bash
pip install air-blackbox
air-blackbox demo        # See it work immediately
```

### Option 2: With your code

```python
from air_blackbox import AirBlackbox

air = AirBlackbox()
client = air.wrap(openai.OpenAI())
# Every LLM call is now HMAC-logged through the gateway
```

### Option 3: Framework auto-detection

```python
from air_blackbox import AirTrust

trust = AirTrust()
trust.attach(your_langchain_agent)
# Framework auto-detected. Audit trails active.
```

### Option 4: LangChain trust layer

```python
from air_blackbox.trust.langchain import AirLangChainHandler

chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})
# Every LLM call + tool invocation logged with PII scanning + injection detection
```

### Option 5: Full gateway stack (Docker)

```bash
git clone https://github.com/airblackbox/gateway.git
cd gateway
cp .env.example .env   # add your OPENAI_API_KEY
docker compose up
```

Then point any OpenAI-compatible client at `http://localhost:8080/v1`.

---

## Install

```bash
pip install air-blackbox                    # Core SDK + compliance + AI-BOM
pip install "air-blackbox[langchain]"       # + LangChain trust layer
pip install "air-blackbox[openai]"          # + OpenAI client wrapper
pip install "air-blackbox[all]"             # Everything
```

---

## EU AI Act Compliance Coverage

`air-blackbox comply -v` checks 20 controls across 6 articles:

| Article | What It Covers | Detection |
|---------|---------------|-----------|
| **Art. 9** — Risk Management | Risk assessment docs, active mitigations | HYBRID |
| **Art. 10** — Data Governance | PII in prompts, data vault, governance docs | AUTO + HYBRID |
| **Art. 11** — Technical Documentation | README, AI-BOM inventory, model cards, doc currency | AUTO + HYBRID |
| **Art. 12** — Record-Keeping | Event logging, HMAC audit chain, traceability, retention | **100% AUTO** |
| **Art. 14** — Human Oversight | Human-in-the-loop, kill switch, operator docs | AUTO + MANUAL |
| **Art. 15** — Robustness & Security | Injection protection, error resilience, access control, red team | AUTO + MANUAL |

**Detection types:**
- **AUTO** — Gateway detects from live traffic. No action needed.
- **HYBRID** — Gateway detects partially. Code scan fills the gap.
- **MANUAL** — Requires human documentation. Gateway provides templates.

---

## Shadow AI Detection

Discover unapproved AI models and services in your environment:

```bash
# See everything your agents are using
air-blackbox discover

# Lock down what's approved
air-blackbox discover --init-registry

# Flag anything not on the list
air-blackbox discover --approved=approved-models.json
```

Detects models, providers, and tools from observed gateway traffic. Generates CycloneDX 1.6 AI-BOM for supply chain transparency.

---

## Trust Layers

Non-blocking callback handlers that observe and log — never control or block.

| Framework | Install | Status |
|-----------|---------|--------|
| **LangChain / LangGraph** | `pip install "air-blackbox[langchain]"` | ✅ Full |
| **OpenAI SDK** | `pip install "air-blackbox[openai]"` | ✅ Full |
| **CrewAI** | `pip install "air-blackbox[crewai]"` | 🔧 Scaffold |
| **AutoGen** | `pip install "air-blackbox[autogen]"` | 🔧 Scaffold |
| **Google ADK** | `pip install "air-blackbox[adk]"` | 🔧 Scaffold |

Trust layers include:
- **PII detection** — emails, SSNs, phone numbers, credit cards in prompts
- **Prompt injection scanning** — 7 patterns (instruction override, role hijack, etc.)
- **Audit logging** — every LLM call + tool invocation as `.air.json`
- **Non-blocking** — if logging fails, your agent keeps running

---

## Why Not Langfuse / Helicone / Datadog?

They answer *"how is the system performing?"*

AIR answers **"what exactly happened, and can we prove it?"**

|  | Observability Tools | AIR Blackbox |
|--|---|---|
| Where data lives | Their cloud | **Your** vault (S3/MinIO/local) |
| PII in traces | Raw content exposed | Vault references only |
| Tamper-evident | ❌ | ✅ HMAC-SHA256 chain |
| Compliance checks | ❌ | ✅ 20 checks, EU AI Act Art. 9-15 |
| AI-BOM generation | ❌ | ✅ CycloneDX 1.6 |
| Shadow AI detection | ❌ | ✅ Approved model registry |
| Evidence export | ❌ | ✅ Signed bundles for auditors |
| Incident replay | ❌ | ✅ Full reconstruction + chain verify |

---

## Architecture

```
gateway/
├── cmd/              # Go proxy binary + replayctl CLI
├── collector/        # Go gateway core
├── pkg/              # Go shared packages (trust, audit chain)
├── sdk/              # Python SDK (pip install air-blackbox)
│   └── air_blackbox/
│       ├── cli.py            # The 4 commands
│       ├── gateway_client.py # Connects to running gateway
│       ├── compliance/       # EU AI Act compliance engine
│       ├── aibom/            # AI-BOM generator + shadow AI
│       ├── replay/           # Incident replay + HMAC verify
│       ├── export/           # Signed evidence bundles
│       └── trust/            # Framework trust layers
│           ├── langchain/
│           ├── openai_agents/
│           ├── crewai/
│           ├── autogen/
│           └── adk/
├── deploy/           # Docker Compose + Prometheus + Makefile
├── docs/             # Documentation + quickstart
└── examples/         # Demo apps
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_ADDR` | `:8080` | Gateway listen address |
| `PROVIDER_URL` | `https://api.openai.com` | Upstream LLM provider |
| `VAULT_ENDPOINT` | `localhost:9000` | MinIO/S3 endpoint |
| `VAULT_ACCESS_KEY` | `minioadmin` | S3 access key |
| `VAULT_SECRET_KEY` | `minioadmin` | S3 secret key |
| `VAULT_BUCKET` | `air-runs` | S3 bucket name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `localhost:4317` | OTel collector gRPC |
| `RUNS_DIR` | `./runs` | AIR record directory |
| `TRUST_SIGNING_KEY` | *(none)* | HMAC-SHA256 signing key |

---

## Contributing

We're looking for contributors interested in AI governance, compliance tooling, and agent safety.

**Current priorities:**
- Trust layers for CrewAI, AutoGen, Google ADK
- CycloneDX AI-BOM enrichment (training data provenance, model weights origin)
- Latency benchmarks for trust layer overhead
- Documentation and integration examples

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

Apache-2.0. See [LICENSE](LICENSE) for details.
