# air-openai-trust

**AIR Trust Layer for OpenAI Python SDK** - EU AI Act compliance infrastructure for every OpenAI API call.

Wraps your existing OpenAI client to automatically add:

- **HMAC-SHA256 tamper-evident audit chains** for every API call (Art. 12)
- **PII detection** in prompts and responses (Art. 10)
- **Prompt injection scanning** (Art. 15)
- **Token usage and latency tracking**
- **Human delegation verification** (Art. 14)
- **Output validation** for robustness (Art. 15)

Part of the [AIR Blackbox](https://airblackbox.ai) ecosystem - open-source EU AI Act compliance tooling for Python AI frameworks.

## Install

```bash
pip install air-openai-trust
```

## Quick Start

### Option 1: Wrap an existing client

```python
from openai import OpenAI
from air_openai_trust import attach_trust

client = OpenAI()
client = attach_trust(client)

# Use normally - every call is now audit-logged
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
```

### Option 2: Create a pre-configured client

```python
from air_openai_trust import air_openai_client

client = air_openai_client()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
)
```

Both approaches produce `.air.json` audit records in the `./runs/` directory (configurable).

## What It Does

### Audit Trail (Art. 12 - Record-Keeping)

Every API call generates a `.air.json` file with:

- Timestamp, model, provider
- Token usage (prompt, completion, total)
- Latency in milliseconds
- PII alerts (if detected)
- Injection alerts (if detected)
- HMAC-SHA256 chain hash linking to the previous record

The chain hashes create a **tamper-evident sequence** - modifying any record invalidates all subsequent hashes. This gives auditors cryptographic proof that logs haven't been altered.

### PII Detection (Art. 10 - Data Governance)

Automatically scans prompts and responses for:

- Email addresses
- Social Security Numbers
- Phone numbers
- Credit card numbers

Detected PII is logged as alerts (with values redacted) in the audit record. Your API calls still work normally.

### Prompt Injection Scanning (Art. 15 - Robustness)

Scans for common injection patterns like:

- "ignore previous instructions"
- "you are now"
- "system prompt:"
- "new instructions:"
- "override:"

Detected injections are logged as alerts in the audit record.

### Output Validation

```python
from air_openai_trust import validate_output

result = validate_output("Some LLM response text")
# Returns: {"safe": True, "pii_alerts": [], "injection_alerts": []}
```

### Human Delegation (Art. 14 - Human Oversight)

```python
from air_openai_trust import check_delegation

# Verify human authorization before agent actions
if check_delegation(authorized_by="jason@example.com", action="send_email"):
    # proceed with action
    pass
```

## Configuration

### Audit directory

```python
# Via argument
client = attach_trust(client, runs_dir="./my-audit-logs")

# Via environment variable
# export AIR_RUNS_DIR=./my-audit-logs
client = attach_trust(client)
```

### Signing key

```python
# Via environment variable (recommended)
# export TRUST_SIGNING_KEY=my-secret-key

# Default key is used if not set
```

## Non-Blocking

All audit logging is non-blocking. If logging fails for any reason, your OpenAI API calls still work normally. The trust layer never crashes your application.

## Supported APIs

| API | Audit Logged |
|-----|-------------|
| `chat.completions.create()` | Yes - full scanning + audit chain |
| `embeddings.create()` | Yes - usage tracking + audit chain |
| All other endpoints | Passed through to OpenAI client |

## Audit Record Format

```json
{
  "version": "1.0.0",
  "run_id": "uuid",
  "timestamp": "2026-03-30T12:00:00+00:00",
  "type": "llm_call",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "tokens": {
    "prompt": 10,
    "completion": 25,
    "total": 35
  },
  "duration_ms": 450,
  "status": "success",
  "message_count": 1,
  "pii_alerts": [],
  "injection_alerts": [],
  "chain_hash": "a1b2c3..."
}
```

## Full Ecosystem

`air-openai-trust` is one of 11 PyPI packages in the AIR Blackbox ecosystem:

| Package | Purpose |
|---------|---------|
| `air-compliance` | CLI scanner - `air-compliance scan .` |
| `air-blackbox` | Governance control plane |
| `air-blackbox-mcp` | MCP server for AI editors |
| `air-blackbox-sdk` | Python SDK |
| `air-langchain-trust` | Trust layer for LangChain |
| `air-crewai-trust` | Trust layer for CrewAI |
| `air-anthropic-trust` | Trust layer for Anthropic Claude SDK |
| `air-adk-trust` | Trust layer for Google ADK |
| `air-openai-trust` | Trust layer for OpenAI SDK (this package) |
| `air-rag-trust` | Trust layer for RAG pipelines |
| `air-gate` | HMAC-SHA256 audit chain engine with tool gating |

## Links

- **Website**: [airblackbox.ai](https://airblackbox.ai)
- **GitHub**: [github.com/airblackbox/air-openai-trust](https://github.com/airblackbox/air-openai-trust)
- **Demo**: [airblackbox.ai/demo](https://airblackbox.ai/demo)

## License

Apache 2.0
