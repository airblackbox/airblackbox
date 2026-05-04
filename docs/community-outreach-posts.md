# AIR Blackbox - GitHub Community Outreach Posts

## 1. Microsoft Agent Framework (github.com/microsoft/agent-framework)
### Post in: Discussions → Ideas or General

**Title:** EU AI Act compliance plugin for Agent Framework - audit trails, runtime validation, evidence export

**Body:**

Hi Agent Framework team 👋

Built an EU AI Act compliance layer that plugs into agent frameworks as a non-blocking observer. Sharing here because Agent Framework's built-in OTel support makes it a natural fit.

**What it does:**

`pip install air-blackbox` gives you 5 commands:

- `comply` - 20 EU AI Act checks across Articles 9-15, 90% auto-detected from observed traffic
- `discover` - AI Bill of Materials (CycloneDX 1.6) + shadow AI detection from live traffic
- `validate` - pre-execution runtime certification (schema validation, tool allowlists, content policy, hallucination guards)
- `replay` - incident reconstruction from HMAC-SHA256 audit chain
- `export` - signed evidence bundles for auditors
