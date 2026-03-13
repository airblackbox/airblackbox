---
title: "We Published a Formal Spec for Tamper-Evident AI Audit Chains"
published: false
description: "AIR Blackbox v1.2.6 ships a Claude Agent SDK trust layer, 4600 training examples, and the first published specification for HMAC-SHA256 audit chains in AI agent systems."
tags: ai, python, opensource, security
cover_image:
---

The EU AI Act requires that high-risk AI systems automatically record events over their lifetime — and that those logs can't be quietly modified after the fact. Article 12 is specific:

> "High-risk AI systems shall technically allow for the automatic recording of events ('logs') over the lifetime of the system."

Most teams building AI agents have no answer for this. They have `print()` statements. Maybe a log file. Nothing a regulator would accept.

We just published a formal specification for how to solve this problem. It's open-source, it's free, and it's the first published spec of its kind.

## What we shipped in v1.2.6

Three things landed this week:

**1. HMAC-SHA256 Audit Chain Specification v1.0**

A formal, citeable spec that defines how to build tamper-evident audit trails for AI agents. Every record is linked to the previous one via HMAC-SHA256 — modify any record and the entire chain breaks from that point forward.

The spec covers:
- The `.air.json` record format (with full JSON Schema)
- The chaining algorithm (genesis hash → linked sequence)
- 7 record types: `llm_call`, `tool_call`, `pre_tool_call`, `permission_decision`, `injection_blocked`, `human_override`, `session_end`
- EU AI Act article mapping (how each record type satisfies specific requirements)
- A standalone verification script

Here's what chain verification looks like:

```python
import json, hashlib, hmac

def verify_chain(records, signing_key):
    key = signing_key.encode("utf-8")
    prev_hash = b"genesis"

    for i, record in enumerate(records):
        record_clean = {k: v for k, v in record.items() if k != "chain_hash"}
        record_bytes = json.dumps(record_clean, sort_keys=True).encode("utf-8")
        expected = hmac.new(key, prev_hash + record_bytes, hashlib.sha256)

        stored = record.get("chain_hash")
        if stored and stored != expected.hexdigest():
            return False, i  # Chain broken at record i

        prev_hash = expected.digest()

    return True, len(records)
```

If someone changes a `risk_level` from `"CRITICAL"` to `"LOW"` in Record 5, every hash from Record 5 onward fails verification. That's the property that makes it audit-ready.

Full spec: [audit-chain-v1.md on GitHub](https://github.com/airblackbox/gateway/blob/main/docs/spec/audit-chain-v1.md)

**2. Anthropic Claude Agent SDK trust layer**

AIR Blackbox now supports 6 agent frameworks. The newest is the Anthropic Claude Agent SDK — the hooks-based architecture made this a natural fit.

```python
from claude_agent_sdk import ClaudeAgentOptions
from air_blackbox.trust.claude_agent import air_claude_hooks

options = ClaudeAgentOptions(
    hooks=air_claude_hooks(
        detect_pii=True,
        detect_injection=True,
    ),
)
```

What this does under the hood:

- **PreToolUse hook**: Scans every tool input for PII (email, SSN, phone, credit cards) and prompt injection patterns (15 weighted patterns with confidence scoring). Blocks tool calls above 0.8 injection confidence.
- **PostToolUse hook**: Logs every tool execution as a `.air.json` audit record with risk classification (CRITICAL/HIGH/MEDIUM/LOW).
- **PostToolUseFailure hook**: Captures tool errors for the audit trail.
- **Stop hook**: Writes a session summary record.

All records are written locally. Nothing leaves your machine.

The full framework support list:

| Framework | Trust Layer | Status |
|-----------|------------|--------|
| LangChain / LangGraph | Callback handler | Shipped |
| CrewAI | Agent wrapper | Shipped |
| OpenAI SDK | Client wrapper | Shipped |
| AutoGen | Agent wrapper | Shipped |
| Google ADK | Agent wrapper | Shipped |
| **Claude Agent SDK** | **Hooks + permission handler** | **New in v1.2.6** |

Install: `pip install air-blackbox[claude]`

**3. 4,600 training examples for the fine-tuned compliance model**

We went from 18 hand-crafted examples to 4,602 diverse training examples covering all 6 frameworks at 4 compliance levels (0/6, 2/6, 4/6, 6/6). The training data generator produces realistic code snippets — not toy examples — with varied compliance gaps.

This is for the fine-tuned Llama model that does deep compliance analysis locally via Ollama. More training data = fewer false positives = a model that actually understands the difference between "has logging" and "has tamper-evident logging."

## How the audit chain actually works

The chain is dead simple. Each `.air.json` record gets a `chain_hash` field computed like this:

```
Record 0: hash = HMAC-SHA256(key, b"genesis" || JSON(record_0))
Record 1: hash = HMAC-SHA256(key, hash_0_bytes || JSON(record_1))
Record 2: hash = HMAC-SHA256(key, hash_1_bytes || JSON(record_2))
```

Each hash depends on every previous hash. Change any record and the chain breaks. The signing key is set via `TRUST_SIGNING_KEY` env var — without it, anyone can compute valid hashes. With it, only key holders can produce or verify the chain.

A typical audit record looks like this:

```json
{
  "version": "1.0.0",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "a1b2c3d4e5f67890",
  "timestamp": "2026-03-13T14:30:01.200Z",
  "type": "tool_call",
  "tool_name": "Bash",
  "risk_level": "CRITICAL",
  "status": "success",
  "framework": "claude_agent_sdk",
  "chain_hash": "b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9..."
}
```

The verification script catches tampering instantly:

```bash
$ python verify_chain.py ./runs --key my-secret-key

Loaded 1250 records from ./runs
Date range: 2026-01-15T09:00:00Z → 2026-03-13T14:35:00Z

PASS: Chain intact. 1250/1250 records verified.
```

Tamper with any record and you get:

```
FAIL: Chain broken at record 847 of 1250.
  Record: 6ba7b810-9dad-11d1-80b4-00c04fd430c8
  Timestamp: 2026-03-01T11:22:33.000Z
```

## Why this matters

The EU AI Act deadline is August 2026. Five months from now. Most AI teams I've talked to are in one of two camps:

1. "We'll figure it out later." (Dangerous.)
2. "We need to buy an enterprise compliance platform." (Expensive and unnecessary for most.)

There's a third option: add compliance as a layer to the tools you're already using. That's what AIR Blackbox does. One pip install, a few lines of code, and you have tamper-evident audit trails, PII scanning, injection detection, and risk classification — all running locally.

This isn't a substitute for legal counsel. It checks technical requirements, not legal compliance. It's a linter for AI governance, not a lawyer.

## What's next

- **Fine-tune run**: 4,600 examples through Unsloth/LoRA to produce a smarter local compliance model
- **ISO 42001 / NIST AI RMF mapping**: Cross-reference our 6-article checks to other standards
- **CI/CD integration**: GitHub Action for compliance checks on every PR

## Try it

```bash
pip install air-blackbox

# Scan your codebase
air-blackbox comply --scan . -v

# Check compliance history
air-blackbox history

# Run the demo
air-blackbox demo
```

GitHub: [github.com/airblackbox/gateway](https://github.com/airblackbox/gateway)
Website: [airblackbox.ai](https://airblackbox.ai)
PyPI: [pypi.org/project/air-blackbox](https://pypi.org/project/air-blackbox/)
Audit Chain Spec: [audit-chain-v1.md](https://github.com/airblackbox/gateway/blob/main/docs/spec/audit-chain-v1.md)

Apache 2.0. Star it, try it, break it. PRs welcome.
