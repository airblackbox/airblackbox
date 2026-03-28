% AIR Blackbox HMAC-SHA256 Audit Chain Specification v1.0
% AIR Blackbox Trust Layer Authors
% 2026-03-28

# AIR Blackbox HMAC-SHA256 Audit Chain Specification

## 1. Abstract

This specification defines the AIR Blackbox Audit Chain format, a tamper-evident, cryptographically signed event log based on HMAC-SHA256 hash chains. The audit chain creates a secure, verifiable record of all agent actions and trust layer decisions. Each record cryptographically links to the previous record, making any tampering, deletion, or reordering of records detectable through chain verification.

The audit chain serves three purposes: (1) compliance evidence for EU AI Act, GDPR, and ISO 42001 audits; (2) tamper detection for forensic investigations; and (3) immutable transaction history for liability protection. This specification is normative; implementations MUST follow all requirements marked MUST, SHOULD, or MAY per RFC 2119.

## 2. Status

Status: **Draft v1.0**

This specification defines the initial audit chain format implemented in AIR Blackbox trust layers. Future versions may add features such as record compression, distributed signing, or hardware security module (HSM) integration, but MUST maintain backward compatibility with v1.0 chains.

## 3. Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

**Audit Chain**: An ordered sequence of cryptographically signed records where each record's signature depends on the previous record's signature.

**Record**: A single JSON object representing an agent action, decision, or event in the audit chain.

**Chain Hash**: The HMAC-SHA256 signature of a record, computed as HMAC(key, previous_hash || JSON(record)).

**Genesis Record**: The first record in a chain, with previous_hash set to the literal string "genesis".

**Signing Key**: A secret key used to compute HMAC signatures. MUST be 32 bytes or longer for production use.

**Tamper Detection**: The ability to identify that a record in the chain has been modified, deleted, or reordered.

**Verification**: The process of recomputing all chain hashes and confirming they match the stored values.

## 4. Chain Structure

### 4.1 Overview

An audit chain is an append-only sequence of records. Each record MUST contain a unique run_id, timestamp, and version. The chain maintains state through the previous_hash field, which links each record to its predecessor.

The first record in the chain (genesis record) has previous_hash set to the literal string "genesis". All subsequent records have previous_hash set to the hex-encoded chain_hash of the immediately preceding record.

The chain_hash for each record is computed deterministically using HMAC-SHA256, making the chain tamper-evident. If any record is modified, reordered, or deleted, verification will detect the inconsistency.

### 4.2 Genesis Record

The genesis record is the first record written to a chain. It MUST have:

- previous_hash: the literal string "genesis" (not a hex value)
- chain_hash: computed as HMAC-SHA256(signing_key, b"genesis" || JSON(record))

Example genesis record:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-28T14:32:00.000Z",
  "version": "1.0.0",
  "framework": "langchain",
  "action": "agent_start",
  "previous_hash": "genesis",
  "chain_hash": "a7f3d8e4b2c6f1a9e5d3c8b4f7e2a1d6c4e8f1a3d5b7c9e2f4a6c8e1b3d5f7"
}
```

### 4.3 Record Format (JSON Schema)

Every record MUST be a JSON object with the following structure:

```json
{
  "run_id": "string (UUID v4, REQUIRED)",
  "timestamp": "string (ISO 8601 UTC, REQUIRED)",
  "version": "string (semver, REQUIRED)",
  "previous_hash": "string (hex or 'genesis', COMPUTED)",
  "chain_hash": "string (hex, COMPUTED)",
  "framework": "string (OPTIONAL)",
  "model": "string (OPTIONAL)",
  "action": "string (OPTIONAL)",
  "tokens": "integer (OPTIONAL)",
  "injection_score": "float 0-1 (OPTIONAL)",
  "pii_detected": "boolean (OPTIONAL)",
  "authorized_by": "string (OPTIONAL)",
  "result": "string (OPTIONAL)",
  "input_context": "string (OPTIONAL)",
  "payload": "object (OPTIONAL)"
}
```

**Required Fields**:

- `run_id` (string): A UUID v4 that uniquely identifies this agent run or session. MUST be present in every record.
- `timestamp` (string): ISO 8601 format with UTC timezone (e.g., "2026-03-28T14:32:00.000Z"). REQUIRED. SHOULD be generated at record creation time.
- `version` (string): Semantic version of the audit chain format (e.g., "1.0.0"). REQUIRED.

**Computed Fields** (MUST be set before storage):

- `previous_hash` (string): For genesis records, the literal string "genesis". For all other records, the hex-encoded chain_hash of the immediately preceding record.
- `chain_hash` (string): The HMAC-SHA256 signature of this record, computed as described in Section 4.4.

**Optional Fields**:

- `framework` (string): The agent framework (e.g., "langchain", "crewai", "autogen", "openai"). OPTIONAL.
- `model` (string): The LLM model identifier (e.g., "claude-3-opus"). OPTIONAL.
- `action` (string): The action type (e.g., "agent_start", "tool_call", "email_send", "database_write"). OPTIONAL.
- `tokens` (integer): Number of tokens consumed. OPTIONAL.
- `injection_score` (float): Prompt injection risk score, range 0.0 to 1.0. OPTIONAL.
- `pii_detected` (boolean): Whether personally identifiable information was detected. OPTIONAL.
- `authorized_by` (string): Human or system that authorized this action (e.g., "policy_auto_allow", "user@example.com"). OPTIONAL.
- `result` (string): Outcome status (e.g., "pending", "approved", "rejected", "blocked", "executed"). OPTIONAL.
- `input_context` (string): The prompt or input that triggered this action. OPTIONAL.
- `payload` (object): The actual data being recorded (e.g., email body, API request, database row). OPTIONAL.

Additional custom fields MAY be added by implementations, but MUST NOT override required or computed fields.

### 4.4 Chain Hash Computation

The chain_hash for a record is computed using HMAC-SHA256 as follows:

1. Sort all fields in the record alphabetically by key (excluding chain_hash itself).
2. Serialize to JSON with no whitespace (canonical form).
3. Compute HMAC-SHA256(signing_key, previous_hash_bytes || record_bytes).
4. Encode the result as hexadecimal (lowercase).

Pseudocode:

```python
import hashlib
import hmac
import json

def compute_chain_hash(signing_key, previous_hash, record):
    # Remove chain_hash field if present
    record_copy = {k: v for k, v in record.items() if k != "chain_hash"}
    
    # Canonical JSON: sorted keys, no whitespace
    record_json = json.dumps(record_copy, sort_keys=True, separators=(",", ":"))
    record_bytes = record_json.encode("utf-8")
    
    # Convert previous_hash to bytes
    if previous_hash == "genesis":
        prev_bytes = b"genesis"
    else:
        prev_bytes = bytes.fromhex(previous_hash)
    
    # HMAC-SHA256
    h = hmac.new(signing_key, prev_bytes + record_bytes, hashlib.sha256)
    return h.hexdigest()
```

### 4.5 Previous Hash Linkage

The previous_hash field creates the chain linkage:

- **Genesis record**: previous_hash is the literal string "genesis" (not a computed value).
- **Subsequent records**: previous_hash is the hex-encoded chain_hash of the preceding record.

This linkage ensures that deleting or reordering records breaks the chain, making tampering detectable during verification.

## 5. Record Fields Reference

### 5.1 Core Fields

**run_id** (UUID v4, REQUIRED)

- Uniquely identifies an agent execution or session
- Format: must be valid UUID v4 (e.g., "550e8400-e29b-41d4-a716-446655440000")
- MUST be present in every record
- Implementations SHOULD generate this field if not provided

**timestamp** (ISO 8601 UTC, REQUIRED)

- Moment when the record was created
- Format: "YYYY-MM-DDTHH:MM:SS.sssZ" (UTC timezone required)
- MUST be in UTC; local times MUST be converted
- SHOULD be generated automatically at write time

**version** (Semantic Version, REQUIRED)

- Audit chain format version (e.g., "1.0.0")
- MUST follow semver rules
- All v1.x implementations MUST be backward compatible with 1.0.0

### 5.2 Computed Fields

**chain_hash** (Hex String, COMPUTED)

- HMAC-SHA256 signature of this record
- Format: lowercase hexadecimal (64 characters for SHA256)
- Computed as: HMAC(key, previous_hash || JSON(record))
- MUST be set before persisting the record
- MUST be verified during chain verification (Section 6)

**previous_hash** (Hex String or "genesis", COMPUTED)

- Links this record to the previous record
- For genesis: the literal string "genesis"
- For all others: the hex-encoded chain_hash of the previous record
- MUST NOT be set by the application; the chain implementation MUST compute it

### 5.3 Optional Context Fields

**framework** (String, OPTIONAL)

- The agent framework in use
- Examples: "langchain", "crewai", "autogen", "openai", "rag"
- Used for audit classification

**model** (String, OPTIONAL)

- The LLM model identifier
- Examples: "claude-3-opus", "gpt-4-turbo", "llama-2-70b"
- Used for compliance reporting

**action** (String, OPTIONAL)

- The action type being recorded
- Examples: "agent_start", "tool_call", "email_send", "database_write", "file_access"
- Used for filtering and analysis

**tokens** (Integer, OPTIONAL)

- Number of tokens consumed or generated
- SHOULD be sum of input and output tokens
- Used for usage tracking and cost analysis

### 5.4 Optional Security Fields

**injection_score** (Float 0.0-1.0, OPTIONAL)

- Prompt injection risk score
- 0.0: no injection detected
- 1.0: high confidence injection attack
- Used to flag potentially malicious inputs

**pii_detected** (Boolean, OPTIONAL)

- Whether personally identifiable information (PII) was detected
- true: PII present (social security number, credit card, etc.)
- false or absent: no PII detected
- Used for GDPR audit trails

### 5.5 Optional Approval/Status Fields

**authorized_by** (String, OPTIONAL)

- Who or what approved this action
- Examples: "policy_auto_allow", "user@example.com", "security_team"
- Used to track authorization chain

**result** (String, OPTIONAL)

- Outcome status
- Values: "pending", "approved", "rejected", "blocked", "executed", "failed"
- Used for action lifecycle tracking

**input_context** (String, OPTIONAL)

- The prompt or input that triggered this action
- Should not contain sensitive data (PII, secrets)
- Used for audit investigation

**payload** (Object, OPTIONAL)

- The actual data being recorded
- Should not contain secrets, API keys, or other sensitive data
- Used for transaction reconstruction

## 6. Chain Verification Algorithm

### 6.1 Verification Overview

Chain verification confirms that no records have been tampered with, deleted, or reordered. The verification process recomputes every chain_hash and compares it to the stored value.

### 6.2 Step-by-Step Verification

```python
def verify_chain(records, signing_key):
    """
    Verify a chain of audit records.
    
    Args:
        records: List of records in order
        signing_key: The HMAC signing key (bytes)
    
    Returns:
        dict with keys:
            valid (bool): True if chain is intact
            events_checked (int): Number of records verified
            errors (list): Any verification failures
    """
    errors = []
    
    if not records:
        return {"valid": True, "events_checked": 0, "errors": []}
    
    # Verify each record
    for i, record in enumerate(records):
        # Check 1: Recompute the chain_hash
        expected_hash = compute_chain_hash(
            signing_key,
            record["previous_hash"],
            record
        )
        if record["chain_hash"] != expected_hash:
            errors.append(
                f"Record {i} ({record['run_id']}): chain_hash mismatch. "
                f"Expected {expected_hash}, got {record['chain_hash']}. "
                f"TAMPERING DETECTED."
            )
        
        # Check 2: Verify previous_hash linkage
        if i == 0:
            # Genesis record must link to "genesis"
            if record["previous_hash"] != "genesis":
                errors.append(
                    f"Record 0 ({record['run_id']}): genesis record must have "
                    f"previous_hash='genesis', got '{record['previous_hash']}'"
                )
        else:
            # All other records must link to the previous record's chain_hash
            expected_prev = records[i - 1]["chain_hash"]
            if record["previous_hash"] != expected_prev:
                errors.append(
                    f"Record {i} ({record['run_id']}): chain broken. "
                    f"previous_hash should be {expected_prev}, got "
                    f"{record['previous_hash']}. "
                    f"Record may have been deleted or reordered."
                )
    
    return {
        "valid": len(errors) == 0,
        "events_checked": len(records),
        "errors": errors
    }
```

### 6.3 Tamper Detection

Tampering is detected when:

1. **Modification**: A record's field is changed. The computed chain_hash will not match the stored value.
2. **Deletion**: A record is removed from the middle of the chain. The next record's previous_hash will not match the preceding record's chain_hash.
3. **Reordering**: Records are placed out of sequence. The previous_hash linkage will break.
4. **Insertion**: A new record is inserted out of order. The following record's previous_hash will not match.

All tampering is immediately detectable because previous_hash values create an unbreakable dependency chain.

### 6.4 Error Handling

If verification fails:

1. Log all errors for audit investigation
2. Do NOT trust the chain or use records for decisions
3. Escalate to security team
4. Do NOT attempt to repair the chain automatically
5. Preserve the corrupted chain as evidence

## 7. Storage Backends

### 7.1 JSONL (JSON Lines)

JSONL is a simple, human-readable format where each record is a complete JSON object on a single line.

**Format**:
```
{"run_id":"...", "timestamp":"...", ...}\n
{"run_id":"...", "timestamp":"...", ...}\n
```

**Advantages**:
- Human-readable for debugging
- Simple append-only writes
- Works with standard Unix tools

**Disadvantages**:
- Slower to load (O(n) scan required)
- No indexing
- Entire file must be parsed to verify

**File extension**: `.jsonl`

### 7.2 SQLite

SQLite provides indexed, queryable storage with better performance for large chains.

**Schema**:
```sql
CREATE TABLE events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    version TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    chain_hash TEXT NOT NULL,
    framework TEXT,
    model TEXT,
    action TEXT,
    tokens INTEGER,
    injection_score REAL,
    pii_detected BOOLEAN,
    authorized_by TEXT,
    result TEXT,
    input_context TEXT,
    payload TEXT
);

CREATE INDEX idx_run_id ON events(run_id);
CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_action ON events(action);
CREATE INDEX idx_result ON events(result);
```

**Advantages**:
- Fast queries and indexing
- Supports concurrent reads
- Built-in integrity constraints
- No external dependencies

**Disadvantages**:
- Requires SQLite driver
- Schema migration needed for extensions
- Less human-readable than JSONL

**File extension**: `.db`

### 7.3 Individual .air.json Files

Records can also be stored as individual JSON files in a directory structure.

**Naming**: Each record is stored as `{run_id}.air.json`

**Directory structure**:
```
runs/
  550e8400-e29b-41d4-a716-446655440000.air.json
  550e8400-e29b-41d4-a716-446655440001.air.json
  550e8400-e29b-41d4-a716-446655440002.air.json
```

**Advantages**:
- Decentralized, each record is independent
- Works with version control (Git)
- Can be archived or compressed individually

**Disadvantages**:
- Slow to verify (filesystem I/O per record)
- No indexing
- Directory scaling issues with millions of records

## 8. Signing Key Management

### 8.1 Key Derivation

The signing key MUST be at least 32 bytes (256 bits). Implementations SHOULD use one of:

1. **Direct key**: A 32-byte random value (generated by `secrets.token_bytes(32)` in Python)
2. **Key derivation**: PBKDF2-SHA256 from a passphrase (at least 100,000 iterations)
3. **Key from environment**: The environment variable `TRUST_SIGNING_KEY` (RECOMMENDED for deployment)

Implementations MUST NOT use short passphrases, hardcoded keys, or md5/sha1 derived keys.

### 8.2 Key Rotation Procedure

To rotate keys (e.g., after key compromise):

1. Generate a new signing key
2. Read all existing records from the old chain
3. Recompute all chain_hash values using the new signing key
4. Write the recomputed chain to a new storage location
5. Verify the new chain with the new key
6. Retire the old chain to archive storage
7. Update the application to use the new key

**Important**: Key rotation invalidates all old chain_hash values. This is acceptable for updating compromised keys, but SHOULD NOT be done frequently.

### 8.3 Environment Variable

Implementations SHOULD read the signing key from the environment variable `TRUST_SIGNING_KEY`:

```python
signing_key = os.environ.get(
    "TRUST_SIGNING_KEY",
    "air-blackbox-default"  # Development default only
)
```

The default value MUST NOT be used in production. In production, `TRUST_SIGNING_KEY` MUST be set to a strong, random value.

## 9. Security Considerations

### 9.1 What the Chain Protects Against

The audit chain provides cryptographic protection against:

1. **Tampering**: Modifying any field in any record invalidates all subsequent chain_hash values
2. **Deletion**: Removing a record breaks the linkage for all following records
3. **Reordering**: Moving records out of sequence causes previous_hash mismatches
4. **Undetectable modification**: The chain_hash computation includes all record fields; no tampering goes undetected

### 9.2 What the Chain Does NOT Protect Against

The audit chain does NOT protect against:

1. **Key compromise**: If the signing key is exposed, an attacker can forge chain_hash values for new records
2. **Implementation bugs**: Software bugs in the chain implementation could allow bypassing the chain
3. **Storage backend compromise**: An attacker with direct database or filesystem access can modify records and their hashes
4. **Denial of service**: The chain can be truncated (records deleted) without triggering integrity checks
5. **Selective disclosure**: The chain cannot prevent hiding records that were created but not persisted

### 9.3 Recommendations for Production

1. **Signing Key Management**:
   - Store the signing key in a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Rotate keys annually
   - Never commit keys to version control
   - Use separate keys for different environments (dev, staging, production)

2. **Storage Security**:
   - Store chains in a write-once or append-only storage system
   - Enable file integrity monitoring (tripwire, AIDE)
   - Use encrypted storage with transparent encryption (dm-crypt, AWS KMS)
   - Implement role-based access control (RBAC) to limit who can read chains

3. **Verification**:
   - Verify the entire chain at application startup
   - Perform periodic verification (daily or weekly)
   - Log verification results for audit purposes
   - Alert on verification failures

4. **Archival**:
   - Archive chains to immutable storage (S3 with versioning, Glacier, tape)
   - Sign archived chains separately to prove they were not modified after archival
   - Maintain chain integrity across long-term storage

## 10. Compliance Mapping

### 10.1 EU AI Act Article 12: Record-Keeping

Article 12 requires that high-risk AI systems maintain records of operation. The audit chain satisfies this by:

- Recording all agent actions with timestamps and outcomes
- Creating tamper-evident records that cannot be modified after creation
- Maintaining a complete trace of decision-making
- Enabling auditor verification of chain integrity

**Specification compliance**: Section 6 (verification) enables auditors to confirm records are intact and unaltered.

### 10.2 GDPR Article 30: Records of Processing

Article 30 requires organizations to maintain records of processing activities. The audit chain assists by:

- Recording the data being processed (via the payload field)
- Tracking authorization and approvals (authorized_by field)
- Maintaining action history (action field)
- Creating immutable evidence of processing

**Specification compliance**: Section 5 (fields) includes optional fields for tracking data handling and authorization.

### 10.3 ISO 42001: AI Management System

ISO 42001 requires documented AI system operations and change tracking. The audit chain provides:

- Model and framework tracking (model, framework fields)
- Token usage records (tokens field)
- Action classification (action field)
- Chain verification for integrity assurance

**Specification compliance**: Optional fields in Section 5 enable operational monitoring per ISO 42001.

## 11. Examples

### 11.1 Example Genesis Record

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-28T14:32:00.000Z",
  "version": "1.0.0",
  "framework": "langchain",
  "model": "claude-3-opus",
  "action": "agent_start",
  "previous_hash": "genesis",
  "chain_hash": "a7f3d8e4b2c6f1a9e5d3c8b4f7e2a1d6c4e8f1a3d5b7c9e2f4a6c8e1b3d5f7"
}
```

**chain_hash computation** (pseudocode):
```
signing_key = b"test-secret-key-32-bytes-minimum"
record_json = '{"action":"agent_start","framework":"langchain","model":"claude-3-opus","previous_hash":"genesis","run_id":"550e8400-e29b-41d4-a716-446655440000","timestamp":"2026-03-28T14:32:00.000Z","version":"1.0.0"}'
record_bytes = record_json.encode("utf-8")
previous_hash_bytes = b"genesis"
h = HMAC-SHA256(signing_key, previous_hash_bytes + record_bytes)
chain_hash = h.hexdigest()
```

### 11.2 Example Chain of 3 Records

**Record 1 (Genesis)**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-28T14:32:00.000Z",
  "version": "1.0.0",
  "action": "agent_start",
  "previous_hash": "genesis",
  "chain_hash": "aaaa000000000000000000000000000000000000000000000000000000000001"
}
```

**Record 2**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-28T14:32:05.000Z",
  "version": "1.0.0",
  "action": "tool_call",
  "tool_name": "send_email",
  "tokens": 150,
  "previous_hash": "aaaa000000000000000000000000000000000000000000000000000000000001",
  "chain_hash": "bbbb000000000000000000000000000000000000000000000000000000000002"
}
```

**Record 3**:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-28T14:32:10.000Z",
  "version": "1.0.0",
  "action": "agent_complete",
  "result": "success",
  "tokens": 200,
  "previous_hash": "bbbb000000000000000000000000000000000000000000000000000000000002",
  "chain_hash": "cccc000000000000000000000000000000000000000000000000000000000003"
}
```

**Chain linkage**:
- Record 2 links to Record 1: previous_hash = "aaaa...001"
- Record 3 links to Record 2: previous_hash = "bbbb...002"
- If Record 2 is modified, its chain_hash changes, breaking Record 3's linkage

### 11.3 Example Verification Code in Python

```python
import hashlib
import hmac
import json
from typing import List, Dict, Any

def compute_chain_hash(
    signing_key: bytes,
    previous_hash: str,
    record: Dict[str, Any]
) -> str:
    """Compute HMAC-SHA256 chain hash for a record."""
    record_copy = {k: v for k, v in record.items() if k != "chain_hash"}
    record_json = json.dumps(record_copy, sort_keys=True, separators=(",", ":"))
    record_bytes = record_json.encode("utf-8")
    
    if previous_hash == "genesis":
        prev_bytes = b"genesis"
    else:
        prev_bytes = bytes.fromhex(previous_hash)
    
    h = hmac.new(signing_key, prev_bytes + record_bytes, hashlib.sha256)
    return h.hexdigest()


def verify_chain(
    records: List[Dict[str, Any]],
    signing_key: bytes
) -> Dict[str, Any]:
    """Verify the integrity of an audit chain."""
    errors = []
    
    if not records:
        return {"valid": True, "events_checked": 0, "errors": []}
    
    for i, record in enumerate(records):
        # Recompute chain hash
        expected_hash = compute_chain_hash(
            signing_key,
            record["previous_hash"],
            record
        )
        
        if record.get("chain_hash") != expected_hash:
            errors.append(
                f"Record {i}: chain_hash mismatch. "
                f"Expected {expected_hash}, got {record.get('chain_hash')}. "
                f"TAMPERING DETECTED."
            )
        
        # Verify linkage
        if i == 0:
            if record.get("previous_hash") != "genesis":
                errors.append(
                    f"Record 0: genesis record must have previous_hash='genesis'"
                )
        else:
            expected_prev = records[i - 1]["chain_hash"]
            if record.get("previous_hash") != expected_prev:
                errors.append(
                    f"Record {i}: chain broken. "
                    f"Expected previous_hash={expected_prev}, "
                    f"got {record.get('previous_hash')}"
                )
    
    return {
        "valid": len(errors) == 0,
        "events_checked": len(records),
        "errors": errors
    }


# Usage example
if __name__ == "__main__":
    signing_key = b"test-secret-key-32-bytes-minimum"
    
    # Load records from JSONL
    records = []
    with open("chain.jsonl", "r") as f:
        for line in f:
            records.append(json.loads(line))
    
    # Verify
    result = verify_chain(records, signing_key)
    if result["valid"]:
        print(f"Chain verified: {result['events_checked']} records intact")
    else:
        print("Chain verification FAILED:")
        for error in result["errors"]:
            print(f"  - {error}")
```

## 12. Implementation Notes

### 12.1 Canonical JSON

To ensure deterministic chain_hash computation:

1. Sort all keys alphabetically
2. Use compact formatting (no spaces or newlines)
3. Use Unix line endings (LF, not CRLF)
4. Encode UTF-8
5. Never include the chain_hash field in the computation

### 12.2 Timestamp Precision

Use ISO 8601 format with millisecond precision and UTC timezone:

**Correct**: `"2026-03-28T14:32:00.000Z"`

**Incorrect**: `"2026-03-28T14:32:00"` (missing timezone)

**Incorrect**: `"2026-03-28T14:32:00-07:00"` (local timezone; must convert to UTC)

### 12.3 Thread Safety

Applications writing to the audit chain from multiple threads MUST use a lock:

```python
import threading

class AuditChain:
    def __init__(self, signing_key):
        self._lock = threading.Lock()
        self._prev_hash = b"genesis"
    
    def write(self, record):
        with self._lock:
            # Compute and write atomically
            record["chain_hash"] = compute_chain_hash(
                self._signing_key,
                self._prev_hash.hex() if self._prev_hash != b"genesis" else "genesis",
                record
            )
            self._persist(record)
            self._prev_hash = bytes.fromhex(record["chain_hash"])
```

---

**End of Specification**

Document version: 1.0.0
Last updated: 2026-03-28
Status: Draft
