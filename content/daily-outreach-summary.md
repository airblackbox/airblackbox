# AIR Blackbox Daily Outreach Summary

**Date**: Monday, May 4, 2026
**Operator**: autonomous AIR Blackbox outreach engine
**Run mode**: scheduled (no human in loop)

## Targets Processed (5 new drafts)

| Project | HQ | Stars | Python Files | Score | Contact | Status |
|---------|----|----|----|------|--------|----|
| Quivr (QuivrHQ, YC W24) | Paris, FR | 35K+ | 77 | 24% (14/58) | stan@quivr.app | Email Drafted |
| PyTorch Geometric (PyG) | TU Dortmund / Kumo.AI lead, DE | 22K+ | 1,328 | 34% (20/58) | matthias@pyg.org | Email Drafted |
| ydata-profiling (YData, acq. KPMG) | Lisbon, PT | 12K+ | 285 | 28% (16/57) | goncalo.ribeiro@ydata.ai | Email Drafted |
| auto-sklearn (AutoML / Hutter group) | Freiburg, DE | 7.6K+ | 381 | 22% (13/57) | feurerm@informatik.uni-freiburg.de | Email Drafted |
| OpenNMT-py (SYSTRAN / Seedfall) | Paris, FR | 6.8K+ | 152 | 21% (12/57) | vince62s@yahoo.com | Email Drafted (flag: contact confidence medium) |

All five passed the "primarily Python" gate cleanly: PyG had 1 non-Python compiled file out of 1,328, the others had 0.

## Why These Targets

- **Quivr** (Tier 1 EU, Paris, YC W24): One of the most-installed open-source RAG / "personal second brain" stacks on GitHub. Frameworks detected by the scanner: anthropic, langchain, openai, which means the AIR Blackbox trust layers translate directly into Article 12 (Record-Keeping) and Article 15 (runtime injection protection) wins via a single import. Article 14 (Human Oversight) is the standout gap: 0/9 passing, with autonomous agent patterns visible in `examples/simple_question_megaparse.py` and `examples/pdf_parsing_tika.py` but no kill switch, token expiry, or agent-to-user identity binding.

- **PyTorch Geometric (PyG)** (Tier 1 EU upstream, TU Dortmund + Kumo.AI): The default Python graph neural network library underneath EU pharma drug discovery, banking graph-fraud / AML, telecom network anomaly, and energy grid forecasting. All four downstream domains hit Annex III. Highest score of the day at 34% thanks to clean determinism + tracing + audit-trail patterns. Article 11 is the leverage point: a `MODEL_CARD.md` template plus public-API docstring coverage on `Data`, `HeteroData`, `MessagePassing`, `GNNExplainer` would meaningfully change downstream Technical Documentation evidence collection.

- **ydata-profiling (YData, acq. KPMG)** (Tier 1 EU, Lisbon): The default Python EDA + data quality pass that lives in front of an enormous amount of regulated tabular ML across EU. The KPMG acquisition is the angle: KPMG advisory engagements terminate in conformity assessments, and ydata-profiling reports are exactly the kind of artifact that becomes Article 10 (Data Governance) evidence. Counterintuitive finding: a library whose entire purpose is data quality scores 1/5 on Article 10 itself - no PII detection in the code path, no `DATA_GOVERNANCE.md`, no built-in vault integration. Big upstream-fix opportunity.

- **auto-sklearn (Hutter group / U. Freiburg)** (Tier 1 EU, DE): One of the most-cited AutoML libraries in Europe, embedded under regulated tabular ML in German banks, insurers, healthcare, and energy. Article 11 (1/5) and Article 14 (1/9) are the leverage points: a `MODEL_CARD.md` template auto-populated from the selected pipeline, plus explicit `time_budget` / `max_iter` enforcement and a structured `audit_log.jsonl`, would inherit upstream into every regulated EU AutoML deployment.

- **OpenNMT-py (SYSTRAN / Seedfall)** (Tier 1 EU, Paris): Older but battle-tested Python neural MT toolkit still embedded across SYSTRAN, Ubiqus-lineage shops, EU public-sector translation, and EU-funded research consortia. Translation systems hit Article 50 transparency obligations broadly and inherit the full Article 9 to 15 stack whenever the translation lands inside an Annex III workflow (immigration, judicial, healthcare triage, employment screening). Lowest-scoring article is 15 (1/10) but most of that is determinism flags not being surfaced at the API surface - likely already implemented under the hood, just not documented. Contact confidence flagged medium because `vince62s@yahoo.com` is the primary OSS git address rather than a corporate inbox; Seedfall doesn't publish a public roster.

## Emails Ready for Jason to Review and Send

- `/Users/jasonshotwell/Desktop/gateway/content/email-quivr.md`
- `/Users/jasonshotwell/Desktop/gateway/content/email-pytorch-geometric.md`
- `/Users/jasonshotwell/Desktop/gateway/content/email-ydata-profiling.md`
- `/Users/jasonshotwell/Desktop/gateway/content/email-auto-sklearn.md`
- `/Users/jasonshotwell/Desktop/gateway/content/email-opennmt-py.md`

## Targets Skipped Today (and why)

None this batch. All five candidates passed the "primarily Python AI/ML repo" gate on the first pass, so there was no need to substitute backups. Tier 1 EU bench is still deep - next batch can pull from Pleias, Quivr-adjacent French RAG stacks, additional Hutter-group libraries (TabPFN, SMAC), HuggingFace-internal Python repos with EU maintainer leads, and OpenNMT's sibling project Eole.

## Follow-up Reminders (5+ days since first email)

All previously-sent emails (Mar 26 to Mar 30 cohort) are now well past their 5-7 day follow-up window. Per the "one email + one follow-up after 5-7 days, then stop" rule, the active follow-up window is closed. Recommend pivoting these from "follow up" to "stop" status during the next pipeline review unless Jason wants to re-touch any specific contact manually.

The 48 emails currently in "Email Drafted" status from prior batches are still awaiting Jason's manual send. They are not on a follow-up clock yet because the first send hasn't happened.

| Project | Sent | Status | Recommended next action |
|---------|------|--------|---|
| Superlinked | ~Mar 27 | Sent, no response | Stop (past 5-7d window) |
| Browser Use | ~Mar 28 | Sent, no response | Stop (past 5-7d window) |
| RAGFlow | ~Mar 28 | Sent, no response | Stop (past 5-7d window) |
| MetaGPT | Mar 29 | Sent, no response | Stop (past 5-7d window) |
| Deepchecks | Mar 29 | Sent, no response | Stop (past 5-7d window) |
| Cleanlab | Mar 29 | Sent, no response | Stop (past 5-7d window) |
| Lightly AI | Mar 29 | Sent, no response | Stop (past 5-7d window) |
| FLUX (Black Forest Labs) | Mar 30 | Sent, no response | Stop (past 5-7d window) |
| supervision (Roboflow) | Mar 30 | Sent, no response | Stop (past 5-7d window) |
| Ivy (Unify) | Mar 30 | Sent, no response | Stop (past 5-7d window) |
| Letta (MemGPT) | Mar 30 | Sent, no response | Stop (past 5-7d window) |
| LiteLLM | ~Mar 26 | Rejected | Do not contact |

## Pipeline Stats (after today)

- **Total targets**: 65 (was 60)
- **Emails sent**: 12
- **Emails drafted (awaiting Jason send)**: 53 (was 48)
- **GitHub issues opened**: 12
- **Responses received**: 1 (LiteLLM, rejected)
- **Combined GitHub stars in pipeline**: 888K+ (was 805K+)
- **Average compliance score**: 25%
- **EU coverage today**: France (Quivr, OpenNMT-py), Germany (PyG via TU Dortmund, auto-sklearn via Freiburg), Portugal (ydata-profiling via Lisbon, now KPMG)

## Notes for Jason

- **Quivr is the highest-leverage send** of the batch. Stan is YC, French, and the scanner detected three frameworks (anthropic, langchain, openai) that all have AIR Blackbox trust layers. The trust-layer angle is a one-import sell that closes a real chunk of Article 12 + Article 15 simultaneously.
- **PyG is the best "upstream library" pitch**: 34% is the highest score of the batch, meaning the conversation is "you're already doing the hard parts, here's the small documentation lift that propagates Article 11 evidence to every regulated EU GNN deployer." Matthias' email `matthias@pyg.org` is in the project's `pyproject.toml`, high confidence.
- **YData has the most unusual angle of the day**: a data-quality library that scores 1/5 on its own Article 10. KPMG context makes the conformity-evidence framing land naturally with Goncalo.
- **OpenNMT-py contact confidence is medium**. `vince62s@yahoo.com` is the address with 394 commits across the project and 44 more under `vince62s` directly, so it's reliable for OSS maintainer outreach, but it is a personal Yahoo address rather than a corporate one. If preferred, Jason can route via LinkedIn to Vincent Nguyen (Seedfall, Paris) instead.
- **auto-sklearn** has been in maintenance mode for a while; if the response is "we're focused on AutoML 2.0 / SMAC / TabPFN now", that's a great pivot to follow up with the Hutter group's newer libraries on the next pass.
