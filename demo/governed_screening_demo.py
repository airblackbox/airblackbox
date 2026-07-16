#!/usr/bin/env python3
"""AIR Blackbox — governed candidate screening, live against the real engine.

Runs the exact tool sequence Claude Desktop calls, with fictional candidates,
and prints every result: covenant enforcement, logged decisions, the human
approval gate, chain verification, a signed evidence export, and a live tamper
test that breaks the chain at the exact record.

    pip install air-blackbox[mcp,gate]
    python demo/governed_screening_demo.py

Nothing here is mocked. The candidates are fictional; never demo with real
people's profiles.
"""

import glob
import json
import os
import tempfile

BOLD, DIM, GREEN, RED, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[0m"


def beat(title):
    print(f"\n{BOLD}{title}{RESET}")


def call(label, out):
    print(f"  {DIM}▸ {label}{RESET}")
    print("    " + out.replace("\n", "\n    "))


def main():
    # Isolated runs dir + the shipped recruiting covenant, so the demo is
    # reproducible and never touches a real store.
    runs = tempfile.mkdtemp(prefix="air-demo-")
    os.environ["AIR_RUNS_DIR"] = runs
    here = os.path.dirname(os.path.abspath(__file__))
    os.environ["AIR_COVENANT"] = os.path.join(
        here, "..", "sdk", "air_blackbox", "gate", "examples",
        "recruiting-screener.covenant.yaml")

    from air_blackbox import mcp_server as m

    print("=" * 72)
    print("  GOVERNED CANDIDATE SCREENING  —  real engine, fictional candidates")
    print("  Role: Senior Backend Engineer (high-throughput distributed systems)")
    print("=" * 72)

    beat("[0] Prove the policy is loaded and actually governing")
    call('check_covenant("infer_protected_attributes")',
         m.check_covenant("infer_protected_attributes"))

    beat("[1] Screen & rank — logged BEFORE the conclusion is stated")
    call('log_screening_decision("Priya Raghavan", "rank", ...)',
         m.log_screening_decision(
             "Priya Raghavan", "rank",
             "40M events/day Kafka ingestion, batch->streaming migration, "
             "on-call lead — direct match"))
    print(f"    {DIM}>>> recruiter: \"approve that ranking\"{RESET}")
    call('record_action("human_approval", ...)',
         m.record_action("human_approval",
                         detail="rank Priya Raghavan approved by user",
                         category="screening"))

    beat("[2] A forbidden action is attempted — blocked AND recorded")
    call('record_action("infer_protected_attributes", ...)',
         m.record_action("infer_protected_attributes",
                         detail="guess ethnicity from candidate name"))

    beat("[3] 'Eliminate the weakest' — the rejection stops for human approval")
    call('check_covenant("reject_candidate")', m.check_covenant("reject_candidate"))
    call('log_screening_decision("Dana Okafor", "reject", ...)',
         m.log_screening_decision(
             "Dana Okafor", "reject",
             "Provenance only: profile carries an impersonation notice; "
             "NOT a merit judgment"))
    print(f"    {DIM}>>> recruiter: \"yes, approve\"{RESET}")
    call('record_action("human_approval", ...)',
         m.record_action("human_approval",
                         detail="reject_candidate for Dana Okafor approved by user",
                         category="screening"))

    beat("[4] The receipts — verify and export")
    call("verify_chain()", m.verify_chain())
    call("export_evidence()", m.export_evidence())

    beat("[5] Independent proof — the human-readable chain")
    rows = []
    for p in glob.glob(os.path.join(runs, "*.air.json")):
        with open(p) as f:
            rows.append(json.load(f))
    rows.sort(key=lambda r: r.get("chain_seq", 0))
    print(f"    {'seq':>3}  {'action':<28} {'decision':<16} detail")
    print("    " + "-" * 78)
    for r in rows:
        detail = (r.get("detail") or "")[:30]
        print(f"    {r.get('chain_seq'):>3}  {r.get('action', ''):<28} "
              f"{r.get('covenant_decision', ''):<16} {detail}")

    beat("[6] TAMPER TEST — falsify one stored record, then re-verify")
    from air_blackbox.replay.engine import ReplayEngine
    for p in glob.glob(os.path.join(runs, "*.air.json")):
        with open(p) as f:
            r = json.load(f)
        if r.get("action") == "reject_candidate":
            r["detail"] = "APPROVED ON MERIT - top candidate"   # the forgery
            with open(p, "w") as f:
                json.dump(r, f)
            print(f"    {RED}✗ tampered record seq {r.get('chain_seq')}: "
                  f"rewrote the rejection rationale{RESET}")
            break
    eng = ReplayEngine(runs_dir=runs)
    eng.load()
    v = eng.verify_chain()
    print(f"    {RED}✗ verify_chain now: CHAIN BROKEN at record "
          f"{v.first_break_at} — {v.verified_records} verified before the "
          f"break{RESET}")
    print(f"\n  {GREEN}The forgery is caught at the exact record. "
          f"It's not notes — it's proof.{RESET}\n")
    print(f"  {DIM}Records were written to {runs}{RESET}")


if __name__ == "__main__":
    main()
