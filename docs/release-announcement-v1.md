# AIR Blackbox v1.0.0 — Release Announcement Content

## LinkedIn Post

---

I shipped an AI governance platform in a day.

Not a slide deck. Not a roadmap. Working software on PyPI.

`pip install air-blackbox`

Four commands:

→ `comply` — 20 EU AI Act checks across Articles 9-15, 90% auto-detected from live traffic
→ `discover` — AI-BOM (CycloneDX 1.6), shadow AI detection, tool inventory  
→ `replay` — incident reconstruction from HMAC-SHA256 audit chain
→ `export` — signed evidence bundles for auditors and insurers

What it actually does:

Your AI agent makes a call. The gateway records it. The compliance engine maps it to EU AI Act articles. The AI-BOM generator catalogs every model, provider, and tool. The shadow AI detector flags anything not on your approved list.

One reverse proxy. One Python package. 90% of compliance checks automated.

The EU AI Act high-risk deadline is August 2, 2026. Penalties up to €35M or 7% of global turnover.

Most companies have no idea how to comply. Enterprise tools cost $50K+/year. We're open-source and free.

Try it in 30 seconds:
```
pip install air-blackbox
air-blackbox demo
```

No Docker. No config. No API keys needed for the demo.

GitHub: https://github.com/airblackbox/gateway
PyPI: https://pypi.org/project/air-blackbox/

#AIGovernance #EUAIAct #OpenSource #Compliance #LangChain #Python #AIBOM

---

## Dev.to / Hacker News Article

---

**Title (HN):** Show HN: 4 commands for EU AI Act compliance — AI-BOM, shadow AI detection, audit trails

**Title (Dev.to):** I built an AI governance control plane in Python. Here's what each command does.

---

The EU AI Act enforcement deadline for high-risk AI systems is August 2, 2026. If you're building AI agents with LangChain, CrewAI, OpenAI, or any Python framework — and you're selling into EU markets — you'll need to prove compliance.

I built AIR Blackbox to make that as simple as `pip install air-blackbox`.

### What it does

Four commands, one product:

**`air-blackbox comply -v`** — Runs 20 compliance checks against EU AI Act Articles 9-15. Connects to your running gateway and analyzes live traffic. Shows which articles pass, which warn, which fail — with specific fix hints for every failing check.

90% of checks are auto-detected from observed traffic. The gateway already sees the data — it just maps it to compliance articles.

**`air-blackbox discover`** — Generates an AI Bill of Materials (CycloneDX 1.6) from your gateway traffic. Every model, every provider, every tool your agents use — inventoried automatically. 

Also does shadow AI detection: define an approved model registry, and anything not on the list gets flagged. "Your team made 45 requests to api.mistral.ai. This endpoint is not approved."

**`air-blackbox replay`** — Incident reconstruction from the HMAC-SHA256 audit chain. When something goes wrong, see exactly which model was called, what tools were invoked, how many tokens were used, and what the response was. `--verify` checks the chain integrity — if any record was tampered with, the chain breaks.

**`air-blackbox export`** — Packages everything into one signed evidence bundle: compliance scan + AI-BOM + audit trail + HMAC attestation. Hand it to your auditor or insurer as a single JSON file. The signature is independently verifiable.

### The trust layers

For LangChain users:

```python
from air_blackbox.trust.langchain import AirLangChainHandler

chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})
```

That one line adds: audit logging for every LLM call and tool invocation, PII detection (emails, SSNs, phone numbers, credit cards), and prompt injection scanning (7 patterns). Non-blocking — if logging fails, your agent keeps running.

### How it's different from Langfuse/Helicone/Datadog

They do observability. AIR does accountability.

- Your data stays in your vault (S3/MinIO/local) — not their cloud
- HMAC-SHA256 tamper-evident audit chain — not just logs
- CycloneDX AI-BOM generation — not just dashboards
- Shadow AI detection — not just metrics
- Signed evidence bundles — not just exports
- EU AI Act compliance mapping — not just monitoring

### Try it now

```bash
pip install air-blackbox
air-blackbox demo
air-blackbox comply -v
air-blackbox discover
```

No Docker required for the demo. Zero config. 30 seconds to see compliance results.

GitHub: https://github.com/airblackbox/gateway  
PyPI: https://pypi.org/project/air-blackbox/

Apache 2.0. Built on OpenTelemetry. Feedback welcome.

---

## Twitter/X Thread

---

🧵 Shipped: `pip install air-blackbox` — an AI governance control plane in 4 commands.

EU AI Act deadline: Aug 2, 2026. Most companies have no idea how to comply.

Here's what it does: ↓

---

1/ `air-blackbox comply -v`

20 EU AI Act checks. Articles 9-15. 90% auto-detected from gateway traffic.

Shows pass/warn/fail for each article with specific fix hints.

The gateway already sees your AI traffic — it just maps it to compliance.

---

2/ `air-blackbox discover`

Generates a CycloneDX 1.6 AI Bill of Materials from observed traffic.

Every model. Every provider. Every tool. Inventoried automatically.

Shadow AI detection: flag any model not on your approved list.

---

3/ `air-blackbox replay`

Incident reconstruction from HMAC-SHA256 audit chain.

When something goes wrong → see exactly what happened.
`--verify` checks chain integrity. Tampering breaks the chain.

---

4/ `air-blackbox export`

One command → signed evidence bundle for auditors.

Compliance scan + AI-BOM + audit trail + HMAC attestation.

Hand one JSON file to your auditor. Signature is independently verifiable.

---

5/ Trust layers for LangChain:

```python
from air_blackbox.trust.langchain import AirLangChainHandler
chain.invoke(input, config={"callbacks": [AirLangChainHandler()]})
```

PII detection. Injection scanning. Audit logging. Non-blocking.

---

6/ Try it now:

```
pip install air-blackbox
air-blackbox demo
```

No Docker. No config. 30 seconds.

GitHub: github.com/airblackbox/gateway
PyPI: pypi.org/project/air-blackbox/

Open source. Apache 2.0. Feedback welcome.

---

## Reddit Post (r/MachineLearning, r/LangChain, r/artificial)

---

**Title:** I built a CLI that checks your AI agent for EU AI Act compliance — 20 checks, 90% automated, CycloneDX AI-BOM included

The EU AI Act high-risk deadline is August 2, 2026 and most teams building with LangChain, CrewAI, or the OpenAI SDK haven't started thinking about compliance.

I built `air-blackbox` — a Python CLI that runs 20 compliance checks against EU AI Act Articles 9-15, generates CycloneDX AI-BOMs from observed traffic, detects shadow AI (unapproved models), and produces signed evidence bundles for auditors.

Try it:
```
pip install air-blackbox
air-blackbox demo
air-blackbox comply -v
```

It's a reverse proxy + Python SDK. Route your AI traffic through it and everything is recorded, analyzed, and compliance-checked. HMAC-SHA256 audit chains, PII detection, prompt injection scanning.

Not observability (that's Langfuse/Datadog). This is accountability — tamper-proof records + compliance mapping + evidence export.

Open source, Apache 2.0: https://github.com/airblackbox/gateway

Looking for feedback, especially from teams building agents that sell into EU markets. What compliance checks would you add?
