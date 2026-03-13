# AIR Blackbox Audit Chain Specification v1.0

**Status:** Published
**Version:** 1.0.0
**Date:** 2026-03-13
**Author:** Jason Shotwell (jason.j.shotwell@gmail.com)
**Repository:** https://github.com/airblackbox/gateway
**License:** Apache 2.0

---

## 1. Introduction

### 1.1 Purpose

This specification defines the tamper-evident audit chain format used by AIR Blackbox to log AI agent operations. The audit chain creates a cryptographically linked sequence of records that satisfies the record-keeping requirements of the EU AI Act (Article 12) and provides a verifiable evidence trail for regulators, auditors, and insurers.

### 1.2 Scope

This specification covers:

- The `.air.json` record format for individual audit entries
- The HMAC-SHA256 chaining algorithm that links records into a tamper-evident sequence
- Entry types for LLM calls, tool executions, human oversight events, and system events
- The verification algorithm for detecting tampering
- The signed evidence bundle format for export

This specification does not cover:

- Legal compliance advice (consult qualified legal counsel)
- Network transport protocols between trust layers and storage backends
- Gateway proxy implementation details

### 1.3 Definitions

| Term | Definition |
|------|-----------|
| **Audit Chain** | An ordered sequence of `.air.json` records linked by HMAC-SHA256 hashes, where each record's hash depends on the previous record's hash. |
| **Audit Record** | A single `.air.json` file capturing one discrete agent event (LLM call, tool execution, etc.). |
| **Chain Hash** | The HMAC-SHA256 hash stored in each record's `chain_hash` field, computed from the record content and the previous record's chain hash. |
| **Genesis Hash** | The initial hash value (`genesis`) used as the `previous_hash` for the first record in a chain. |
| **Signing Key** | A secret key used for HMAC computation. Set via the `TRUST_SIGNING_KEY` environment variable. |
| **Trust Layer** | A framework-specific adapter (LangChain callback, CrewAI hook, Claude Agent SDK hook, etc.) that generates audit records from agent operations. |
| **Evidence Bundle** | A signed JSON document combining compliance scan results, AI-BOM, audit trail statistics, and an HMAC attestation. |

### 1.4 EU AI Act Context

The EU AI Act (Regulation 2024/1689) becomes enforceable in August 2026. Article 12 requires that high-risk AI systems:

> "shall technically allow for the automatic recording of events ('logs') over the lifetime of the system."

These logs must be detailed enough for regulators to verify system behavior, and must be protected against unauthorized modification. The HMAC-SHA256 audit chain satisfies both requirements: it automatically records events and makes any modification cryptographically detectable.

---

## 2. Audit Record Format

### 2.1 File Format

Each audit record is a single JSON file with the extension `.air.json`, stored in a runs directory (default: `./runs/`). The filename is the record's `run_id` with the `.air.json` extension:

```
runs/
  550e8400-e29b-41d4-a716-446655440000.air.json
  6ba7b810-9dad-11d1-80b4-00c04fd430c8.air.json
  ...
```

### 2.2 Required Fields

Every audit record MUST contain the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Specification version. MUST be `"1.0.0"`. |
| `run_id` | string | Unique identifier for this record. UUID v4 format. |
| `timestamp` | string | ISO 8601 UTC timestamp with `Z` suffix. Example: `"2026-03-13T14:30:00.000Z"` |
| `type` | string | Record type. One of: `llm_call`, `tool_call`, `tool_error`, `pre_tool_call`, `permission_decision`, `injection_blocked`, `session_end`, `human_override`. |
| `status` | string | Outcome status. One of: `success`, `error`, `timeout`, `blocked`, `scanned`, `completed`, `denied`, `allowed`, `approval_required`. |

### 2.3 Common Optional Fields

These fields appear on most record types:

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Correlation ID linking related records in the same agent session. First 16 hex characters of a UUID. |
| `session_id` | string | Session identifier for multi-turn conversations. |
| `framework` | string | Agent framework that produced this record. One of: `langchain`, `crewai`, `openai`, `autogen`, `haystack`, `claude_agent_sdk`. |
| `chain_hash` | string | HMAC-SHA256 hash linking this record to the chain. Hex-encoded. See Section 3. |
| `pii_alerts` | array | PII detections. Each element: `{"type": "<pii_type>", "count": <int>, "timestamp": "<iso8601>"}`. Types: `email`, `ssn`, `phone`, `credit_card`, `iban`. |
| `injection_alerts` | array | Injection pattern matches. Each element: `{"pattern": "<regex>", "weight": <float>, "timestamp": "<iso8601>"}`. |

### 2.4 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://airblackbox.ai/spec/audit-record-v1.schema.json",
  "title": "AIR Blackbox Audit Record v1.0",
  "type": "object",
  "required": ["version", "run_id", "timestamp", "type", "status"],
  "properties": {
    "version": {
      "type": "string",
      "const": "1.0.0"
    },
    "run_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique record identifier (UUID v4)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 UTC timestamp"
    },
    "type": {
      "type": "string",
      "enum": [
        "llm_call",
        "tool_call",
        "tool_error",
        "pre_tool_call",
        "permission_decision",
        "injection_blocked",
        "session_end",
        "human_override"
      ]
    },
    "status": {
      "type": "string",
      "enum": [
        "success", "error", "timeout",
        "blocked", "scanned", "completed",
        "denied", "allowed", "approval_required"
      ]
    },
    "trace_id": {
      "type": "string",
      "maxLength": 16
    },
    "session_id": {
      "type": "string"
    },
    "framework": {
      "type": "string",
      "enum": [
        "langchain", "crewai", "openai",
        "autogen", "haystack", "claude_agent_sdk"
      ]
    },
    "chain_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "HMAC-SHA256 chain hash (hex-encoded)"
    },
    "model": {
      "type": "string",
      "description": "LLM model identifier"
    },
    "provider": {
      "type": "string",
      "description": "LLM provider (openai, anthropic, google, etc.)"
    },
    "tokens": {
      "type": "object",
      "properties": {
        "prompt": { "type": "integer" },
        "completion": { "type": "integer" },
        "total": { "type": "integer" }
      }
    },
    "duration_ms": {
      "type": "integer",
      "minimum": 0,
      "description": "Operation duration in milliseconds"
    },
    "tool_name": {
      "type": "string",
      "description": "Name of the tool (for tool_call, pre_tool_call types)"
    },
    "risk_level": {
      "type": "string",
      "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
      "description": "EU AI Act risk classification"
    },
    "injection_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Injection detection confidence (0.0–1.0)"
    },
    "pii_alerts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": { "type": "string" },
          "count": { "type": "integer" },
          "timestamp": { "type": "string", "format": "date-time" }
        }
      }
    },
    "injection_alerts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "pattern": { "type": "string" },
          "weight": { "type": "number" },
          "timestamp": { "type": "string", "format": "date-time" }
        }
      }
    },
    "error": {
      "type": "string",
      "maxLength": 500,
      "description": "Error message (truncated to 500 chars)"
    },
    "request_vault_ref": {
      "type": "string",
      "description": "Vault reference for the request payload"
    },
    "response_vault_ref": {
      "type": "string",
      "description": "Vault reference for the response payload"
    },
    "request_checksum": {
      "type": "string",
      "description": "SHA-256 checksum of the request payload"
    },
    "response_checksum": {
      "type": "string",
      "description": "SHA-256 checksum of the response payload"
    }
  }
}
```

---

## 3. Cryptographic Integrity

### 3.1 HMAC-SHA256 Computation

Each record's `chain_hash` is computed using HMAC-SHA256 with the following inputs:

- **Key:** The signing key (from `TRUST_SIGNING_KEY` environment variable, or `"air-blackbox-default"` if not set)
- **Message:** The concatenation of the previous record's chain hash (as raw bytes) and the current record's JSON content (serialized with sorted keys, encoded as UTF-8)

```
chain_hash[i] = HMAC-SHA256(key, chain_hash[i-1] || JSON(record[i]))
```

Where `||` denotes byte concatenation and `JSON()` denotes `json.dumps(record, sort_keys=True).encode("utf-8")`.

### 3.2 Chain Linking

The chain is an ordered sequence where each record's hash depends on all previous records. This means modifying any record invalidates all subsequent hashes.

```
Record 0:  chain_hash = HMAC-SHA256(key, b"genesis" || JSON(record_0))
Record 1:  chain_hash = HMAC-SHA256(key, bytes(chain_hash_0) || JSON(record_1))
Record 2:  chain_hash = HMAC-SHA256(key, bytes(chain_hash_1) || JSON(record_2))
...
Record N:  chain_hash = HMAC-SHA256(key, bytes(chain_hash_N-1) || JSON(record_N))
```

The genesis value `b"genesis"` (7 bytes, ASCII) is the initial previous hash for the first record in any chain.

### 3.3 Key Management

The signing key determines who can produce valid chain hashes and who can verify them.

| Scenario | Key Source | Security Level |
|----------|-----------|----------------|
| Development | Default key `"air-blackbox-default"` | Low — anyone can verify and forge |
| Production | `TRUST_SIGNING_KEY` environment variable | Medium — key holder can verify and produce |
| Enterprise | External KMS (AWS KMS, HashiCorp Vault) | High — key never leaves the KMS |

**Recommendations:**

- Never use the default key in production
- Rotate keys periodically (the chain remains verifiable with the key that was active when each record was created)
- Store keys separately from audit records

### 3.4 Verification Algorithm

To verify a chain, a verifier with the signing key recomputes each hash and compares it to the stored `chain_hash`:

```python
import json
import hashlib
import hmac

def verify_chain(records: list[dict], signing_key: str) -> tuple[bool, int]:
    """Verify HMAC-SHA256 audit chain integrity.

    Args:
        records: List of audit records, sorted by timestamp.
        signing_key: The HMAC signing key.

    Returns:
        (intact: bool, verified_count: int)
        If intact is False, verified_count indicates where the break occurred.
    """
    key = signing_key.encode("utf-8")
    prev_hash = b"genesis"

    for i, record in enumerate(records):
        # Serialize record without the chain_hash field
        record_copy = {k: v for k, v in record.items() if k != "chain_hash"}
        record_bytes = json.dumps(record_copy, sort_keys=True).encode("utf-8")

        # Compute expected hash
        expected = hmac.new(key, prev_hash + record_bytes, hashlib.sha256).hexdigest()

        # Compare to stored hash
        stored = record.get("chain_hash")
        if stored and stored != expected:
            return False, i  # Chain broken at record i

        prev_hash = hmac.new(key, prev_hash + record_bytes, hashlib.sha256).digest()

    return True, len(records)
```

---

## 4. Entry Types

### 4.1 LLM Interaction Records

Type: `llm_call`

Generated when a trust layer intercepts an LLM API call. Captures the model, provider, token usage, and duration.

```json
{
  "version": "1.0.0",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "a1b2c3d4e5f67890",
  "timestamp": "2026-03-13T14:30:00.000Z",
  "type": "llm_call",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "tokens": {
    "prompt": 120,
    "completion": 350,
    "total": 470
  },
  "duration_ms": 2100,
  "status": "success",
  "pii_alerts": [],
  "injection_alerts": [],
  "framework": "langchain",
  "chain_hash": "a3f2b8c9d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"
}
```

### 4.2 Tool Execution Records

Type: `tool_call` (success) or `tool_error` (failure)

Generated after a tool completes execution. For Claude Agent SDK, this corresponds to the `PostToolUse` hook. For LangChain, the `on_tool_end` callback.

```json
{
  "version": "1.0.0",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "trace_id": "a1b2c3d4e5f67890",
  "session_id": "sess_abc123",
  "timestamp": "2026-03-13T14:30:01.200Z",
  "type": "tool_call",
  "tool_name": "Bash",
  "risk_level": "CRITICAL",
  "status": "success",
  "framework": "claude_agent_sdk",
  "chain_hash": "b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3"
}
```

### 4.3 Pre-Tool Scan Records

Type: `pre_tool_call`

Generated before tool execution (PreToolUse hook). Contains scan results including PII detection and injection analysis. This record type enables blocking dangerous operations before they execute.

```json
{
  "version": "1.0.0",
  "run_id": "7ca8b920-aebd-21e2-91c5-11d15564110a",
  "trace_id": "a1b2c3d4e5f67890",
  "session_id": "sess_abc123",
  "timestamp": "2026-03-13T14:30:01.000Z",
  "type": "pre_tool_call",
  "tool_name": "Write",
  "risk_level": "HIGH",
  "pii_alerts": [
    {"type": "email", "count": 2, "timestamp": "2026-03-13T14:30:01.000Z"}
  ],
  "injection_alerts": [],
  "injection_score": 0.0,
  "status": "scanned",
  "framework": "claude_agent_sdk"
}
```

### 4.4 Permission Decision Records

Type: `permission_decision`

Generated when the trust layer's permission handler makes a risk-based access control decision.

```json
{
  "version": "1.0.0",
  "run_id": "8db9c031-bfce-32f3-a2d6-22e26675221b",
  "timestamp": "2026-03-13T14:30:00.800Z",
  "type": "permission_decision",
  "tool_name": "Bash",
  "risk_level": "CRITICAL",
  "status": "denied",
  "framework": "claude_agent_sdk"
}
```

### 4.5 Injection Blocked Records

Type: `injection_blocked`

Generated when a prompt injection attempt is detected and blocked.

```json
{
  "version": "1.0.0",
  "run_id": "9ec0d142-c0df-43g4-b3e7-33f37786332c",
  "trace_id": "f9e8d7c6b5a49382",
  "timestamp": "2026-03-13T14:30:02.500Z",
  "type": "injection_blocked",
  "tool_name": "Bash",
  "risk_level": "CRITICAL",
  "injection_score": 0.9,
  "injection_alerts": [
    {"pattern": "ignore (?:all )?previous instructions", "weight": 0.9, "timestamp": "2026-03-13T14:30:02.500Z"}
  ],
  "status": "blocked",
  "framework": "claude_agent_sdk"
}
```

### 4.6 Human Override Records

Type: `human_override`

Generated when a human intervenes in agent execution — approving, denying, or modifying an agent action.

```json
{
  "version": "1.0.0",
  "run_id": "0fd1e253-d1e0-54h5-c4f8-44048897443d",
  "session_id": "sess_abc123",
  "timestamp": "2026-03-13T14:30:03.000Z",
  "type": "human_override",
  "tool_name": "Write",
  "risk_level": "HIGH",
  "status": "allowed",
  "framework": "claude_agent_sdk"
}
```

### 4.7 Session End Records

Type: `session_end`

Generated when an agent session terminates.

```json
{
  "version": "1.0.0",
  "run_id": "1ge2f364-e2f1-65i6-d5g9-55159908554e",
  "session_id": "sess_abc123",
  "timestamp": "2026-03-13T14:35:00.000Z",
  "type": "session_end",
  "status": "completed",
  "framework": "claude_agent_sdk"
}
```

---

## 5. EU AI Act Mapping

### 5.1 Article 12 — Record-Keeping

Article 12 requires automatic recording of events over the system's lifetime. The audit chain satisfies this through:

| Requirement | How AIR Blackbox Satisfies It |
|-------------|-------------------------------|
| Automatic recording | Trust layers generate `.air.json` records without developer intervention |
| Event logging over lifetime | Records persist in the runs directory across sessions |
| Sufficient detail for verification | Each record captures model, tokens, duration, tool calls, PII alerts, injection alerts |
| Protection against modification | HMAC-SHA256 chain makes any modification cryptographically detectable |
| Traceability | `trace_id` and `session_id` link related records across a session |

### 5.2 Article 14 — Human Oversight

Article 14 requires that humans can effectively oversee the AI system. The audit chain supports this through:

| Requirement | How AIR Blackbox Satisfies It |
|-------------|-------------------------------|
| Understand system capabilities | `llm_call` records show exactly which models and tools the agent uses |
| Decide not to use the system | `permission_decision` records show risk-based gating with deny capability |
| Intervene or interrupt | `human_override` records document human intervention points |
| Real-time monitoring | Records are written in real-time as events occur |

### 5.3 Cross-Article Traceability

The audit chain provides evidence for multiple articles simultaneously:

| Article | Evidence From Audit Chain |
|---------|--------------------------|
| Art. 9 (Risk Management) | `risk_level` classification on every tool call, `permission_decision` records |
| Art. 10 (Data Governance) | `pii_alerts` showing PII detection, `request_vault_ref` showing data tokenization |
| Art. 11 (Technical Documentation) | Full record schema with version, timestamps, and structured fields |
| Art. 12 (Record-Keeping) | The entire chain, HMAC integrity, tamper detection |
| Art. 14 (Human Oversight) | `human_override` and `permission_decision` records |
| Art. 15 (Cybersecurity) | `injection_alerts`, `injection_score`, `injection_blocked` records |

---

## 6. Evidence Bundle

### 6.1 Bundle Format

The evidence bundle is a signed JSON document that combines all AIR Blackbox data into one auditor-ready package. It is generated by the `air-blackbox export` command.

```json
{
  "air_blackbox_evidence_bundle": {
    "version": "1.0.0",
    "generated_at": "2026-03-13T15:00:00.000Z",
    "generator": "air-blackbox v1.2.6"
  },
  "gateway": {
    "url": "http://localhost:8080",
    "reachable": true,
    "vault_enabled": true,
    "guardrails_enabled": true,
    "signing_key_configured": true
  },
  "compliance": {
    "framework": "EU AI Act",
    "articles_checked": [9, 10, 11, 12, 14, 15],
    "results": "...",
    "summary": {
      "total_checks": 39,
      "passing": 35,
      "warnings": 3,
      "failing": 1
    }
  },
  "aibom": "...",
  "audit_trail": {
    "total_records": 1250,
    "models": {"gpt-4o-mini": 800, "claude-3-5-sonnet": 450},
    "chain_verification": {
      "intact": true,
      "records_verified": 1250,
      "total_records": 1250
    }
  },
  "attestation": {
    "algorithm": "HMAC-SHA256",
    "signature": "a3f2...f9a0",
    "signed_at": "2026-03-13T15:00:00.000Z",
    "verification": "Compute HMAC-SHA256 of the bundle (excluding attestation) with the signing key."
  }
}
```

### 6.2 Bundle Signing

The bundle is signed using HMAC-SHA256 over the complete JSON content (excluding the `attestation` field):

```python
bundle_bytes = json.dumps(bundle_without_attestation, sort_keys=True).encode("utf-8")
signature = hmac.new(key.encode(), bundle_bytes, hashlib.sha256).hexdigest()
```

### 6.3 Bundle Verification

To verify a bundle:

1. Extract and remove the `attestation` field
2. Serialize the remaining bundle with `json.dumps(bundle, sort_keys=True)`
3. Compute `HMAC-SHA256(key, serialized_bundle)`
4. Compare the computed hash to `attestation.signature`

```python
import json
import hmac
import hashlib

def verify_bundle(bundle: dict, signing_key: str) -> bool:
    """Verify an AIR Blackbox evidence bundle signature."""
    attestation = bundle.pop("attestation", None)
    if not attestation:
        return False

    bundle_bytes = json.dumps(bundle, sort_keys=True).encode("utf-8")
    expected = hmac.new(
        signing_key.encode(), bundle_bytes, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, attestation["signature"])
```

---

## 7. Implementation Notes

### 7.1 Python Reference Implementation

The reference implementation is in the `air-blackbox` PyPI package:

```bash
pip install air-blackbox
```

Key modules:

| Module | Purpose |
|--------|---------|
| `air_blackbox.replay.engine` | Chain verification, record loading, filtering |
| `air_blackbox.export.bundle` | Evidence bundle generation and signing |
| `air_blackbox.trust.langchain` | LangChain trust layer (callback handler) |
| `air_blackbox.trust.claude_agent` | Claude Agent SDK trust layer (hooks) |
| `air_blackbox.trust.openai_agents` | OpenAI SDK trust layer (wrapper) |

### 7.2 Storage Backends

The default storage backend writes `.air.json` files to a local directory. The format is designed to be backend-agnostic:

| Backend | Status | Notes |
|---------|--------|-------|
| Local filesystem (`./runs/`) | Supported | Default. One file per record. |
| SQLite | Supported | Via `air_blackbox.compliance.history` for compliance scans |
| S3-compatible object storage | Planned | One object per record, prefix by date |
| PostgreSQL JSONB | Planned | Single table, JSONB column for record content |

Records MUST be stored in a way that preserves insertion order (by timestamp) for chain verification.

### 7.3 Performance Considerations

- Record writing is non-blocking: if a write fails, the agent operation continues normally
- Records are written synchronously to ensure ordering, but the write itself (file I/O) is fast (<1ms typical)
- Chain verification is O(n) in the number of records — verify periodically, not on every write
- For high-throughput systems (>1000 records/second), consider batching records and computing chain hashes in bulk

---

## Appendix A: Complete JSON Schema

The canonical JSON Schema is hosted at:

```
https://airblackbox.ai/spec/audit-record-v1.schema.json
```

See Section 2.4 for the full schema definition.

---

## Appendix B: Annotated Example Chain

A three-record chain demonstrating the linking:

```
Record 0 (LLM call):
  run_id: "aaa-001"
  timestamp: "2026-03-13T14:30:00.000Z"
  type: "llm_call"
  model: "gpt-4o-mini"
  status: "success"
  chain_hash: HMAC-SHA256(key, b"genesis" || JSON(record_0))
              = "a1b2c3..."

Record 1 (Tool call):
  run_id: "aaa-002"
  timestamp: "2026-03-13T14:30:01.000Z"
  type: "tool_call"
  tool_name: "Bash"
  risk_level: "CRITICAL"
  status: "success"
  chain_hash: HMAC-SHA256(key, bytes("a1b2c3...") || JSON(record_1))
              = "d4e5f6..."

Record 2 (Session end):
  run_id: "aaa-003"
  timestamp: "2026-03-13T14:30:05.000Z"
  type: "session_end"
  status: "completed"
  chain_hash: HMAC-SHA256(key, bytes("d4e5f6...") || JSON(record_2))
              = "g7h8i9..."
```

If Record 1 is modified (e.g., changing `risk_level` from `"CRITICAL"` to `"LOW"`), the recomputed hash at Record 1 will differ from `"d4e5f6..."`, and Record 2's hash will also fail verification because it depends on Record 1's hash. This cascading failure is what makes the chain tamper-evident.

---

## Appendix C: Verification Script

A standalone script to verify an audit chain:

```python
#!/usr/bin/env python3
"""Verify an AIR Blackbox audit chain.

Usage:
    python verify_chain.py ./runs --key your-signing-key
    python verify_chain.py ./runs  # uses default key
"""

import argparse
import glob
import hashlib
import hmac
import json
import os
import sys


def load_records(runs_dir: str) -> list[dict]:
    """Load and sort .air.json records by timestamp."""
    records = []
    for fpath in glob.glob(os.path.join(runs_dir, "**/*.air.json"), recursive=True):
        try:
            with open(fpath) as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            print(f"  WARN: Could not read {fpath}", file=sys.stderr)
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def verify(records: list[dict], signing_key: str) -> tuple[bool, int, int]:
    """Verify chain integrity. Returns (intact, verified, total)."""
    key = signing_key.encode("utf-8")
    prev_hash = b"genesis"

    for i, record in enumerate(records):
        record_clean = {k: v for k, v in record.items() if k != "chain_hash"}
        record_bytes = json.dumps(record_clean, sort_keys=True).encode("utf-8")
        expected = hmac.new(key, prev_hash + record_bytes, hashlib.sha256)

        stored = record.get("chain_hash")
        if stored and stored != expected.hexdigest():
            return False, i, len(records)

        prev_hash = expected.digest()

    return True, len(records), len(records)


def main():
    parser = argparse.ArgumentParser(description="Verify AIR Blackbox audit chain")
    parser.add_argument("runs_dir", help="Path to runs directory")
    parser.add_argument("--key", default="air-blackbox-default", help="HMAC signing key")
    args = parser.parse_args()

    records = load_records(args.runs_dir)
    if not records:
        print("No .air.json records found.")
        sys.exit(1)

    print(f"Loaded {len(records)} records from {args.runs_dir}")
    print(f"Date range: {records[0].get('timestamp', '?')} → {records[-1].get('timestamp', '?')}")
    print()

    intact, verified, total = verify(records, args.key)

    if intact:
        print(f"PASS: Chain intact. {verified}/{total} records verified.")
        sys.exit(0)
    else:
        print(f"FAIL: Chain broken at record {verified} of {total}.")
        print(f"  Record: {records[verified].get('run_id', '?')}")
        print(f"  Timestamp: {records[verified].get('timestamp', '?')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-13 | Initial specification. Covers record format, HMAC-SHA256 chaining, 7 entry types, EU AI Act mapping, evidence bundles, verification algorithm. |
