# Cryptographic Proof of Agent-to-Agent Handoffs in Python

**Tags:** #ai #python #opensource #euaiact

---

When your AI pipeline hands off from one agent to another, how do you prove it happened?

Not "there's a log entry." Prove it. Cryptographically. In a way that holds up when someone asks: *which agent made this decision, and did it actually receive the data it claimed to receive?*

That's what I shipped this week in [air-trust v0.6.1](https://github.com/airblackbox/air-trust): Ed25519 signed handoffs for multi-agent Python systems.

---

## The Problem

Multi-agent pipelines are becoming the default architecture for serious AI work. A research agent gathers context, hands off to a writer agent, which hands off to a fact-checker, which hands off to a publisher. Each agent does a piece of the work.

But when something goes wrong — or when a regulator asks for an audit trail — you have a problem. Your logs show *what* happened. They don't prove *who* did it or that the data wasn't modified in transit.

Three specific failure modes that are genuinely hard to detect today:

1. **Payload tampering**: Agent A says it handed off document X. Agent B received document X. But was it the same X? Without a hash comparison locked in at handoff time, you can't know.
2. **Identity spoofing**: An agent claims to be "research-bot." Is it? If agents communicate over any shared message bus, impersonation is trivial.
3. **Silent unsigned records**: You think your audit chain has signatures. It doesn't — the signing key was missing and the library failed silently. (This was actually a bug in air-trust v0.6.0 that we fixed in v0.6.1.)

The EU AI Act's Article 12 requires high-risk AI systems to maintain logs "sufficient to ensure traceability." Unsigned JSON files don't meet that bar for systems making consequential decisions.

---

## The Solution: Three Record Types + Ed25519 Keys

`air-trust` adds three new event types to its audit chain:

- **`handoff_request`** — Agent A says "I want to hand off to Agent B with this payload"
- **`handoff_ack`** — Agent B acknowledges receipt
- **`handoff_result`** — Agent B reports back what it produced

Each record is automatically signed with the agent's Ed25519 private key. The verifier checks all three: valid signatures, matching counterparties, payload hash integrity, and nonce uniqueness (to prevent replay attacks).

### Install

```bash
pip install "air-trust[handoffs]"
```

The `[handoffs]` extra pulls in the `cryptography` library for Ed25519 support. The core audit chain has no external dependencies.

### Generate keypairs for each agent

```bash
python3 -m air_trust keygen --agent research-bot
python3 -m air_trust keygen --agent writer-bot
```

Keys are stored at `~/.air-trust/keys/` with `0600` permissions.

### Instrument the handoff

```python
import air_trust
from air_trust import trust, session, AuditChain

# Research agent side
chain = AuditChain()
air_trust.trust(identity=air_trust.AgentIdentity(
    agent_id="research-bot",
    fingerprint="research-bot"
))

with session(chain):
    # ... do research work ...

    iid = chain.handoff_request(
        counterparty_id="writer-bot",
        payload={"summary": research_summary},
    )

# Writer agent side (separate process, same or different machine)
air_trust.trust(identity=air_trust.AgentIdentity(
    agent_id="writer-bot",
    fingerprint="writer-bot"
))

with session(chain):
    chain.handoff_ack(
        interaction_id=iid,
        counterparty_id="research-bot",
    )

    # ... do writing work ...

    chain.handoff_result(
        interaction_id=iid,
        counterparty_id="research-bot",
        payload={"article": finished_article},
    )
```

### Verify the chain

```bash
python3 -m air_trust verify audit_chain.jsonl
```

Output:

```
INTEGRITY     PASS  47 events, 47 valid HMAC links
COMPLETENESS  PASS  2 sessions complete, no gaps
HANDOFFS      PASS  1 interaction verified

  interaction abc123:
    request   PASS  Ed25519 OK (research-bot)
    ack       PASS  Ed25519 OK (writer-bot)
    result    PASS  Ed25519 OK (writer-bot)
    payload   PASS  SHA-256 hash match
    nonce     PASS  unique
```

If someone tampers with the payload between request and result:

```
HANDOFFS      FAIL  1 interaction failed

  interaction abc123:
    result    FAIL  payload hash mismatch
              expected: a3f2c1...
              got:      9d4e8b...
```

---

## How It Works Under the Hood

### The signing payload

Every signed record commits to six fields, pipe-delimited:

```
interaction_id|counterparty_id|payload_hash|nonce|type|timestamp
```

The `payload_hash` is SHA-256 of the JSON-serialized payload. This means:

1. The signature covers the payload content, not just the record metadata
2. Payload mutation is detectable even if the signature itself isn't forged
3. The nonce prevents an attacker from replaying a valid old record

### Ed25519 vs. HMAC

The tamper-evident chain (spec v1.0) uses HMAC-SHA256 with a shared secret — this catches post-hoc modification of stored records. But HMAC is symmetric: anyone with the secret key can forge a record.

Signed handoffs (spec v1.2) use Ed25519 asymmetric keys. The private key never leaves the agent. The public key is embedded in every signed record. This means:

- **Non-repudiation**: agent A can prove it signed the request, and nobody else can produce that signature
- **No shared secret**: agents don't need to trust each other's key management
- **Public key in the record**: verifiers don't need a key registry — the public key is self-contained in the audit log

### The audit chain is layered

```
v1.0  HMAC chain        — tamper detection for all records
v1.1  Session sequences — completeness: no gaps, no replays within a session
v1.2  Signed handoffs   — identity proof at agent boundaries
```

Each layer is backward compatible. A v1.0 chain verifies clean under v1.2. A v1.2 chain with no handoffs still passes.

---

## What We Fixed in v0.6.1

The silent failure modes I mentioned earlier were real bugs in v0.6.0, caught during a design review after shipping:

**Bug 1 — Signed records written without signatures**: If the `cryptography` package wasn't installed, handoff records were written silently without signatures. The verifier then silently skipped them. The chain appeared to verify clean. It now raises `ImportError` at write time instead.

**Bug 2 — Verifier skipped unsigned records**: Even with the library installed, if an agent had no keypair, records were written unsigned and the verifier skipped checking them. It now flags these as `missing_signature` with severity `warn`.

**Bug 3 — Session ID leaked on exception**: If a `session()` block raised, the ContextVar holding the session ID wasn't reset, so the next session wrote events with the wrong session ID. Fixed with a `finally` block.

**Bug 4 — Thread safety**: The global chain and identity singletons weren't protected by a lock. In threaded code (common with agent frameworks), you could get cross-thread identity clobbering. Fixed with `threading.Lock()`.

I'm documenting these because they're the kind of bugs that would be catastrophic in a compliance context — you think you have signed records, you don't. Soundness matters more than features here.

---

## What This Is (and Isn't)

This is a **technical audit layer**, not a legal compliance certification. `air-trust` helps you answer: *did these agents interact in the way the logs claim, and is the data intact?* It doesn't answer whether your system meets every requirement of the EU AI Act — that's a legal question involving risk classification, conformity assessments, and a lot more.

Think of it as a linter for your audit chain. Fast, local, no cloud, no API keys. It either passes or it tells you exactly what's wrong.

---

## Try It

```bash
pip install "air-trust[handoffs]"
python3 -m air_trust keygen --agent my-agent
python3 examples/signed_handoff.py  # in the repo
python3 -m air_trust verify audit_chain.jsonl
```

Interactive demo (no install): [airblackbox.ai/demo/signed-handoff](https://airblackbox.ai/demo/signed-handoff)

GitHub: [github.com/airblackbox/air-trust](https://github.com/airblackbox/air-trust)

---

## What's Next

The roadmap has two items queued for Phase 3:

- **Remote verification endpoint** — post a chain to a verifier service and get a signed attestation back (useful for third-party audits)
- **Framework trust layers** — drop-in `air_trust` wrappers for LangChain, CrewAI, and AutoGen that auto-instrument handoffs with zero code changes

If you're building multi-agent systems and care about auditability, I'd genuinely like to know what your current setup looks like. Comments open.
