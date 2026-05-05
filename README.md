# air-trust

Tamper-evident audit chain for Python AI agents. HMAC-SHA256 integrity, framework-native hooks, zero infrastructure.

```
pip install air-trust
```

## The problem

Your agent makes decisions, calls tools, and produces outputs. If something goes wrong (or a regulator asks), you need to prove what happened, when, and that nobody altered the record after the fact.

Logging is not enough. Anyone with write access to your log store can edit a record. HMAC chains make alteration detectable - modify one record and every record after it breaks.

## How it works

```python
from air_trust import AuditChain

chain = AuditChain(signing_key="your-secret")

# Every call to .write() produces a chained .air.json record
chain.write({
    "run_id": "agent-run-001",
    "action": "tool_call",
    "tool": "search_database",
    "input": {"query": "customer records"},
    "output": {"results": 42},
})
```

Each record contains an HMAC-SHA256 hash computed over the previous hash + current record. The chain is append-only and tamper-evident by construction.

Records are written to `./runs/` as `.air.json` files. Async, non-blocking - your agent never waits on the audit layer.

## Framework trust layers

Drop-in wrappers that produce the same audit chain from inside your framework's execution loop. No proxy. No infrastructure. Just import and attach.

```python
# LangChain
from air_trust.langchain import AirLangChainHandler
chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})

# CrewAI
from air_trust.crewai import AirCrewAIHandler
crew = Crew(agents=[...], callbacks=[AirCrewAIHandler()])

# OpenAI Agents SDK
from air_trust.openai_agents import AirOpenAIHandler

# AutoGen
from air_trust.autogen import AirAutoGenHandler

# Google ADK
from air_trust.adk import AirADKHandler

# Haystack
from air_trust.haystack import AirHaystackHandler
```

Each trust layer captures: prompts, completions, tool calls, intermediate reasoning, token counts, latency, and error states. All written to the same HMAC chain.

## What you get

**Tamper-evident records** - HMAC-SHA256 chain where each record's hash depends on the previous. Alter one record, every subsequent hash breaks.

**Complete episode capture** - not just inputs and outputs but tool calls, intermediate steps, and framework-specific execution context.

**Non-blocking writes** - audit records write asynchronously. Your agent's latency is unaffected.

**Local-first** - records write to disk. No cloud service, no external dependency, no data leaving your machine.

**Evidence export** - package your audit chain into a self-verifying `.air-evidence` ZIP that an auditor can validate with one command (`python verify.py`).

## Verifying the chain

```python
from air_trust import verify_chain

result = verify_chain("./runs/", signing_key="your-secret")
print(result)
# ChainVerification(valid=True, records=847, first="2026-01-15T...", last="2026-05-04T...")
```

If any record has been modified, `valid=False` and the broken link is identified.

## Evidence bundles

Package your audit chain for a regulator or auditor:

```bash
air-trust export --runs ./runs --output audit-2026-Q1.air-evidence
```

The `.air-evidence` ZIP contains:
- All `.air.json` records
- Chain integrity manifest (SHA-256 per file)
- ML-DSA-65 signature (quantum-safe, FIPS 204)
- `verify.py` - standalone verification script, no pip install needed on the auditor's machine

## When to use air-trust vs air-blackbox

| | air-trust | air-blackbox |
|---|---|---|
| **Purpose** | Record and prove what happened | Scan code for compliance gaps |
| **When** | Runtime (while your agent runs) | Build time (before you deploy) |
| **Output** | Signed audit chain + evidence bundles | Gap analysis report + remediation |
| **Install** | `pip install air-trust` | `pip install air-blackbox` |

Use both: air-blackbox scans your code for gaps, air-trust records what happens in production.

## EU AI Act relevance

Article 12 requires "automatic recording of events" that is tamper-evident and retained for the system's lifetime. air-trust satisfies the technical requirement. Combined with air-blackbox scans, you cover Articles 9-15.

## Configuration

```python
chain = AuditChain(
    runs_dir="./runs",           # where records write (default: ./runs)
    signing_key="your-secret",   # HMAC key (or set TRUST_SIGNING_KEY env var)
)
```

Environment variables:
- `TRUST_SIGNING_KEY` - HMAC signing key (fallback if not passed to constructor)
- `AIR_TRUST_RUNS_DIR` - override default runs directory

## License

Apache-2.0

---

Part of the [AIR Blackbox](https://airblackbox.ai) ecosystem. If this helps you build auditable AI agents, [star the repo](https://github.com/airblackbox/air-trust).
