# AIR Blackbox Outreach - Skip List

**Last updated:** 2026-05-04
**Owner:** Jason Shotwell
**Used by:** air-blackbox-outreach-engine (Track A + Track B)

This list is consulted on every run. If a company is here, the agent does not draft, regardless of how good the fit looks. If you think a skip is wrong, edit this file rather than overriding in copy.

## Hard skips (never contact)

| Company / Project | Reason | Added |
|---|---|---|
| Haystack / deepset | Active collaborators, do not pitch | 2026-04 |
| Geodesia | Direct competitor (G-1 evaluator), do not tip off | 2026-04 |
| asqav | Direct competitor (jagmarques), do not tip off | 2026-04 |

## Off-strategy skips (carried over from sales-pipeline.md "Off-Limits" / "Skipped" sections)

These were evaluated and rejected for technical or strategic reasons; do not re-evaluate without a new signal.

- **Qdrant** (Berlin, DE) - primary codebase is Rust, not Python
- **Neptune.ai** (Warsaw, PL) - being acquired by OpenAI
- **Lakera** (Zurich, CH) - no significant open-source Python repo
- **Seldon** (London, UK) - primary codebase is Go/Kubernetes
- **Kern AI** (Berlin, DE) - refinery repo is mostly Docker/shell
- **Resistant AI** (Prague, CZ) - no significant Python OSS repo
- **Humanloop** (London, UK) - Python SDK too small (11 stars)
- **PhotonAI** (Mannheim, DE) - academic project, only 64 stars
- **KNIME (knime-python-llm)** (Konstanz, DE) - repos return 404
- **InstaDeep / Jumanji** (London, UK) - already contacted via Mava sibling repo
- **Feedzai / fairgbm** (Lisbon, PT) - C++-dominant, fails primarily-Python gate
- **DeepL** (Cologne, DE) - no primary OSS Python repo
- **Sionna (NVlabs)** (Helsinki / Munich) - under NVIDIA Research, low response likelihood
- **Wayve (LingoQA / Driving-with-LLMs)** (London, UK) - repos too small to scan
- **Helsing AI** (Munich, DE) - primary repos are Rust
- **Synthflow / Parloa / Cognigy** (DE) - proprietary, no Python OSS
- **SpeakLeash / Bielik** (PL) - repos too small to scan
- **Quantexa** (London, UK) - Decision Intelligence Platform is closed source

## Notes

- The agent ALSO skips any company already in `sales-pipeline.md` with status: Sent, Email Drafted, Responded, Qualified, Objection, Nurture, Dead, or Closed. That dedupe is automatic - only add a company here if you want to permanently exclude it even after the existing draft is dropped.
- If the agent flags a company in the daily summary as "skip-list candidate," review and decide before adding.
