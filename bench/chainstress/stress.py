#!/usr/bin/env python3
"""Stress test the AIR gateway audit chain under concurrent load."""
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.request

GATEWAY = "http://127.0.0.1:8080"
RUNS = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 500
CONCURRENCY = int(sys.argv[3]) if len(sys.argv) > 3 else 50

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk"))
from air_blackbox.replay.engine import ReplayEngine


def call(i):
    body = json.dumps({"model": "gpt-4", "messages": [
        {"role": "user", "content": f"screen candidate #{i}"}]}).encode()
    req = urllib.request.Request(f"{GATEWAY}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
    return (time.monotonic() - t0) * 1000


print(f"Firing {N} requests at concurrency {CONCURRENCY}...")
t0 = time.monotonic()
lat = []
with cf.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    for ms in ex.map(call, range(N)):
        lat.append(ms)
wall = time.monotonic() - t0

lat.sort()
print(f"  {N} requests in {wall:.2f}s = {N/wall:.0f} req/s")
print(f"  latency p50={lat[len(lat)//2]:.1f}ms p95={lat[int(len(lat)*0.95)]:.1f}ms "
      f"p99={lat[int(len(lat)*0.99)]:.1f}ms max={lat[-1]:.1f}ms")

# Records land asynchronously; wait for the background writers to drain.
print("Waiting for async record writes to settle...")
for _ in range(30):
    time.sleep(1)
    n = len([f for f in os.listdir(RUNS) if f.endswith(".air.json")])
    if n >= N:
        break
print(f"  {n}/{N} records on disk")

print("Verifying the full chain...")
t0 = time.monotonic()
engine = ReplayEngine(runs_dir=RUNS)
total = engine.load()
result = engine.verify_chain()
vt = time.monotonic() - t0
print(f"  {total} records, chain {'INTACT' if result.intact else 'BROKEN'}, "
      f"{result.verified_records} verified in {vt:.2f}s")

# Check sequence completeness: no gaps, no dupes.
seqs = sorted(r.get("chain_seq", 0) for r in engine._raw_records)
expected = list(range(1, total + 1))
gaps = set(expected) - set(seqs)
dupes = len(seqs) - len(set(seqs))
print(f"  chain_seq: min={seqs[0]} max={seqs[-1]} gaps={len(gaps)} dupes={dupes}")

ok = (result.intact and result.verified_records == total
      and not gaps and not dupes and total == N)
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
