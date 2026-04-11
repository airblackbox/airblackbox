# gateway

**OpenAI-compatible reverse proxy that records every LLM call as an OpenTelemetry trace.**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

```bash
git clone https://github.com/airblackbox/gateway.git
cd gateway && docker compose up
# Point your AI clients at http://localhost:8080/v1
```

## What It Does

Gateway sits between your AI agents and any LLM API. Every call passes through and gets recorded as an OpenTelemetry trace — model, tokens, latency, cost, and full prompt/completion content (redactable).

Your agents don't change. You just swap the base URL.

```
Your Agent  →  Gateway (:8080)  →  OpenAI / Anthropic / Any LLM
                  │
                  └──→ OTel traces → Jaeger / Prometheus / Any backend
```

## Why Use a Proxy?

If you're using multiple frameworks (LangChain, CrewAI, AutoGen, raw OpenAI calls), a proxy captures everything in one place without adding SDK instrumentation to each one. It also means:

- **No code changes** — agents talk to `localhost:8080` instead of `api.openai.com`
- **Framework-agnostic** — works with any client that speaks the OpenAI API format
- **PII redaction** — hash sensitive content before it hits your observability backend
- **Cost tracking** — unified token/cost metrics across all providers
- **Loop detection** — flags agents stuck in repeat cycles

## Quick Start

```bash
cp .env.example .env          # Add your OPENAI_API_KEY
docker compose up              # Starts Gateway + Jaeger + Prometheus
```

Then point any OpenAI-compatible client at the gateway:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
# Traced automatically — view at http://localhost:16686 (Jaeger)
```

## Configuration

| Env Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your upstream API key |
| `GATEWAY_PORT` | `8080` | Proxy listen port |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://jaeger:4317` | Where to send traces |
| `REDACT_MODE` | `hash_and_preview` | PII handling: `none`, `hash`, `hash_and_preview` |
| `LOOP_DETECTION` | `true` | Flag repeated tool calls |
| `REPEAT_THRESHOLD` | `6` | Calls before flagging a loop |

## Part of AIR Blackbox

Gateway is the ingestion layer in the [AIR Blackbox](https://airblackbox.ai) ecosystem:

| Component | What It Does |
|---|---|
| **gateway** (this repo) | Reverse proxy — captures LLM calls as OTel traces |
| [air-trust](https://pypi.org/project/air-trust/) | HMAC-SHA256 audit chain + Ed25519 signed handoffs |
| [air-blackbox](https://pypi.org/project/air-blackbox/) | CLI compliance scanner — 39 EU AI Act checks |
| [air-blackbox-mcp](https://pypi.org/project/air-blackbox-mcp/) | MCP server for Claude Desktop, Cursor, Claude Code |
| [air-platform](https://github.com/airblackbox/air-platform) | Docker Compose — full stack in one command |

## License

Apache-2.0. See [LICENSE](LICENSE).
