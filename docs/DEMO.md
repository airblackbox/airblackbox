# AIR Blackbox — End-to-End Demo & Operator Guide

A worked recruiting scenario that exercises the whole product: a governed
AI screener, a tamper-evident audit chain, a queryable lake, a covenant-
governed browser session, and a signed evidence bundle. Every command below
was run against the real gateway; the numbers in "Stress test" are measured,
not estimated.

---

## 0. Prerequisites

```bash
# Python SDK + optional extras used here
pip install -e ".[lake]"          # from the repo root (adds pyarrow)

# Build the Go gateway and the mock provider (no real API key needed to demo)
go build -o /tmp/air-gateway ./cmd/gateway
go build -o /tmp/air-mockllm ./bench/mockllm
```

---

## 1. Start the gateway

The gateway is an OpenAI-compatible reverse proxy. Point it at any provider;
here we use the bundled mock so the demo is self-contained and free.

```bash
/tmp/air-mockllm &                       # fake provider on :9100

LISTEN_ADDR=:8080 \
PROVIDER_URL=http://127.0.0.1:9100 \
RUNS_DIR=./demo-runs \
/tmp/air-gateway &
```

No `TRUST_SIGNING_KEY` is set, so the gateway generates a random key and
writes it to `demo-runs/.air-signing-key` (mode 0600). Verification tooling
auto-discovers it — zero key handling. In production, set `TRUST_SIGNING_KEY`
from your secret store instead.

**Point your agent at it:** change one line in your code.

```python
client = OpenAI(base_url="http://localhost:8080/v1")   # that's the whole change
```

---

## 2. Run the scenario

```bash
python examples/recruiting_demo.py --gateway http://127.0.0.1:8080 --runs ./demo-runs
```

What it does, step by step:

| Step | What happens | What you get |
|------|--------------|--------------|
| 1 | 5 candidates screened via `/v1/chat/completions` | 5 signed `.air.json` records, HMAC-chained |
| 2 | `ReplayEngine.verify_chain()` | `chain INTACT, 5 records verified` |
| 3 | `lake.export_records` + `verify_lake` | Parquet dataset, verified in-place |
| 4 | Outreach as a `BrowserSession` under a covenant | session passport (read permitted, sends human-approved, scrape **blocked**) |
| 5 | `export_passport()` | signed `.air-evidence` ZIP for an auditor/client |

Step 4's verdict is `VIOLATIONS` **on purpose** — the demo agent attempts a
`scrape_search_page` and the covenant blocks it. That blocked attempt is
itself recorded: the governance catching overreach is the point.

---

## 3. Inspect and prove

```bash
# Human-readable timeline of every screening decision
air-blackbox replay --runs-dir ./demo-runs

# Prove nothing was altered (auto-discovers the signing key)
air-blackbox replay --runs-dir ./demo-runs --verify
#   ✅ CHAIN INTACT - 5 records verified. No tampering detected.

# Query the audit trail as data
air-blackbox lake export --runs-dir ./demo-runs -o ./demo-lake
air-blackbox lake verify -o ./demo-lake
```

Try tampering to see detection fire: edit any `model` field in a
`demo-runs/*.air.json`, then re-run `--verify`. It reports the exact record
that broke and refuses to certify the chain.

---

## 4. Governance surfaces

The same covenant model, chain, and evidence bundle work in three places:

- **Sandbox** (pre-deployment): `air-blackbox sandbox-run --covenant policy.yaml --gateway-bin /tmp/air-gateway -- python your_agent.py` — the agent graduates only if the recorded evidence obeys the covenant.
- **Claude-native** (MCP): `air-blackbox-mcp` — connect it to Claude Desktop or, via `deploy/mcp/`, to claude.ai. `record_action` governs and records each step Claude takes.
- **Browser session** (logged-in apps): `air_blackbox.passport.BrowserSession` — governs any driver, issues a session passport.

---

## 5. Stress test (measured)

```bash
# with the gateway running against RUNS_DIR=./stress-runs
python bench/chainstress/stress.py ./stress-runs 2000 100   # N=2000, concurrency=100
```

Results on a single node, recording enabled, against the mock provider:

| Metric | 500 @ 50 | 2000 @ 100 |
|--------|---------:|-----------:|
| Throughput | 1,538 req/s | 1,639 req/s |
| Latency p50 / p99 | 17.6 / 54.6 ms | 36.7 / 142.5 ms |
| Records persisted | 500 / 500 | 2000 / 2000 |
| Chain | INTACT, 500 verified | INTACT, 2000 verified |
| `chain_seq` gaps / dupes | 0 / 0 | 0 / 0 |
| Full-chain verify time | 0.02 s | 0.07 s |

The gaps/dupes=0 line is the important one: records are written
asynchronously off the request path, yet under 100-way concurrency the
chain sequence is complete and every link verifies. **Tamper detection at
scale:** altering the record at `chain_seq=1000` in the 2000-record chain is
caught precisely — 999 verified, break at index 999.

Reproduce: `python bench/chainstress/stress.py <runs_dir> <N> <concurrency>`.

---

## 6. Production checklist

- Set `TRUST_SIGNING_KEY` from a secret store; back up the keyfile if you let
  the gateway generate one. Whoever holds the key can produce valid chains —
  treat it like a signing secret.
- Records contain prompt/PII context: keep the runs dir, lake, and bundles
  in-region and encrypted at rest; archive evidence bundles to WORM storage
  (S3 Object Lock) for retention.
- One chain per gateway replica. For HA, keep per-replica runs dirs separate
  and verify each independently (see `deploy/HA.md`).
- Enable OAuth on the MCP server before exposing it (`deploy/mcp/README.md`).
