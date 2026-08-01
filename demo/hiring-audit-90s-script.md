# 90-Second Demo — "Audit Day" (the operator-rewrite catch)

The recording script for `demo/hiring_audit_day.py`. This is the one that lands
with a recruiting design partner, because it dramatizes the single thing no
other audit-log tool does: it catches a company that rewrites its *entire*
hiring history to survive a bias audit.

The companion Claude Desktop video is `demo/desktop-demo-shotlist.md` (what it
*feels* like to use). This one is the terminal proof of the guarantee — record
it second, or splice the "REWRITE DETECTED" beat into the Desktop cut as the
closer.

**Never use real candidates.** The script ships fictional ones.

---

## Before you hit record

```bash
cd airblackbox && git pull
pip3 install -e ".[mcp,gate]"      # needs openssl on PATH for the anchor act
python3 demo/hiring_audit_day.py   # dry run once; confirm it ends EXIT=0
```

Terminal, dark theme, big font. One clean run top to bottom — the output *is*
the storyboard. Total read time at a calm pace is ~90 seconds.

---

## The voiceover (timed to the output)

**0:00 — the setup (title card).**
> "This is an AI agent screening candidates for a backend role. NYC and
> Colorado now require you to keep tamper-evident records of hiring AI. So we
> do — here's what that actually buys you."

**0:12 — Act 1, the record.**
> "Back in February the agent read four profiles and made four decisions —
> advanced Priya, rejected Marcus for a real reason. Every one written to a
> signed chain as it happened, before the agent even stated its conclusion."

**0:25 — Act 1b, the guardrail (the hook).**
> "A recruiter asks it to guess someone's ethnicity from their name. The
> policy forbids that — so it's blocked before it can run, *and* the attempt
> is itself on the record. It says no to the wrong thing, and it can't
> pretend the question was never asked."

**0:40 — Act 2, the outside witness.**
> "When the records are exported, the top of the chain gets countersigned by
> an external timestamp authority — a key the company doesn't hold. Remember
> that head number."

**0:52 — Act 3, the cover-up (the tension).**
> "Six months later a rejected candidate files a bias complaint. Someone with
> database access rewrites Marcus's rejection reason and re-signs the whole
> history with the company's own key. And watch — their internal hash-chain
> check comes back **clean**. A normal audit-log product stops right here and
> tells the auditor everything's fine."

**1:08 — the catch (the payoff). Let the two head numbers sit on screen.**
> "But AIR re-derives the head over the rewritten records and checks it
> against what the outside witness signed in February. They don't match.
> **Rewrite detected.** The company's own logs were rewritten perfectly — the
> outside witness is what gave it away."

**1:20 — the line.**
> "You can still lie. You just can't do it invisibly. *That's* the difference
> between a log and evidence."

**1:28 — stop.**

---

## Editing notes

- The two keeper beats are **1b (blocked)** and **the catch (rewrite
  detected)**. If you cut to 60s, keep those two and Act 2.
- Open on "REWRITE DETECTED" as a 3-second cold teaser, then hard-cut to the
  title and play it straight. Lead with the payoff.
- Put the two head hashes side by side on screen at 1:08 and don't rush them —
  the mismatch is the whole argument, visually.
- Keep "fictional candidates" legible for a beat. It signals you understand the
  exact risk your product addresses.
- Be honest about the limit if asked on the call: this catches a rewrite that
  wasn't re-anchored. A rewrite plus a *fresh* timestamp is caught by the
  public transparency log (M2 — opt-in with `AIR_REKOR=1`; old log entries
  can never be removed, so `audit_public_log` catches even that). It's
  written down in `docs/security/cryptographic-posture.md` — that honesty is
  part of the pitch.

---

## Drop-in DM (paste, then swap the bracketed bits)

> Hey [name] — you mentioned [LL144 / audit-readiness / "what happens when a
> candidate complains"]. Built a 90-second thing I'd love your gut check on.
>
> It's an AI agent screening a (fictional) backend pipeline. Two moments:
> (1) it's asked to infer a protected attribute and the policy blocks it before
> it runs, and (2) six months later someone rewrites the whole hiring history
> to bury a rejection reason and re-signs it — their own audit log passes
> clean, and we still catch it, because the record was countersigned by an
> outside witness they don't control.
>
> It's not a mockup — you can run the exact thing:
> `python demo/hiring_audit_day.py`. 30 seconds, no signup.
>
> Worth 15 min to show you where it'd fit your process? Mostly want to know if
> "you can still lie, but not invisibly" is the guarantee your legal team
> actually wants, or the wrong one.

---

## What's real here (for the technical follow-up)

Every claim in the video runs product code, not a script that prints nice
words:

- the **chain** is `air_blackbox.trust.chain.AuditChain` (HMAC-SHA256);
- the **block** is `air_blackbox.gate.covenant.Covenant.evaluate` returning
  `FORBID`;
- the **anchor** is the real key-free `compute_head` + RFC 3161
  `verify_anchor_bytes`, against a throwaway local `openssl` TSA so it runs
  offline;
- the same guarantee is regression-tested in CI via `bench/proof/prove.py` and
  `sdk/tests/test_proof_harness.py`, which also assert a bare hash chain still
  *misses* the rewrite — so the comparison can never quietly become rigged.
