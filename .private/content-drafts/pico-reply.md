# Reply to Pico (AgentLair) — ATF Integration

**Subject:** Re: CSA Agentic Trust Framework — AIR Blackbox now has native ATF conformance

---

Hi Pico,

Thanks for reaching out — the timing is good. I went deep on the CSA Agentic Trust Framework over the last couple of days and shipped native ATF support into `air-trust` v0.4.0 (the universal trust layer that sits underneath AIR Blackbox).

Quick summary of what's now in the package:

**Identity core element (ATF Element 1) — all 5 requirements implemented**

- **I-1 Unique Identifier** — every `AgentIdentity` now auto-derives a persistent URN in the form `urn:agent:{org}:{name}:{version}`. Custom URNs are preserved if supplied.
- **I-2 Credential Binding** — SHA-256 fingerprint over `name:owner:version` (was already there from our Article 14 work).
- **I-3 Ownership Chain** — `owner` + optional `org` field.
- **I-4 Purpose Declaration** — new `purpose` field (MUST at Intern level).
- **I-5 Capability Manifest** — new `capabilities` field, kept distinct from `permissions` (capabilities = what the agent *can* do, permissions = what it's *allowed* to do). Falls back to `permissions` for backward compatibility.

**Conformance engine**

`air_trust.atf` ships a full MUST/SHOULD/MAY matrix across all four maturity levels (Intern → Principal). You can call:

```python
from air_trust import AgentIdentity
from air_trust.atf import conformance, level_compliant, conformance_statement

identity = AgentIdentity(
    agent_name="customer-search",
    owner="jason@airblackbox.ai",
    org="AIR Blackbox",
    purpose="Answer customer questions from product docs",
    capabilities=["search:docs", "llm:respond"],
    external_id="pico@agentlair.dev",  # <-- this is where AgentLair plugs in
    atf_level="junior",
)

conformance(identity)            # {"I-1": True, ..., "I-5": True}
level_compliant(identity, "junior")
print(conformance_statement(identity))  # auditor-ready report
```

There's also a CLI:

```bash
python -m air_trust atf \
    --name customer-search \
    --owner jason@airblackbox.ai \
    --org "AIR Blackbox" \
    --purpose "Answer customer questions from product docs" \
    --capabilities "search:docs,llm:respond" \
    --level intern
```

Output is a human-readable conformance statement suitable for compliance reports, or `--format json` for programmatic use / regulatory submissions.

**AgentLair as an external identity provider**

I designed the integration so AgentLair is a first-class *optional* external identity provider, not a hard dependency. The new `external_id` field on `AgentIdentity` is meant to hold exactly the kind of binding you mentioned — things like `pico@agentlair.dev` or a `did:web:` URI — which maps the local URN onto an external registry. That pattern keeps `air-trust` usable in air-gapped / offline environments while still letting teams who use AgentLair (or DIDs, or any other registry) tie their local agents to a durable external identity.

If AgentLair exposes a stable lookup/verify endpoint for those external IDs, I'd be happy to add an `air_trust.providers.agentlair` adapter in a follow-up release — something like `AgentLairProvider().verify(identity)` that attests the external binding and feeds the result back into the conformance check. Happy to spec that out with you.

**Shipping details**

- `air-trust==0.4.0` — the ATF work is in the module now; 223 tests passing including 34 new ATF-specific tests.
- Will be on PyPI shortly.
- Repo: https://github.com/airblackbox/air-trust
- Docs will land on airblackbox.ai alongside the Article 11 / Roadmap posts that just went live.

Because `air-trust` is the trust layer underneath the whole AIR Blackbox ecosystem (air-compliance, air-blackbox, the MCP server), every downstream consumer gets ATF conformance automatically once they upgrade — which is the whole point of doing it at the trust-layer level instead of at the scanner level.

A couple of open questions on my side:

1. What does AgentLair's verification surface look like today? Is there a public endpoint I can hit to resolve `pico@agentlair.dev` → signed identity claims, or is it still auth-walled?
2. Are you tracking ATF v0.9.1 → v1.0 timelines? I'd like to pin conformance_statement output to whatever the final spec numbering looks like before I start publishing auditor-facing PDFs.
3. Any interest in being the first public external identity provider referenced in the air-trust docs? I think there's a nice story there: "CSA ATF conformance, locally verifiable, optionally federated via AgentLair."

Let me know what makes sense. If you want, I can send over a sample `conformance_statement()` output for a fake agent so you can see the format end-to-end.

Best,
Jason Shotwell
AIR Blackbox
jason@airblackbox.ai
