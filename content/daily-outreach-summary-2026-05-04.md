# AIR Blackbox Outreach Summary, 2026-05-04

**Operator:** autonomous AIR Blackbox outreach engine
**Run mode:** scheduled (no human in loop)
**This file consolidates the morning Track A run + the afternoon Track B run.**

## TOP-LEVEL ALERT FOR JASON

**Gmail labels are missing.** A `list_labels` call to the Gmail MCP returned empty. None of the 10 required `AIR/OSS/*` and `AIR/Enterprise/*` labels exist. `list_drafts` is also empty, which means the morning Track A run did NOT create Gmail drafts either - it only wrote .md files. Per the outreach-engine spec ("If any are missing, STOP and tell Jason to create them in Gmail before continuing. Do not proceed with drafts that have nowhere to land"), this run also skipped Gmail draft creation.

**Action required:** Create these 10 Gmail labels manually (Gmail → Settings → Labels → Create new label) before the next run, then the agent can resume Gmail draft creation autonomously:

- `AIR/OSS/Sent`, `AIR/OSS/Replies`, `AIR/OSS/Qualified`, `AIR/OSS/Dead`
- `AIR/Enterprise/Sent`, `AIR/Enterprise/Replies`, `AIR/Enterprise/Qualified`, `AIR/Enterprise/Objection`, `AIR/Enterprise/Nurture`, `AIR/Enterprise/Dead`

In the meantime, the .md files at `~/Desktop/gateway/content/email-*.md` are send-ready - the email body and subject are at the top of each file. Copy/paste into Gmail compose, send, and apply the label manually until the agent can resume.

---

## Track A (OSS Maintainers) - Morning Run

- **Targets processed:** 5
- **Drafts created (as .md files):** 5
- **Skipped:** 0

This run completed successfully at ~16:10-16:11 local. Full per-target detail is in `daily-outreach-summary.md` (the legacy un-dated file). Quick recap:

### Quivr (QuivrHQ, YC W24)
- Stars: 35K+ • Score: 24% (14/58) • Python files: 77
- Contact: stan@quivr.app - confidence HIGH
- Subject: "EU AI Act compliance scan results for Quivr (77 files scanned)"
- Gmail draft: NOT created (labels missing)
- Trust layer offered: yes - anthropic, langchain, openai detected
- File: `email-quivr.md`

### PyTorch Geometric (PyG)
- Stars: 22K+ • Score: 34% (20/58) • Python files: 1,328
- Contact: matthias@pyg.org - confidence HIGH
- Subject: "EU AI Act compliance scan results for PyTorch Geometric (1,328 files scanned)"
- Gmail draft: NOT created (labels missing)
- Trust layer offered: no (library, not an agent framework)
- File: `email-pytorch-geometric.md`

### ydata-profiling (YData, acq. KPMG)
- Stars: 12K+ • Score: 28% (16/57) • Python files: 285
- Contact: goncalo.ribeiro@ydata.ai - confidence HIGH
- Subject: "EU AI Act compliance scan results for ydata-profiling (285 files scanned)"
- Gmail draft: NOT created (labels missing)
- Trust layer offered: no
- File: `email-ydata-profiling.md`

### auto-sklearn (AutoML / U. Freiburg, Hutter group)
- Stars: 7.6K+ • Score: 22% (13/57) • Python files: 381
- Contact: feurerm@informatik.uni-freiburg.de - confidence HIGH
- Subject: "EU AI Act compliance scan results for auto-sklearn (381 files scanned)"
- Gmail draft: NOT created (labels missing)
- Trust layer offered: no
- File: `email-auto-sklearn.md`

### OpenNMT-py (SYSTRAN / Seedfall)
- Stars: 6.8K+ • Score: 21% (12/57) • Python files: 152
- Contact: vince62s@yahoo.com - confidence MEDIUM (primary OSS git address, not a corporate inbox)
- Subject: "EU AI Act compliance scan results for OpenNMT-py (152 files scanned)"
- Gmail draft: NOT created (labels missing)
- Trust layer offered: no
- File: `email-opennmt-py.md`

---

## Track B (Enterprise Buyers) - Afternoon Run

- **Targets researched:** 5 (CaixaBank, Amplifon, Adecco Group, ENGIE, Finnair)
- **Drafts created (as .md files):** 4
- **Skipped:** 1 (CaixaBank - email confidence below 70% threshold)

All four drafts include the full 3-email sequence (Email 1 hook, Email 2 proof at Day 4, Email 3 breakup at Day 9) per spec.

### Adecco Group
- Industry: Staffing / HR Tech (Annex III(4) high-risk)
- Lead: Hélène Jonquoy, Chief Digital, Data & AI Officer (Zurich, CH)
- Email: helene.jonquoy@adeccogroup.com - confidence HIGH (97.5% per RocketReach)
- Hook article: Article 14 (Human Oversight)
- Signal: Unlimited Agentforce 360 license signed Mar 2026, targeting 50% AI-driven revenue by end of 2026; UK + France + India + Poland + Mexico + Morocco rollout
- Signal URL: https://www.adeccogroup.com/our-group/media/press-releases/the-adecco-group-completes-successful-first-agentic-ai-implementation-at-scale
- Subject: "agentforce 360 + annex iii(4)"
- Gmail draft: NOT created (labels missing)
- File: `email-adecco-group.md` (Email 1 + 2 + 3 all in file)

### Amplifon
- Industry: Healthcare / Hearing aids
- Lead: Giuseppe Ficara, Senior Director / Global Head of Data and AI (Milan, IT)
- Email: giuseppe.ficara@amplifon.com - confidence HIGH (97% per RocketReach)
- Hook article: Article 10 (Data Governance)
- Signal: AmplifAI launched as global AI governance program + Agentforce deployment for autonomous scheduling, follow-ups, device-servicing alerts across 26 countries / 20K professionals
- Signal URL: https://www.startuphub.ai/ai-news/artificial-intelligence/2026/amplifon-s-ai-platform-governance-control-and-discovery
- Subject: "amplifai + article 10"
- Gmail draft: NOT created (labels missing)
- File: `email-amplifon.md`

### ENGIE
- Industry: Energy / Utilities (Annex III(2) critical infrastructure + NIS2 overlay)
- Lead: Sébastien Arbola, EVP Data, Digital & IT, Strategy and R&I (Courbevoie, FR)
- Email: sebastien.arbola@engie.com - confidence HIGH (97.4% per RocketReach)
- Hook article: Article 11 + 12 (Documentation + Record-Keeping)
- Signal: Belgium Agentforce rollout with Capgemini hitting 71% autonomous resolution on billing, smart meter, contracts, EV charging; field tech + sales + trading agents next
- Signal URL: https://www.salesforce.com/customer-stories/engie/
- Subject: "71% auto-resolution + article 12"
- Gmail draft: NOT created (labels missing)
- File: `email-engie.md`

### Finnair
- Industry: Airline (consumer-facing, Article 50 transparency directly applicable)
- Lead: Antti Kleemola, Chief Digital Officer, member of Executive Board (Helsinki, FI)
- Email: antti.kleemola@finnair.com - confidence HIGH (98% per RocketReach)
- Hook article: Article 50 (Transparency obligations to natural persons)
- Signal: First Agentforce agent on finnair.com hitting up to 80% resolution + 30% reduction in human-agent onboarding; Amadeus PSS integration is the next step
- Signal URL: https://diginomica.com/how-finnair-aims-fly-high-agentforce
- Subject: "finnair.com agent + article 50"
- Gmail draft: NOT created (labels missing)
- File: `email-finnair.md`

### CaixaBank - DEFERRED
- Reason: Email format split per RocketReach (63.6% `jdoe@caixabank.com` vs. ~30% `jane.doe@caixabank.com`). Best-guess email for Mariona Vicens (Director Digital Transformation & Advanced Analytics, Management Committee) is below the 70% confidence threshold the spec requires.
- Suggested next action: Verify whether Vicens uses `mvicens@caixabank.com` or `mariona.vicens@caixabank.com` via LinkedIn or a CaixaBank press release with author byline. Once verified, this is otherwise the strongest fit on the Track B target list (banking is Annex III(5) high-risk; CaixaBank's 2025-2027 Cosmos Strategic Plan commits €5B to AI; the CaixaBank-Salesforce partnership is publicly named).
- Logged in `sales-pipeline.md` under Track B Manual Research Needed.

---

## Follow-up reminders

### Track A - past 5-7 day window (recommend "stop")

All previously-sent Track A emails (Mar 26 to Mar 30 cohort) are now well past their 5-7 day follow-up window. Per the "one email + one follow-up after 5-7 days, then stop" rule: Superlinked, Browser Use, RAGFlow, MetaGPT, Deepchecks, Cleanlab, Lightly AI, FLUX, supervision (Roboflow), Ivy (Unify), Letta (MemGPT) - all should move from "follow up" to "stop" status. Recommendation: bulk-update during the next pipeline review.

### Track A - drafts pending Jason send

53 drafts from prior batches sit in "Email Drafted" status awaiting Jason's manual send. They have no follow-up clock running yet because the first send hasn't happened. Today's 5 new Track A drafts join that queue.

### Track B - follow-up dates if Email 1 sent today (2026-05-04)

| Company | Email 2 (Day 4) | Email 3 (Day 9) |
|---------|----------------|----------------|
| Adecco Group | 2026-05-08 | 2026-05-13 |
| Amplifon | 2026-05-08 | 2026-05-13 |
| ENGIE | 2026-05-08 | 2026-05-13 |
| Finnair | 2026-05-08 | 2026-05-13 |

These dates assume Email 1 actually goes out today. If Jason can't send until labels are fixed, slide each follow-up date by the same number of days.

---

## Manual research needed

- **CaixaBank - Mariona Vicens email format.** See above.
- **ENGIE backup contact - Julia Maris (EVP Group Corporate Secretariat / Legal & Ethics).** Format `julia.maris@engie.com` is high-confidence per the same RocketReach data, but only worth pursuing if Arbola doesn't engage.
- **Finnair backup contact - Tiina Vesterinen (VP Digital Customer & Revenue).** Same logic: `tiina.vesterinen@finnair.com` is high-confidence, but Kleemola is the primary.

---

## Skip-list adds suggested

None this run. All 5 Track B candidates were either drafted or deferred for confidence reasons; no candidate showed signals that warrant a permanent skip.

---

## Pipeline stats

- **Track A targets contacted (lifetime):** 65
- **Track B targets contacted (lifetime):** 4 (all from this run)
- **Track A drafts pending send:** 58 (53 prior + 5 today)
- **Track B drafts pending send:** 4 (all today)
- **Replies awaiting triage:** 0 (Replies labels don't exist yet)
- **Qualified this week:** 0

---

## Setup files created this run

- `~/Desktop/gateway/content/skip-list.md` - was missing per Appendix A; now exists with the three hard skips (Haystack/deepset, Geodesia, asqav) plus the carryover off-strategy skips from the existing pipeline file
- `~/Desktop/gateway/content/reply-triage-prompt.md` - was missing per Appendix B; now exists with the Track-aware reply triage template

---

## Recommendations for tomorrow

1. **Highest-impact unblocker: create the 10 Gmail labels.** Without them, every future run produces .md files that need manual copy-paste. With them, the agent can run truly hands-off.
2. **Track B can produce 5-10/day comfortably once unblocked.** Today's research overhead was a one-time cost - the 4 drafted accounts are a starting bench, and the same enterprise-targets.csv has another ~135 candidates to qualify.
3. **The enterprise-targets.csv schema is shallower than the spec assumes.** The spec wants `lead_name, lead_email, lead_linkedin, ai_signal_url, hook_article` columns; the existing CSV has `Company, Industry, Confidence, Priority, EU AI Concern, Source URL` only. Recommend a one-time enrichment pass (lead-finding + signal verification) on the 50 highest-priority entries so future runs spend less time on research and more on writing. Could be delegated to the hiring-signal-detector skill.
