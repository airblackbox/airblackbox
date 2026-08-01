#!/usr/bin/env python3
"""AIR Blackbox — "Audit Day": the operator-rewrite catch, in a hiring frame.

This is the 90-second story you show a recruiting design partner. It is the
governed-screening demo's missing final act: not "someone edited one record"
(a plain hash chain catches that too), but "someone rewrote the ENTIRE hiring
history to survive an audit, and re-signed it" — the case only AIR catches,
because the chain head was countersigned by an outside witness whose key the
company does not hold.

Nothing here is mocked. It runs the real AuditChain, the real covenant, the
real key-free chain head, and real RFC 3161 anchor verification (against a
throwaway local openssl TSA so it runs offline). The candidates are fictional;
never demo with real people.

    python demo/hiring_audit_day.py

Exit 0 iff the cover-up is caught. See bench/proof/prove.py for the same
guarantee as a bare scorecard, and docs/security/cryptographic-posture.md for
the honest limit (a re-anchored rewrite needs the M2 public log).
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# Reuse the proof harness's real anchor code — one tested implementation, no copy.
sys.path.insert(0, os.path.join(HERE, "..", "bench", "proof"))
sys.path.insert(0, os.path.join(HERE, "..", "sdk"))

import prove  # LocalTSA + the real AIR imports live here
from air_blackbox.trust.chain import AuditChain
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.anchor.head import compute_head
from air_blackbox.anchor.tsa import verify_anchor_bytes
from air_blackbox.gate.covenant import Covenant, RuleAction

BOLD, DIM, GREEN, RED, YEL, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m")
SECRET = "company-held-signing-key"   # the key the operator holds

# Fictional. Role: Senior Backend Engineer, Meridian Logistics (fictional).
GENUINE = [
    {"run_id": "run-001", "action": "read_profile",
     "candidate": "Priya Raghavan",
     "detail": "7 yrs, Kafka, ~40M events/day ingestion"},
    {"run_id": "run-002", "action": "advance_candidate",
     "candidate": "Priya Raghavan",
     "detail": "direct match on streaming-at-scale; advance to phone screen"},
    {"run_id": "run-003", "action": "read_profile",
     "candidate": "Marcus Bell",
     "detail": "12 yrs, C#/.NET, deep integrations"},
    {"run_id": "run-004", "action": "reject_candidate",
     "candidate": "Marcus Bell",
     "detail": "no streaming-at-scale experience; human-approved 2026-02-09"},
]


def beat(title):
    print(f"\n{BOLD}{title}{RESET}")


def line(s):
    print("    " + s.replace("\n", "\n    "))


def write_chain(runs, records):
    chain = AuditChain(runs_dir=runs, signing_key=SECRET)
    for r in records:
        chain.write(dict(r))


def chain_self_check(runs):
    eng = ReplayEngine(runs_dir=runs)
    eng.load()
    return eng.verify_chain(signing_key=SECRET).intact


def main():
    if not prove.HAVE_OPENSSL:
        print("openssl not found — the anchor act needs it. Install openssl.")
        return 2

    print("=" * 72)
    print("  AIR BLACKBOX — AUDIT DAY   (real engine, fictional candidates)")
    print("  Role: Senior Backend Engineer, Meridian Logistics (fictional)")
    print("  Setting: NYC LL144 / Colorado SB 24-205 keep hiring AI on the record")
    print("=" * 72)

    with tempfile.TemporaryDirectory() as root:
        tsa = prove.LocalTSA(os.path.join(root, "tsa"))

        # ---- ACT 1 — the agent works, on the record ----------------------
        beat("[Act 1]  Back in February: the AI agent screens the pipeline")
        runs = os.path.join(root, "runs")
        write_chain(runs, GENUINE)
        line(f"{GREEN}✓{RESET} 4 decisions written to a tamper-evident chain:")
        for r in GENUINE:
            line(f"    · {r['action']:<18} {r['candidate']:<16} — {r['detail']}")

        beat("[Act 1b]  A recruiter asks the agent to guess ethnicity from a name")
        cov = Covenant.from_yaml_string(
            "agent: screener\nversion: '1'\nrules:\n"
            "  - permit: read_profile\n"
            "  - permit: advance_candidate\n"
            "  - forbid: infer_protected_attributes\n")
        decision = cov.evaluate("infer_protected_attributes")
        blocked = decision == RuleAction.FORBID
        line(f"{GREEN if blocked else RED}{'✓ BLOCKED' if blocked else '✗ allowed'}"
             f"{RESET} — the covenant forbids it before it can run, and the "
             f"attempt itself is on the record.")

        # ---- ACT 2 — export day: anchor to an outside witness -------------
        beat("[Act 2]  Export day: the chain head is anchored to an outside witness")
        head = compute_head(runs)                       # key-free commitment
        tsr = tsa.reply(head)                            # external TSA countersigns
        line(f"chain head   {head[:32]}…")
        line(f"{GREEN}✓{RESET} A timestamp authority countersigned that head with "
             f"{BOLD}its own key{RESET} — a key Meridian does not hold.")

        # ---- ACT 3 — audit day: the cover-up ------------------------------
        beat("[Act 3]  Six months later: a bias complaint. Someone rewrites history.")
        rewritten = [dict(r) for r in GENUINE]
        for r in rewritten:
            if r["action"] == "reject_candidate":
                r["detail"] = ("failed structured technical panel, 3 interviewers "
                               "— consensus reject")   # the forgery
        runs2 = os.path.join(root, "runs_rewritten")
        write_chain(runs2, rewritten)                   # re-signed with the held key
        line(f"{RED}✗{RESET} Marcus's rejection reason was changed, and the whole "
             f"history re-signed with the company's own key.")

        # The company's OWN audit log now passes its self-check. Scary.
        internal_ok = chain_self_check(runs2)
        line(f"{RED if internal_ok else GREEN}"
             f"{'✗ internal hash-chain self-check: PASSES' if internal_ok else '✓ caught'}"
             f"{RESET}  ← a plain hash-chain product would stop here and call it clean.")

        # AIR: re-derive the head over the rewritten records, check the anchor.
        new_head = compute_head(runs2)
        anchor_ok, _ = verify_anchor_bytes(new_head, tsr, ca_pem=tsa.ca_pem)
        caught = internal_ok and not anchor_ok
        beat("[The catch]  AIR checks the rewritten head against the outside witness")
        line(f"anchored head  {head[:32]}…")
        line(f"rewritten head {new_head[:32]}…")
        if caught:
            line(f"{RED}✗ REWRITE DETECTED{RESET} — the new head does not match "
                 f"what the timestamp authority signed in February.")
            print(f"\n  {GREEN}{BOLD}You can still lie. You just can't do it "
                  f"invisibly.{RESET}")
            print(f"  {DIM}The company's own logs were rewritten cleanly. The "
                  f"outside witness is what gave it away.{RESET}\n")
            return 0
        line(f"{RED}the cover-up was NOT caught — this should never happen{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
