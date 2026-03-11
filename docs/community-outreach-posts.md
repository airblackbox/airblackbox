# GitHub Community Outreach — Ready to Post

---

## 1. Microsoft Agent Framework (Discussions)

**Title:** EU AI Act compliance plugin for Agent Framework — audit trails, PII detection, runtime validation

**Body:**

Hi team 👋

Built an EU AI Act compliance layer that works with Agent Framework's middleware/plugin system. Sharing it here for feedback — the August 2, 2026 high-risk deadline is approaching and teams deploying agents in EU markets will need to demonstrate compliance.

**What it does:**

- Tamper-evident HMAC-SHA256 audit logging across agent lifecycle callbacks
- PII detection and optional blocking/redaction in prompts and outputs
- Prompt injection scanning (7 patterns)
- Pre-execution runtime validation — validates tool call arguments against schemas, content policies, and approved tool lists BEFORE execution
- EU AI Act compliance checks mapped to Articles 9-15 (20 checks, ~90% auto-detected)
- CycloneDX 1.6 AI-BOM generation from observed traffic
- Signed evidence bundles for auditors

**Design philosophy:**

Composable with the agent lifecycle, not a hidden orchestration layer. Callbacks observe and log — they don't control. Non-blocking by contract: if logging fails, your agent keeps running. Same guarantee as OTel collectors.

**Quick start:**

```bash
pip install air-blackbox
air-blackbox demo
air-blackbox comply -v
```

**Runtime validation (new):**

```python
from air_blackbox.validate import RuntimeValidator, ToolAllowlistRule

validator = RuntimeValidator()
validator.add_rule(ToolAllowlistRule(["web_search", "calculator"]))

report = validator.validate({
    "tool_name": "db_query",
    "arguments": {"query": "SELECT * FROM users"}
})

if report.passed:
    execute_tool(...)
else:
    handle_blocked(report)
```

Evidence bundles prove both what happened (audit chain) AND what was validated before execution (runtime certification). Auditors get one JSON file with compliance scan + AI-BOM + audit trail + HMAC attestation.

Agent Framework's built-in OTel integration is a natural fit — we emit OpenTelemetry-compatible spans alongside the .air.json records.

GitHub: https://github.com/airblackbox/gateway
PyPI: https://pypi.org/project/air-blackbox/

Open source, Apache 2.0. Looking for feedback on how this maps to the middleware pipeline and what Agent Framework-specific hooks would be most useful.

---

## 2. AutoGen (Discussions)

**Title:** EU AI Act compliance for multi-agent systems — audit trails that trace decisions across agents

**Body:**

Hi AutoGen community 👋

Multi-agent systems have a unique compliance challenge: when Agent A delegates to Agent B which calls a tool that affects production data, the audit trail needs to trace the full decision chain, not just individual LLM calls.

Built AIR Blackbox to handle this. It's an open-source EU AI Act compliance layer — 5 commands:

```bash
pip install air-blackbox

air-blackbox comply      # 20 EU AI Act checks (Articles 9-15), 90% auto-detected
air-blackbox discover    # AI-BOM + shadow AI detection
air-blackbox replay      # Incident reconstruction across agent calls
air-blackbox validate    # Pre-execution runtime validation
air-blackbox export      # Signed evidence bundle for auditors
```

**Why multi-agent matters for compliance:**

- Article 12 (Record-Keeping): Need to trace decisions across agent boundaries, not just per-agent logs
- Article 14 (Human Oversight): Auditors ask "at which point in the chain could a human have intervened?"
- Article 15 (Robustness): Injection in one agent's context can cascade through the hierarchy

**What it does:**

- HMAC-SHA256 tamper-evident audit chain across all agent interactions
- PII detection before data crosses agent boundaries
- Runtime validation — check tool call arguments before execution
- CycloneDX AI-BOM showing every model and tool across the agent graph
- Replay engine: reconstruct exactly what happened in a multi-agent run

**Design:**

Non-blocking callbacks. If logging fails, your agents keep running. The trust layer observes — it never orchestrates. Same overhead profile as OTel collectors.

GitHub: https://github.com/airblackbox/gateway
PyPI: https://pypi.org/project/air-blackbox/

Apache 2.0. Looking for feedback — especially on how to best hook into AutoGen's conversational patterns and agent handoff points. Episode grouping (linking related calls across agents into one traceable unit) is the next feature we're building, and AutoGen's multi-agent patterns are the target use case.

---

## 3. Composio (Discussions)

**Title:** EU AI Act compliance for tool orchestration — audit + validate tool calls before execution

**Body:**

Hi Composio team 👋

Composio powers 1000+ toolkits, which makes tool call governance especially relevant — when an agent has access to hundreds of tools with real-world side effects, auditing what was called and validating before execution becomes critical for EU AI Act compliance.

Built AIR Blackbox to handle this:

```bash
pip install air-blackbox
air-blackbox validate --tool=db_query --args='{"query":"SELECT * FROM users"}' --allowlist=web_search,calculator
```

That command validates a tool call BEFORE execution against 5 rules: tool allowlist, schema validation, content policy (blocks DROP TABLE, rm -rf, eval), PII output check, and hallucination guard. If it fails, the action is blocked and logged.

**What it does for tool-heavy agents:**

- **Tool allowlists** — define which tools are approved, block everything else
- **Schema validation** — validate tool arguments against expected types before execution
- **Content policy** — scan tool inputs for dangerous patterns (SQL injection, shell commands)
- **Audit trail** — every tool call logged with HMAC-SHA256 tamper-evident chain
- **AI-BOM** — inventory every model, provider, and tool from observed traffic (CycloneDX 1.6)
- **Shadow AI detection** — flag unapproved models or providers
- **Signed evidence bundles** — one JSON file for auditors: compliance scan + AI-BOM + audit trail + HMAC attestation

The compliance engine runs 20 checks across EU AI Act Articles 9-15, with ~90% auto-detected from observed traffic.

Non-blocking. If logging or validation fails, your agent keeps running. The trust layer observes and validates — it never orchestrates.

GitHub: https://github.com/airblackbox/gateway
PyPI: https://pypi.org/project/air-blackbox/

Apache 2.0. Looking for feedback on how to best integrate with Composio's tool execution pipeline — especially the MCP server patterns.

---

## 4. PraisonAI (Discussions)

**Title:** EU AI Act compliance layer for PraisonAI multi-agent workflows

**Body:**

Hi PraisonAI community 👋

PraisonAI's focus on production-ready multi-agent systems makes EU AI Act compliance especially relevant — the August 2, 2026 high-risk deadline is coming and teams deploying agents in EU markets need audit trails, compliance checks, and evidence bundles.

Built AIR Blackbox — an open-source compliance control plane:

```bash
pip install air-blackbox
air-blackbox demo        # Zero-config demo, 30 seconds
air-blackbox comply -v   # 20 EU AI Act checks, Articles 9-15
air-blackbox discover    # AI-BOM + shadow AI detection
air-blackbox validate    # Pre-execution runtime validation
air-blackbox export      # Signed evidence bundle for auditors
```

**Key features:**

- 20 compliance checks mapped to EU AI Act Articles 9-15 (~90% auto-detected from live traffic)
- HMAC-SHA256 tamper-evident audit chain
- Runtime validation: checks tool call outputs BEFORE execution (tool allowlists, schema validation, content policy, PII check, hallucination guard)
- CycloneDX 1.6 AI-BOM from observed traffic
- PII detection + prompt injection scanning
- Non-blocking: if logging fails, your agents keep running

**Trust layers available for:**

```bash
pip install "air-blackbox[langchain]"    # LangChain / LangGraph
pip install "air-blackbox[openai]"       # OpenAI SDK
pip install "air-blackbox[all]"          # Everything
```

GitHub: https://github.com/airblackbox/gateway
PyPI: https://pypi.org/project/air-blackbox/

Apache 2.0. Would love feedback on how to best hook into PraisonAI's agent lifecycle and task workflow patterns.

---

## TIER 2 — eu-ai-act GitHub Topic

Make sure the gateway repo appears under github.com/topics/eu-ai-act.

The topic `eu-ai-act` is already added to the gateway repo. Verified.

---

## TIER 3 — Compliance/Governance Adjacent

### 5. COMPL-AI (compl-ai/compl-ai) — Issue or Discussion

**Title:** Complementary tooling — runtime compliance checks + COMPL-AI benchmarks

**Body:**

Hi COMPL-AI team 👋

Great work on the evaluation framework — mapping EU AI Act principles to benchmarks is exactly the right approach for model-level compliance.

Wanted to flag a complementary project: AIR Blackbox (https://github.com/airblackbox/gateway) handles runtime/deployment-level compliance — the controls that apply when AI systems are operating in production, not when models are being evaluated.

Where COMPL-AI checks "does this model meet fairness/robustness benchmarks?" — AIR Blackbox checks "is this deployed system logging decisions, detecting PII, validating outputs, and maintaining tamper-proof audit trails?"

The two layers map to different parts of the EU AI Act:
- COMPL-AI → model evaluation (Articles 9, 10, 15 at the model level)
- AIR Blackbox → runtime controls (Articles 11, 12, 14, 15 at the deployment level)

There might be an interesting integration: COMPL-AI benchmark results could feed into AIR Blackbox's evidence bundles, giving auditors both model evaluation AND runtime compliance in one package.

GitHub: https://github.com/airblackbox/gateway
PyPI: `pip install air-blackbox`

Apache 2.0. Happy to explore how these could work together.

---

### 6. Attestix — Issue or Discussion

**Title:** Complementary tooling — AIR Blackbox audit trails + Attestix attestation infrastructure

**Body:**

Hi Attestix team 👋

Interesting project — DID-based agent identity + W3C Verifiable Credentials for AI agents is a natural complement to what we're building with AIR Blackbox.

AIR Blackbox handles the runtime compliance layer: HMAC-SHA256 tamper-evident audit chains, EU AI Act compliance checks (Articles 9-15), CycloneDX AI-BOM, pre-execution runtime validation, and signed evidence bundles.

Where AIR Blackbox proves "what happened and what was validated" — Attestix could prove "who the agent is and what credentials it holds."

Potential integration: AIR Blackbox evidence bundles signed with Attestix DIDs and issued as Verifiable Credentials. An auditor would get: agent identity (Attestix) + runtime compliance evidence (AIR Blackbox) in one verifiable package.

GitHub: https://github.com/airblackbox/gateway
PyPI: `pip install air-blackbox`

Apache 2.0. Would be interested in exploring how delegation chains and reputation scoring could map to our audit trail data.

---

### 7. ark-forge/mcp-eu-ai-act — Issue or Discussion

**Title:** Complementary MCP tooling — runtime compliance + static analysis

**Body:**

Hi 👋

Nice MCP-based approach to EU AI Act compliance scanning. We built something complementary: AIR Blackbox (https://github.com/airblackbox/gateway) handles runtime compliance — what happens when the system is actually running, not just at scan time.

Your tool does static analysis: scan codebases for AI framework usage, check compliance against requirements. Our tool does runtime analysis: observe live AI traffic, log decisions with HMAC chains, validate outputs before execution, generate AI-BOMs from observed traffic.

The two approaches cover different phases:
- **ark-forge/mcp-eu-ai-act** → "Does this codebase have the right structure for compliance?"
- **AIR Blackbox** → "Is this running system actually producing compliant behavior?"

We also have an MCP server: https://github.com/airblackbox/air-blackbox-mcp

Might be worth exploring how static scan results + runtime compliance data could combine into a more complete picture for auditors.

GitHub: https://github.com/airblackbox/gateway
PyPI: `pip install air-blackbox`

Apache 2.0.
