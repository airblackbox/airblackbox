#!/usr/bin/env python3
"""End-to-end AIR Blackbox demo: an AI recruiting screener under governance.

Scenario: a recruiting agent screens candidates for a role. Every LLM call
goes through the AIR gateway (recorded, chained, signed). A covenant declares
what the agent may do. We then:

  1. Route screening calls through the gateway (tamper-evident records)
  2. Verify the chain
  3. Export the audit trail to a queryable Parquet lake
  4. Run a candidate-outreach browser session under a covenant -> session passport
  5. Produce a signed evidence bundle a regulator/client can verify

Run:  python examples/recruiting_demo.py --gateway http://127.0.0.1:8080
It expects an AIR gateway running with RUNS_DIR pointing at --runs.
"""

import argparse
import json
import os
import sys
import urllib.request

CANDIDATES = [
    ("Alice Chen", "Senior Backend Engineer, 8y Go/Python, ex-Stripe"),
    ("Bob Martins", "Frontend Engineer, 3y React, bootcamp grad"),
    ("Carla Diaz", "Staff SRE, 11y, led 3 platform migrations"),
    ("Dan Okafor", "New-grad SWE, strong algorithms, no industry exp"),
    ("Erin Walsh", "Engineering Manager, 6y IC + 4y management"),
]


def screen_candidate(gateway, name, blurb):
    """One screening decision = one governed, recorded LLM call."""
    body = json.dumps({
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You screen candidates for a Senior Backend role. Reply with a one-line recommendation."},
            {"role": "user", "content": f"Candidate: {name}. Background: {blurb}. Screen for a Senior Backend Engineer role."},
        ],
    }).encode()
    req = urllib.request.Request(
        f"{gateway}/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "X-Session-ID": "recruiting-demo"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        run_id = resp.headers.get("x-run-id", "?")
        json.loads(resp.read())
    return run_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:8080")
    ap.add_argument("--runs", default="./demo-runs")
    args = ap.parse_args()

    print("STEP 1: Screen candidates through the AIR gateway")
    print("-" * 60)
    for name, blurb in CANDIDATES:
        run_id = screen_candidate(args.gateway, name, blurb)
        print(f"  screened {name:16s} -> recorded run {run_id[:8]}")
    print(f"\n  {len(CANDIDATES)} screening decisions recorded, each a signed "
          f"chain link.\n")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk"))

    print("STEP 2: Verify the audit chain")
    print("-" * 60)
    from air_blackbox.replay.engine import ReplayEngine
    # The verifier auto-discovers the gateway's generated .air-signing-key
    # from the runs directory - no key handling needed (zero-config).
    engine = ReplayEngine(runs_dir=args.runs)
    total = engine.load()
    result = engine.verify_chain()
    print(f"  {total} records loaded, chain "
          f"{'INTACT' if result.intact else 'BROKEN'}, "
          f"{result.verified_records} records verified.\n")

    print("STEP 3: Export the audit trail to a queryable lake")
    print("-" * 60)
    try:
        from air_blackbox.lake import export_records, verify_lake
        lake_dir = os.path.join(os.path.dirname(args.runs), "demo-lake")
        n = export_records(args.runs, lake_dir)
        lv = verify_lake(lake_dir, runs_dir=args.runs)
        print(f"  exported {n} records to Parquet; lake chain intact: "
              f"{lv.intact}\n")
    except ImportError:
        print("  (skipped: pip install air-blackbox[lake])\n")

    print("STEP 4: Candidate outreach as a governed browser session")
    print("-" * 60)
    from air_blackbox.passport import BrowserSession
    cov = os.path.join(os.path.dirname(__file__), "..", "sdk", "air_blackbox",
                       "gate", "examples", "linkedin-sourcing.covenant.yaml")
    with BrowserSession(runs_dir=os.path.join(os.path.dirname(args.runs),
                        "demo-passport"), covenant=cov,
                        signing_key="demo-key") as s:
        for name, _ in CANDIDATES[:3]:
            s.action("read_profile", target=f"linkedin.com/in/{name}")
            d = s.action("send_message", target=f"linkedin.com/in/{name}")
            if d.needs_approval:
                s.approve(d, approver="recruiter@demo")  # human clicks approve
        s.action("scrape_search_page")  # agent overreach -> blocked + flagged
    passport = s.passport()
    print(f"  verdict: {passport.verdict}")
    print(f"  actions: {passport.action_counts}")
    print(f"  human approvals: {passport.approvals}, blocked: {passport.blocked}")
    print(f"  chain intact: {passport.chain_intact}\n")

    print("STEP 5: Signed evidence bundle (hand to auditor/client)")
    print("-" * 60)
    bundle = s.export_passport()
    print(f"  passport bundle: {os.path.basename(bundle)}")
    print("\nDONE. Every decision recorded, chained, governed, and provable.")


if __name__ == "__main__":
    main()
