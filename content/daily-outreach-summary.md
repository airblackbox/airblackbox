# Daily Outreach Summary — April 23, 2026

## Targets Processed (Apr 23 batch, 4 drafts)

| Project | Location | Stars | Python Files | Score | Contact | Email File | Status |
|---|---|---|---|---|---|---|---|
| Graphcore (examples) | Bristol, UK (SoftBank) | ~780 | 1,225 | 14/58 (24%) | Nigel Toon, CEO — nigelt@graphcore.ai | email-graphcore-examples.md | Ready for review |
| LightOn (PyLate) | Paris, FR | ~600 | 104 | 11/57 (19%) | Antoine Chaffin, Head of Search / PyLate maintainer — antoine.chaffin@lighton.ai | email-pylate-lighton.md | Ready for review |
| Silo AI / LumiOpen (Megatron-LM-lumi) | Helsinki, FI (AMD) | ~45 | 282 | 14/58 (24%) | Peter Sarlin, CEO — peter.sarlin@silo.ai | email-silo-ai-lumiopen.md | Ready for review |
| ScrapeGraphAI | Trento, IT | 17K+ | 258 | 21/58 (36%) | Marco Vinciguerra, Co-Founder — marco@scrapegraphai.com | email-scrapegraphai.md | Ready for review, contact confidence medium |

All four are Tier 1 EU targets directly subject to the EU AI Act in August 2026.

## Contact Notes

- **nigelt@graphcore.ai**: derived from git log pattern (firstname + last-name-initial, e.g. `adams@`, `philb@`, `sofial@`, `ganeshk@`). High confidence.
- **antoine.chaffin@lighton.ai**: maintainer of PyLate, listed on lighton.ai/team. High confidence. Fallback: igor.carron@lighton.ai or contact@lighton.ai for CEO route.
- **peter.sarlin@silo.ai**: confirmed Silo AI domain pattern from git log (`antti.virtanen@silo.ai`). High confidence.
- **marco@scrapegraphai.com**: pattern guess. Git log shows personal Gmails (mvincig11@gmail.com, perinim.98@gmail.com, lorenzo.padoan977@gmail.com). Fallback: contact@scrapegraphai.com. Flagged for Jason to confirm before sending.

## Targets Skipped This Batch

- **KNIME (knime-python-llm)** (Konstanz, DE): GitHub repo URL returns 404 (likely private or renamed). Same for knime-python and knime-examples. Pivoted to ScrapeGraphAI to keep 4 targets.
- **InstaDeep / Jumanji** (London, UK): already contacted via sibling repo Mava (see email-mava-instadeep.md). Do not double-tap.
- **LumiOpen/lumiopen-tools** (11 Python files) and **LumiOpen/poro2-scripts-dev** (4 files): too small to justify as the scan target. Used Megatron-LM-lumi (282 files) instead as Silo AI's substantive training stack.
- **Iktos** (Paris, FR): no meaningful open-source Python repo found.

## Emails Ready for Jason to Review and Send

1. `content/email-graphcore-examples.md` → nigelt@graphcore.ai
2. `content/email-pylate-lighton.md` → antoine.chaffin@lighton.ai
3. `content/email-silo-ai-lumiopen.md` → peter.sarlin@silo.ai
4. `content/email-scrapegraphai.md` → marco@scrapegraphai.com (confirm contact first)

## Follow-up Reminders

All previously sent emails (Apr 1 through Apr 4) are now past their 5-day follow-up window and past the one-email-plus-one-follow-up sequence cap. No fresh follow-up due today:

- **Superlinked** (sent Apr 1): 22 days past follow-up window. Sequence complete.
- **Browser Use / RAGFlow** (sent Apr 2): 21 days past. Sequence complete.
- **MetaGPT / Deepchecks / Cleanlab / Lightly AI** (sent Apr 3): 20 days past. Sequence complete.
- **FLUX / supervision (Roboflow) / Ivy (Unify) / Letta (MemGPT)** (sent Apr 4): 19 days past. Sequence complete.
- **LiteLLM**: rejected. No follow-up.

Per the outreach rules (one email + one follow-up, then stop), these are done. If any of the GitHub issues opened against those repos show fresh engagement, Jason can choose to re-open the conversation on that thread rather than via email.

## Pipeline Totals After This Batch

- Total targets: 39 (was 35)
- Emails sent: 12
- Emails drafted: 27 (was 23, +4 today)
- GitHub issues opened: 12
- Responses: 1 (LiteLLM, rejected)
- Combined GitHub stars of contacted + drafted targets: 720K+
- Avg compliance score across pipeline: 25%

## Notes for Jason

The ScrapeGraphAI scan (21/58) is the strongest opening score in this batch. That email leads with genuine praise for Articles 11, 12, and 15 before surfacing the Art. 10 gap, so it should land well. Consider this one the highest-probability reply in the batch.

Silo AI / LumiOpen is the most strategically valuable target. Peter Sarlin is the loudest European voice on sovereign AI, and a published EU AI Act compliance posture on Poro and Viking would be a PR moment for both sides.

Graphcore post-SoftBank is quieter than it used to be. The email frames it as "every example you ship sets the default compliance posture for downstream IPU users," which should resonate if it reaches Nigel directly.

PyLate is a tight, technical outreach to a specific maintainer (Antoine) rather than a CEO. That is deliberate, since the LightOn org is big enough that a maintainer-to-maintainer note is more likely to land than a CEO cold email. If no reply in 5-7 days, the follow-up can route to igor.carron@lighton.ai.
