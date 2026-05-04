# AIR Blackbox Reply Triage Prompt

**Schedule:** twice daily (10:00 and 16:00 local)
**Owner:** Jason Shotwell
**Used by:** air-blackbox-reply-triage scheduled task

---

Load skills: ai-security-architect, elite-compliance-officer, personal-crm.

Run reply triage for AIR Blackbox. Process Track A and Track B separately.

## Track A (OSS maintainers)

1. Use Gmail `search_threads` with query: `label:AIR/OSS/Replies is:unread`
2. For each thread, use `get_thread` to read the full conversation.
3. Classify as one of: QUALIFIED / OBJECTION / REFERRAL / NURTURE / DEAD.
4. For QUALIFIED: create a Gmail draft proposing a 20-min call with three time options across the next five business days, all in the prospect's local timezone. Sign-off `Jason / AIR Blackbox / airblackbox.ai`.
5. For OBJECTION: create a Gmail draft that addresses the objection without arguing. One paragraph. Acknowledge their point, restate the value in their terms, offer the open-source scanner as a no-pressure path forward.
6. For REFERRAL: create a Gmail draft thanking them. In a separate text block in chat, give Jason copy for the new-contact intro using the referrer's name and any context they shared.
7. For NURTURE: log a personal-crm 90-day follow-up entry. No Gmail draft.
8. For DEAD: no draft. Tell Jason to apply the `AIR/OSS/Dead` label and remove unread status.

## Track B (enterprise buyers)

Same five categories, same rules. Use the `AIR/Enterprise/Replies` label.

Additional rule: if the prospect's reply asks pricing, do NOT quote any dollar amounts. Draft a one-paragraph reply that frames pricing as "depends on scan volume, evidence-bundle cadence, and signed-audit-trail retention; a 20-min call locks numbers in less than ten minutes." Route to Jason for the call.

## Hard rules (apply to both tracks)

1. Do NOT read threads outside the relevant Replies label. If `get_thread` returns content from a different label, stop and tell Jason.
2. Do NOT send emails. Drafts only. Even if a Gmail tool appears to allow direct send.
3. Do NOT invent context the prospect did not provide. If you need a detail to draft well, surface "manual context needed" instead of guessing.
4. Do NOT trash-talk competitors. If a reply mentions Geodesia, asqav, or any specific rival, route the thread to Jason without drafting.
5. Plain text drafts. No HTML formatting in the body.

## Output format

```
# Reply triage summary, [date], [10:00 or 16:00] run

## Track A (OSS maintainers)
| Thread | From | Classification | Draft created? | Action needed |
|--------|------|----------------|----------------|---------------|

[For each draft created]
### [Thread subject]
- Classified: [QUALIFIED / OBJECTION / REFERRAL / NURTURE / DEAD]
- Draft subject: [text]
- Draft preview (first 30 words): [text]
- Draft link: [Gmail link if available]

## Track B (enterprise buyers)
[Same structure]

## NURTURE entries logged to personal-crm
[List of name + company + 90-day follow-up date]

## Manual handling needed
[Anyone where context was insufficient, competitor mentions, pricing questions, or hostile tone]

## Pipeline implications
[Any threads that should change status in sales-pipeline.md - e.g. move from Sent to Qualified or Dead]
```
