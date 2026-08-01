#!/usr/bin/env python3
"""AIR Blackbox proof harness: prove the guarantees, side by side with the
alternatives, against real attacks.

This is not a mock. Every AIR cell runs the actual product code (AuditChain,
ReplayEngine.verify_chain, the anchor head + RFC 3161 verification, and the
Gate covenant). The two baselines are honest, minimal implementations of what
you get WITHOUT AIR:

  - "plain log"  : an append-only list. No integrity, no policy. (What most
                   teams have.)
  - "hash chain" : a genuine HMAC-SHA256 audit chain with NO external anchor.
                   This is a fair, non-strawman stand-in for a well-built
                   tamper-evident log (e.g. a Rust HMAC hash-chain product):
                   it catches edits and deletions, but the operator holds the
                   key, so a full rewrite-and-re-sign passes.
  - "AIR Blackbox": the hash chain PLUS the external timestamp anchor, the
                   covenant, and public-key-verifiable evidence.

Run it:  python bench/proof/prove.py
Exit code 0 iff AIR delivers every guarantee (so this doubles as a CI
regression on the product's core claims).

The anchor rows use a throwaway local openssl TSA, so the whole thing runs
offline. If openssl is absent, those rows report SKIP rather than fake a pass.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk"))

from air_blackbox.trust.chain import AuditChain
from air_blackbox.replay.engine import ReplayEngine
from air_blackbox.anchor.head import compute_head
from air_blackbox.anchor.tsa import make_query, verify_anchor_bytes
from air_blackbox.gate.covenant import Covenant, RuleAction

SECRET = "operator-held-signing-key"
HAVE_OPENSSL = shutil.which("openssl") is not None

# Outcome labels.
DETECTED = "DETECTED"   # tampering caught
MISSED = "MISSED"       # tampering NOT caught (bad)
BLOCKED = "BLOCKED"     # action refused before execution
RECORDED = "RECORDED"   # action logged but allowed to happen
YES = "YES"
NO = "NO"
NA = "n/a"
SKIP = "SKIP"


# --------------------------------------------------------------------------
# A throwaway RFC 3161 TSA (CA + timestamping cert) so the anchor runs offline.
# --------------------------------------------------------------------------
class LocalTSA:
    def __init__(self, d):
        self.dir = d
        os.makedirs(d, exist_ok=True)
        self.ca_pem = os.path.join(d, "ca.pem")
        self._setup()

    def _o(self, *a):
        return subprocess.run(["openssl", *a], capture_output=True,
                              cwd=self.dir, timeout=30)

    def _setup(self):
        self._o("req", "-x509", "-newkey", "ec",
                "-pkeyopt", "ec_paramgen_curve:P-256", "-keyout", "ca.key",
                "-out", "ca.pem", "-nodes", "-subj", "/CN=Proof Root CA",
                "-days", "2")
        self._o("req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                "-keyout", "tsa.key", "-out", "tsa.csr", "-nodes",
                "-subj", "/CN=Proof TSA")
        with open(os.path.join(self.dir, "tsa.ext"), "w") as f:
            f.write("extendedKeyUsage=critical,timeStamping\n")
        self._o("x509", "-req", "-in", "tsa.csr", "-CA", "ca.pem",
                "-CAkey", "ca.key", "-CAcreateserial", "-out", "tsa.pem",
                "-days", "2", "-extfile", "tsa.ext")
        with open(os.path.join(self.dir, "tsa.conf"), "w") as f:
            f.write("[tsa]\ndefault_tsa = c\n[c]\nserial = ./serial\n"
                    "crypto_device = builtin\nsigner_cert = ./tsa.pem\n"
                    "certs = ./ca.pem\nsigner_key = ./tsa.key\n"
                    "signer_digest = sha256\ndefault_policy = 1.2.3.4.1\n"
                    "digests = sha256, sha384, sha512\naccuracy = secs:1\n"
                    "ordering = yes\ntsa_name = yes\ness_cert_id_chain = no\n")
        with open(os.path.join(self.dir, "serial"), "w") as f:
            f.write("01\n")

    def reply(self, head_hex):
        with open(os.path.join(self.dir, "req.tsq"), "wb") as f:
            f.write(make_query(head_hex))
        self._o("ts", "-reply", "-config", "tsa.conf", "-queryfile", "req.tsq",
                "-out", "resp.tsr")
        with open(os.path.join(self.dir, "resp.tsr"), "rb") as f:
            return f.read()


# --------------------------------------------------------------------------
# Baselines (honest, minimal).
# --------------------------------------------------------------------------
def plain_log_write(records):
    """A plain append-only log has no verification. Tampering is never caught."""
    return list(records)  # a mutable list; that is the whole "integrity model"


def hash_chain_write(runs_dir, records):
    """A genuine HMAC-SHA256 chain, operator-held key, NO external anchor."""
    chain = AuditChain(runs_dir=runs_dir, signing_key=SECRET)
    for r in records:
        chain.write(dict(r))


def hash_chain_intact(runs_dir):
    eng = ReplayEngine(runs_dir=runs_dir)
    eng.load()
    return eng.verify_chain(signing_key=SECRET).intact


# --------------------------------------------------------------------------
# The genuine, untampered baseline state.
# --------------------------------------------------------------------------
def genuine_records():
    return [
        {"run_id": f"run-{i:03d}", "action": a,
         "timestamp": f"2026-08-01T00:00:{i:02d}Z", "candidate": f"cand-{i}"}
        for i, a in enumerate(
            ["read_profile", "score_candidate", "advance_candidate",
             "read_profile", "score_candidate"])
    ]


def build_genuine(root, tsa):
    """Write a genuine chain and anchor its head. Returns (runs_dir, tsr)."""
    runs = os.path.join(root, "runs")
    hash_chain_write(runs, genuine_records())
    tsr = tsa.reply(compute_head(runs)) if tsa else None
    return runs, tsr


# --------------------------------------------------------------------------
# Scenarios. Each returns {system: outcome}.
# --------------------------------------------------------------------------
def scenario_edit(root, tsa, tsr):
    """Edit a past record's content in place."""
    out = {}
    # plain log: mutate the list; nothing verifies it.
    log = plain_log_write(genuine_records())
    log[1]["candidate"] = "TAMPERED"
    out["plain log"] = MISSED

    # hash chain: mutate a record on disk, re-verify with the key.
    runs, _ = build_genuine(os.path.join(root, "hc_edit"), None)
    f = sorted(os.listdir(runs))[1]
    p = os.path.join(runs, f)
    rec = json.load(open(p))
    rec["candidate"] = "TAMPERED"
    json.dump(rec, open(p, "w"))
    out["hash chain"] = DETECTED if not hash_chain_intact(runs) else MISSED

    # AIR: same tamper; verify_chain catches it (the anchor would too).
    runs2, _ = build_genuine(os.path.join(root, "air_edit"), None)
    f2 = sorted(os.listdir(runs2))[1]
    p2 = os.path.join(runs2, f2)
    rec2 = json.load(open(p2))
    rec2["candidate"] = "TAMPERED"
    json.dump(rec2, open(p2, "w"))
    out["AIR Blackbox"] = DETECTED if not hash_chain_intact(runs2) else MISSED
    return out


def scenario_delete(root, tsa, tsr):
    """Delete a record from the middle of the history."""
    out = {"plain log": MISSED}
    for label, sub in (("hash chain", "hc_del"), ("AIR Blackbox", "air_del")):
        runs, _ = build_genuine(os.path.join(root, sub), None)
        os.remove(os.path.join(runs, sorted(os.listdir(runs))[2]))
        out[label] = DETECTED if not hash_chain_intact(runs) else MISSED
    return out


def scenario_rewrite(root, tsa, tsr):
    """Rewrite the ENTIRE history and re-sign it with the operator-held key.
    This is the case a plain hash chain cannot catch."""
    out = {"plain log": MISSED}

    # A fabricated history, cleanly re-chained with the same secret the
    # operator holds. verify_chain(SECRET) will pass -> MISSED for a chain.
    fabricated = [
        {"run_id": f"run-{i:03d}", "action": "advance_candidate",
         "timestamp": f"2026-08-01T00:00:{i:02d}Z", "candidate": "COVER-UP"}
        for i in range(5)]

    runs = os.path.join(root, "hc_rewrite")
    hash_chain_write(runs, fabricated)
    out["hash chain"] = MISSED if hash_chain_intact(runs) else DETECTED

    # AIR: the chain still verifies (re-signed), but the anchor countersigned
    # the ORIGINAL head. Re-derive the head over the rewritten records and
    # check it against that timestamp.
    if not tsa or tsr is None:
        out["AIR Blackbox"] = SKIP
        return out
    runs2 = os.path.join(root, "air_rewrite")
    hash_chain_write(runs2, fabricated)
    chain_ok = hash_chain_intact(runs2)              # True: re-signed cleanly
    new_head = compute_head(runs2)
    anchor_ok, _ = verify_anchor_bytes(new_head, tsr, ca_pem=tsa.ca_pem)
    # Detected iff the chain looks fine but the anchor rejects the new head.
    out["AIR Blackbox"] = DETECTED if (chain_ok and not anchor_ok) else MISSED
    return out


def scenario_forbidden(root, tsa, tsr):
    """An agent attempts a forbidden action (inferring protected attributes)."""
    cov = Covenant.from_yaml_string(
        "agent: screener\nversion: '1'\nrules:\n"
        "  - permit: read_profile\n"
        "  - forbid: infer_protected_attributes\n")
    air = BLOCKED if cov.evaluate("infer_protected_attributes") == RuleAction.FORBID else MISSED
    # A log or a bare chain records the call; neither refuses it.
    return {"plain log": RECORDED, "hash chain": RECORDED, "AIR Blackbox": air}


def scenario_verify_no_secret(root, tsa, tsr):
    """Can a third party verify integrity WITHOUT the operator's secret?"""
    out = {"plain log": NA, "hash chain": NO}  # HMAC verify needs the secret
    if not tsa or tsr is None:
        out["AIR Blackbox"] = SKIP
        return out
    runs, _ = build_genuine(os.path.join(root, "air_nosecret"), None)
    head = compute_head(runs)                          # key-free
    ok, _ = verify_anchor_bytes(head, tsr, ca_pem=tsa.ca_pem)  # no secret used
    out["AIR Blackbox"] = YES if ok else NO
    return out


SCENARIOS = [
    ("edit a past record", scenario_edit),
    ("delete a record from history", scenario_delete),
    ("rewrite + re-sign entire history", scenario_rewrite),
    ("forbidden action attempted", scenario_forbidden),
    ("verify with no secret", scenario_verify_no_secret),
]

SYSTEMS = ["plain log", "hash chain", "AIR Blackbox"]

# What AIR must deliver for the proof to pass.
AIR_EXPECTED = {
    "edit a past record": DETECTED,
    "delete a record from history": DETECTED,
    "rewrite + re-sign entire history": DETECTED,
    "forbidden action attempted": BLOCKED,
    "verify with no secret": YES,
}


def collect():
    """Run every scenario and return [(name, {system: outcome})]."""
    with tempfile.TemporaryDirectory() as root:
        tsa = LocalTSA(os.path.join(root, "tsa")) if HAVE_OPENSSL else None
        _, tsr = build_genuine(os.path.join(root, "genuine"), tsa)

        rows = []
        for name, fn in SCENARIOS:
            sub = os.path.join(root, name.replace(" ", "_").replace("+", ""))
            os.makedirs(sub, exist_ok=True)
            rows.append((name, fn(sub, tsa, tsr)))
    return rows


def run():
    rows = collect()

    # Print the scorecard.
    w = max(len(n) for n, _ in rows) + 2
    header = "attack".ljust(w) + "".join(s.ljust(15) for s in SYSTEMS)
    print("\nAIR Blackbox proof harness  (real attacks, real code)\n")
    print(header)
    print("-" * len(header))
    for name, res in rows:
        line = name.ljust(w) + "".join(res.get(s, "?").ljust(15) for s in SYSTEMS)
        print(line)
    if not HAVE_OPENSSL:
        print("\n(openssl not found: anchor-dependent rows reported SKIP)")

    # Verdict: AIR must meet every expected guarantee (SKIP is tolerated only
    # when openssl is unavailable).
    failures = []
    for name, res in rows:
        got = res.get("AIR Blackbox")
        want = AIR_EXPECTED[name]
        if got == want:
            continue
        if got == SKIP and not HAVE_OPENSSL:
            continue
        failures.append(f"{name}: AIR expected {want}, got {got}")

    print()
    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("PASS: AIR Blackbox delivered every guarantee against every attack.")
    if HAVE_OPENSSL:
        # Sanity: the comparison must be real, not rigged. The bare hash chain
        # MUST miss the rewrite, or the harness is not proving anything.
        rewrite = dict(rows)["rewrite + re-sign entire history"]
        assert rewrite["hash chain"] == MISSED, "baseline unexpectedly caught rewrite"
    return 0


if __name__ == "__main__":
    sys.exit(run())
