## The EU AI Act enforcement deadline is August 2, 2026.

Penalties: up to 35M euros or 7% of global turnover.

Your board will ask: "Are we compliant?" Your legal team will ask: "Show me the audit trail." Your engineers will ask: "How do we prove it?"

**AIR Blackbox answers all three in 5 minutes.**

One scan. Four compliance standards. EU AI Act + ISO 42001 + NIST AI RMF + Colorado SB 205. Single audit package for every regulator, every auditor, every investor question.

Local-first. No cloud. No vendor lock-in. Drop it into any AI pipeline.

### Get started in 30 seconds

```bash
pip install air-blackbox
air-blackbox comply --scan .
```

That's it. 39 checks across 6 EU AI Act articles. No config, no API keys, no Docker.

### What we ship

| Package | What it does | Install |
|---|---|---|
| **[air-blackbox](https://github.com/airblackbox/gateway)** | CLI compliance scanner: 4 frameworks, 39 checks, evidence export | `pip install air-blackbox` |
| **[air-trust](https://github.com/airblackbox/gateway)** | Tamper-evident HMAC-SHA256 audit chain + Ed25519 signed handoffs | `pip install air-trust` |
| **[air-gate](https://github.com/airblackbox/air-gate)** | Human-in-the-loop tool approval with audit trail | `pip install air-gate` |
| **[air-blackbox-mcp](https://github.com/airblackbox/air-blackbox-mcp)** | Compliance scanning inside Claude Desktop, Cursor, Claude Code | `pip install air-blackbox-mcp` |

Plus drop-in trust layers for **LangChain**, **CrewAI**, **OpenAI Agents**, **Anthropic Claude**, **Google ADK**, and **25+ frameworks**. No code changes needed.

### One scan, four standards

Most compliance tools cover one framework. AIR Blackbox maps every check to four simultaneously:

| Category | EU AI Act | ISO 42001 | NIST AI RMF | Colorado SB 205 |
|---|---|---|---|---|
| Risk Management | Article 9 | 6.1, 6.1.2, A.6.2.1 | GOVERN 1, MAP 1, MAP 3 | Section 6(2)(a-b) |
| Data Governance | Article 10 | A.6.2.4, A.6.2.5 | MAP 2, MEASURE 2 | Section 6(2)(c) |
| Human Oversight | Article 14 | A.6.2.3 | GOVERN 2, MANAGE 1 | Section 6(2)(e), 7 |
| + 5 more categories | Art. 11-15 | 7.5, 9.1, A.6.2.x | Full RMF coverage | Sections 2-7 |

```bash
air-blackbox standards                      # See the full crosswalk
air-blackbox comply --frameworks eu,nist    # Filter by framework
```

### Try the demo

**[airblackbox.ai/demo/signed-handoff](https://airblackbox.ai/demo/signed-handoff)** -- see Ed25519 signed agent handoffs in action. No install needed.

### Get in touch

[airblackbox.ai](https://airblackbox.ai) | [jason@airblackbox.ai](mailto:jason@airblackbox.ai)
