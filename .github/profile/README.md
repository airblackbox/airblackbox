# AIR Blackbox

**The flight recorder for autonomous AI agents. Record, replay, enforce, audit.**

Your agents are calling APIs, writing to databases, and moving money.
When something goes wrong — and it will — you need a record of exactly
what happened, who authorized it, and proof nobody altered the log.

That's what AIR Blackbox builds.

---

## What It Does

```bash
pip install air-blackbox
air-blackbox comply --scan . -v   # EU AI Act gap analysis, 60 seconds
```

One proxy swap gives every LLM call in your stack:

* A tamper-evident audit record — HMAC-SHA256 chained, async, zero latency impact
* Quantum-safe signing — ML-DSA-65 / FIPS 204. Signatures hold against future quantum attacks
* PII and injection detection — scanned before the model sees the prompt
* Replay — reconstruct any incident from the audit chain, not from memory
* EU AI Act coverage — 51+ gap analysis checks across Articles 9, 10, 11, 12, 13, 14, 15

No SDK changes. No code refactoring. Change `base_url`. Done.

## Repos

| Repo | What it is |
|---|---|
| [airblackbox](https://github.com/airblackbox/airblackbox) | Gateway + Python scanner + HMAC audit chain + evidence bundles |
| [air-trust](https://github.com/airblackbox/air-trust) | Cryptographic trust layer — Ed25519 signed handoffs + tamper-evident chains |
| [air-platform](https://github.com/airblackbox/air-platform) | Full stack deployment. Gateway + Episode Store + Policy Engine + Jaeger + Prometheus. `make up`. |
| [air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp) | MCP server — expose audit, replay, and compliance tools to any MCP-compatible agent |
| [compliance-action](https://github.com/airblackbox/compliance-action) | GitHub Action — run the scanner in any CI pipeline |

## Validated By

* **Julian Risch** (deepset) — public validation on LinkedIn and GitHub issue #10810
* **Piero Molino** (Ludwig maintainer) — merged EU AI Act compliance changes driven by AIR scan results
* **arXiv AEGIS paper** (March 2026) — independent researchers published the same interception-layer architecture
* **McKinsey State of AI Trust 2026** — named trust infrastructure as the critical agentic AI category

## Install

```bash
pip install air-blackbox
```

[airblackbox.ai](https://airblackbox.ai) · [PyPI](https://pypi.org/project/air-blackbox/) · [Live Demo](https://airblackbox.ai/demo/hub)
