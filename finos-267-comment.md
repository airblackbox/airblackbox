# FINOS Issue #267 comment

**Context**: finos/ai-governance-framework #267 is the active thread reshaping the NIST RFI response around "AIGF as augmentation of NIST." It's where the working group is now focused. Our comment introduces AIR Blackbox as the compliance scanner that audits AIGF implementation — not as a competing framework.

**Tone**: Contributor, not vendor. Specific, technical, offers to help.

---

## DRAFT COMMENT

Following the thread between @botbotfromuk and @Cyberweasel777 on agent identity continuity (and the SCC spec that came out of it), I shipped something complementary today that might be useful for the FINOS NIST RFI response:

**air-blackbox v1.12.0** — an open-source CLI scanner that checks whether a Python AI codebase implements any recognized agent identity scheme:

- `air_trust` (Ed25519 agent keys + HMAC-SHA256 audit chain)
- `botindex-aar` — Agent Action Receipt
- `botindex-aar@1.1.0+` — Session Continuity Certificate

It's Apache 2.0, runs locally, no cloud. Install: `pip install air-blackbox`. Repo: https://github.com/airblackbox/airblackbox

**How this fits the FINOS response:**

The draft response identifies MI-21 (Agent Decision Audit) Tier 3 as requiring "comprehensive cryptographic audit trail" for SR 11-7 compliance. The AAR + SCC specs @Cyberweasel777 and @botbotfromuk developed ARE that infrastructure. What's been missing is the static-analysis layer that verifies a given codebase implements it correctly — before it ships, before a regulator sees it.

AIR Blackbox now does that layer across the three main schemes, with per-check mapping to EU AI Act Articles 9, 10, 11, 12, 13, 14, 15 plus GDPR and bias/fairness. The 1.11.x / 1.12.0 releases also shipped the first Article 13 transparency scanner (AI disclosure, model card, instructions for use, provider identity, output interpretation, change logging) and the first Article 15 hardware determinism scanner — checks RNG seed setting, framework-level deterministic algorithm flags (`torch.use_deterministic_algorithms`, `cudnn.deterministic`, `enable_op_determinism`), and hardware abstraction anti-patterns. That last piece is directly relevant to SR 11-7 model reproducibility, which the FINOS draft response calls out several times.

**Specific offer:** if it's useful for the FINOS submission, I can:

1. Write a short section describing AIR Blackbox as a reference implementation of the static-audit layer for MI-21 Tier 3 — keeps the FINOS framework as the authoritative catalogue, positions compliance scanning as one of the open-source tools supporting it
2. Contribute a Python port of SCC that wires into `air_trust.chain` — would give the FINOS response one codebase demonstrating both the runtime protocol (SCC) and the static auditor (AIR Blackbox)
3. Map every AIR Blackbox check to the FINOS RI-XX / MI-XX identifiers in the framework so the scanner output reads as AIGF compliance evidence

Whichever is most useful — happy to draft against whatever format the working group prefers.

— Jason Shotwell (@jshotwell)

---

## POSTING PLAN

- Post as a single comment on finos/ai-governance-framework#267
- Tag @alvin-c-shih (thread owner), @botbotfromuk, @Cyberweasel777 only if the issue permits tagging — otherwise let them find it via thread notifications
- Do NOT cross-post on the closed #266 thread
- If someone responds with interest in any of the three offers, open a tracking issue in the gateway repo and follow up in-thread
