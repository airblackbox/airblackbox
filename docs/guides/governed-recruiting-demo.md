# Governed Recruiting with Claude — Setup & Demo Guide

AI screening a candidate pool with every decision recorded into a
tamper-evident chain, human approval enforced on rejections, and a signed
evidence bundle at the end. Zero code for the person running it.

This guide is the full step-by-step process (Part 1), a scripted demo with
expected outputs at every beat (Part 2), independent verification (Part 3),
and every failure mode we hit in live field testing (Part 4).

> **Never demo with real people's profiles.** The candidate materials below
> are fictional. Screening real people creates real ADM records about them.

---

## Part 1 — Setup (one time, ~5 minutes)

**1. Install** (requires Python 3.10+):

```bash
git clone https://github.com/airblackbox/airblackbox.git
cd airblackbox
pip3 install -e ".[mcp,gate]"
which air-blackbox-mcp        # note this absolute path
pwd                           # note this too
```

**2. Connect to Claude Desktop.** Settings → Developer → Edit Config, add:

```json
{
  "mcpServers": {
    "air-blackbox": {
      "command": "<output of `which air-blackbox-mcp`>",
      "env": {
        "AIR_COVENANT": "<output of pwd>/sdk/air_blackbox/gate/examples/recruiting-screener.covenant.yaml"
      }
    }
  }
}
```

Both paths must be **absolute** — Claude Desktop does not inherit your
shell's PATH. Then quit Claude Desktop completely (Cmd+Q) and relaunch.

**3. Truth test.** New chat: *"What air-blackbox tools do you have?"*
You must see five tools named: `record_action`, `log_screening_decision`,
`check_covenant`, `verify_chain`, `export_evidence`. If not → Part 4.

**4. Clean slate for the demo.** Records accumulate in
`~/.air-blackbox/runs/`. Before a demo, archive any test debris:

```bash
mv ~/.air-blackbox/runs ~/.air-blackbox/runs-$(date +%s) 2>/dev/null; true
```

---

## Part 2 — The demo script

### Demo materials (fictional)

**The role** — paste when asked for a JD:

> Senior Backend Engineer, Meridian Logistics (fictional). Must-haves:
> 5+ years backend, high-throughput distributed systems (queues/streaming
> at scale), Python or Go in production, operated systems with >1M
> events/day. Nice-to-have: event-sourcing, on-call ownership. Remote OK,
> US hours. Band: $170–200k.

**Candidate A — Priya Raghavan (fictional)**

> Senior Backend Engineer — Python, Kafka, event pipelines. 7 yrs.
> Currently: staff-adjacent IC at a logistics SaaS; built ingestion
> handling ~40M events/day across 12 partners; led move from cron batch
> to streaming; on-call lead. Open to new roles (posted 2 weeks ago).

**Candidate B — Marcus Bell (fictional)**

> Senior Backend Engineer — C#/.NET, AWS serverless, integrations. 12 yrs.
> Currently: platform team at a healthcare martech co, 4 years. Deep in
> third-party integrations, dbt/Snowflake pipelines, no streaming-at-scale
> work. No availability signal.

**Candidate C — Dana Okafor (fictional)**

> Senior Backend Engineer — Go, distributed KV stores. 6 yrs. **Profile
> carries a pinned note: "I am not job searching. Applications are being
> submitted using my name — if you receive one, it is not from me."**

### The beats

**Beat 0 — governance is live.**
Say: *"Check the covenant — am I allowed to infer a candidate's ethnicity
from their name?"*
Expect: a `check_covenant` call → **forbid (explicit rule)**. This proves
the policy is loaded and distinguishing real rules from unknowns.

**Beat 1 — the screen.**
Paste the role, then the three candidates. Say: *"Screen and rank these
against the role. Log each decision."*
Expect: `log_screening_decision` calls (rank/score/hold) appearing
**before** Claude states conclusions, and Dana flagged on provenance —
the impersonation note — rather than judged on merit.

> Field note: decisive phrasing matters. "Log each decision" in the ask
> keeps informal analysis from slipping past the chain — in testing,
> chatty exploratory ranking sometimes went unlogged until the model
> corrected itself.

**Beat 2 — the money moment.**
Say: *"Eliminate the weakest candidate from my group."*
Expect the exact sequence field-tested live:

```
check_covenant: reject_candidate → require_approval (explicit rule)
log_screening_decision: <candidate> / reject → chain_hash=...
  → REQUIRES HUMAN APPROVAL before proceeding
```

Claude **stops and asks for your explicit yes**. This is GDPR Art. 22 /
EU AI Act Art. 14 human oversight, enforced by policy, not by mood. Give
the yes; Claude records the approval against the decision's hash.

**Beat 3 — the receipts.**
Say: *"Give me my audit trail."*
Expect: `verify_chain` → **"CHAIN INTACT: all N records verified. No
tampering detected."** — then say *"export the evidence"* and expect a
signed `.air-evidence` ZIP path, with **"chain fully verified at export
time"** in the response. The integrity verdict is stamped inside the
signed bundle itself; an export over a broken chain says so loudly
instead.

### The "before" (optional, brutal, recommended)

Run Beats 1–3 once with the connector toggled **off**. When you ask for
the audit trail, Claude will tell you the truth: it hasn't been keeping
one, and any reconstruction is partly invented. That transcript next to
the governed run is the entire product pitch with no slides.

---

## Part 3 — Independent verification (the point of it all)

The evidence must verify **without trusting Claude or the demo machine**:

```bash
# Verify the chain from the terminal:
air-blackbox replay --runs-dir ~/.air-blackbox/runs --verify
#   ✅ CHAIN INTACT - N records verified. No tampering detected.

# Prove tamper-evidence live (great closing move in a demo):
#   open any .air.json in ~/.air-blackbox/runs, change one character,
#   re-run the verify → ❌ CHAIN BROKEN at that exact record.

# The bundle self-verifies anywhere, no install needed:
unzip air-evidence-*.zip -d evidence && cd evidence
python3 verify.py --key "$(cat ~/.air-blackbox/runs/.air-signing-key 2>/dev/null || echo air-blackbox-default)"
```

---

## Part 4 — Troubleshooting (every one of these happened in real testing)

| Symptom | Cause | Fix |
|---|---|---|
| Tools listed in settings but Claude says it has none / "point me at the repo" | Server never launched: relative `command` path, or wrong module name (`air_blackbox_mcp` — it's `air_blackbox.mcp_server`) | Use the absolute `air-blackbox-mcp` binary path; check `~/Library/Logs/Claude/mcp-server-air-blackbox.log` |
| Every `check_covenant` returns forbid — even "say good morning" | Covenant is default-deny and matches exact snake_case names; free-text descriptions never match | Working as designed; the tools now answer "no rule (vocabulary miss)" and list valid names. Use the covenant's vocabulary |
| `CHAIN BROKEN` at some old record | Fossil records from before a server update — multiple genesis chains in one store | History can't be healed (that's the guarantee). Archive the store (Part 1, step 4) and start clean |
| `PARTIAL: N of M verified` | Unchained records (written without the trust layer) sitting in the same directory | Expected honesty, not an error — the verifiable portion is intact; move stray files out for a clean demo |
| Claude analyzes candidates but logs nothing | Behavioral drift on informal asks | Say "log each decision" explicitly; decisions phrased decisively ("eliminate…", "reject…") reliably trigger the gate |

---

## What this demo proves

1. **Recording**: every candidate-affecting decision written to a
   tamper-evident, HMAC-chained record — before the conclusion is stated.
2. **Enforcement**: forbidden actions blocked *and recorded*; rejections
   require an explicit human yes (Art. 14 / GDPR Art. 22).
3. **Proof**: a signed bundle carrying its own integrity verdict,
   verifiable by an auditor with no AIR install and no trust in anyone.

What it deliberately does **not** claim: that logging makes a decision
lawful, that it audits bias (that needs demographic outcome data the
gateway never sees), or that a covenant substitutes for a written role
spec. The model will ask for a JD before ranking on merit — let it.
