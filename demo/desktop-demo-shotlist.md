# Claude Desktop Demo — Shot List (for screen recording)

The "what it feels like" companion to the terminal proof
(`demo/governed_screening_demo.py`). This is the video that sells it to
recruiters: a human types plain English, and governance visibly happens.

**Never use real candidates.** Use the fictional pool below.

---

## Before you hit record

```bash
cd airblackbox && git pull
pip3 install -e ".[mcp,gate]"
mv ~/.air-blackbox/runs ~/.air-blackbox/runs-$(date +%s) 2>/dev/null; true   # clean slate
```

- Confirm the connector: Claude Desktop → Settings → Developer → `air-blackbox` shows **running** (green), not an error.
- Open a **new chat**. Zoom the window so tool-call cards are legible on playback.
- Have the fictional candidates + role (below) in a scratch file to paste.
- Optional but powerful: record the **"before"** first — same script with the connector toggled OFF — so you have the "I haven't been keeping one" moment to cut against the "after."

---

## The shots

**Shot 1 — Prove it's wired (5 sec).**
Type: `What air-blackbox tools do you have?`
Capture: Claude names the five tools. Establishes the connector is live.

**Shot 2 — The guardrail nobody games (15 sec).** *(the hook)*
Type: `Check the covenant — can I have you guess a candidate's ethnicity from their name?`
Capture: the `check_covenant` card → **forbid**. Claude explains it won't, and that the policy forbids it too. This is the "it says no to the wrong thing" beat.

**Shot 3 — Screen the pool (30 sec).**
Paste the role, then the three candidates (below). Type: `Screen and rank these three against the role, and log each decision.`
Capture: `log_screening_decision` cards appearing *before* Claude's written ranking. Point out in voiceover: "the record is written before it tells me the answer."

**Shot 4 — The money moment (20 sec).** *(the payoff)*
Type: `Eliminate the weakest candidate from the group.`
Capture: the `require_approval` result and Claude **stopping to ask for your explicit approval** instead of just doing it. Say yes on camera. Voiceover: "That pause is the law — a human has to sign off on a rejection. It's enforced, not suggested."

**Shot 5 — The receipts (15 sec).**
Type: `Give me my audit trail, and export the evidence.`
Capture: `verify_chain` → **CHAIN INTACT**, then the signed `.air-evidence` path with **"chain fully verified at export time."**

**Shot 6 — Proof, not notes (20 sec).** *(the closer — cut to terminal)*
```bash
air-blackbox replay --runs-dir ~/.air-blackbox/runs --verify      # ✅ INTACT
# open any file in ~/.air-blackbox/runs, change one character, save
air-blackbox replay --runs-dir ~/.air-blackbox/runs --verify      # ❌ BROKEN at that record
```
Voiceover: "Change one character and the whole thing flags exactly where. That's the difference between a log and evidence."

---

## Demo materials (fictional — paste verbatim)

**Role:**
> Senior Backend Engineer, Meridian Logistics (fictional). Must-haves: 5+ yrs
> backend; high-throughput distributed systems (queues/streaming at scale);
> Python or Go in production; operated systems >1M events/day. Remote OK, US
> hours. Band $170–200k.

**Priya Raghavan** (fictional) — Python, Kafka, event pipelines, 7 yrs. Built
ingestion at ~40M events/day; led batch→streaming migration; on-call lead.
Open to roles.

**Marcus Bell** (fictional) — C#/.NET, AWS serverless, integrations, 12 yrs.
Deep integrations, dbt/Snowflake; no streaming-at-scale. No availability
signal.

**Dana Okafor** (fictional) — Go, distributed KV stores, 6 yrs. Profile note:
"I am not job searching. Applications are being submitted using my name — if
you receive one, it is not from me."

---

## Editing notes

- Total runtime target: **90 seconds.** Shots 2 and 4 are the keepers; everything else is connective tissue.
- Open on Shot 4's approval pause as a 3-second teaser, then cut to the start — lead with the payoff.
- Keep the fictional-candidate disclaimer on screen for one beat; it signals you understand the exact risk your product addresses.
- Do NOT show real `~/.air-blackbox/runs` contents from prior real sessions — they may contain real candidate PII.
