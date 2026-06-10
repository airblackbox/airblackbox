# Benchmarks

AIR Blackbox Gateway sits in the request path between your AI agents and your
LLM provider. This document publishes what that costs, measured, reproducible,
and updated with every release that touches the hot path.

**TL;DR: Full recording (content vault, HMAC-SHA256 audit chain, OTel spans)
adds ~0.3 ms median per LLM call at low concurrency and ~3 ms under heavy
load, with a single-node ceiling of ~7,200 requests/sec. In a realistic LLM
call (~800 ms), recording overhead is under 0.4% of request time at the median
and under 1% at p99, with identical throughput to running unproxied. Zero
dropped requests across 15,000+ benchmark requests, including with the vault
and collector down.**

## Methodology

The benchmark stack runs the gateway in its full production configuration
(content vault, OTel collector, audit chain, AIR records) pointed at a mock
OpenAI-compatible provider with configurable latency. This isolates gateway
overhead from provider latency.

- Load generator and gateway run inside the same Docker network, removing
  host-networking variance.
- Each concurrency level runs a warmup phase before measurement.
- Added latency is (through-gateway percentile) minus (direct-to-provider
  percentile) for the same run profile.

Reproduce everything with two commands from the repo root:
bash bench/run-bench.sh            # latency + throughput
bash bench/failure-injection.sh    # witness contract under failure

## Results

Hardware: Apple Silicon Mac, Docker Desktop
Gateway version: e016c49
Date: 2026-06-10

### Pure overhead (mock provider latency = 0 ms)

| Path | Concurrency | RPS | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-------------|-----|----------|----------|----------|--------|
| direct | 1 | 13948 | 0.07 | 0.09 | 0.14 | 0 |
| gateway | 1 | 2231 | 0.35 | 0.78 | 2.05 | 0 |
| direct | 8 | 27486 | 0.18 | 0.50 | 2.73 | 0 |
| gateway | 8 | 6050 | 0.91 | 2.55 | 8.09 | 0 |
| direct | 32 | 35456 | 0.33 | 1.97 | 14.49 | 0 |
| gateway | 32 | 7272 | 3.56 | 8.44 | 16.71 | 0 |

Added latency at concurrency 32: p50 +3.23 ms, p90 +6.48 ms, p99 +2.22 ms.
Note the p99 convergence between direct and gateway (16.71 vs 14.49 ms): tail
latency at high concurrency is dominated by scheduling, not gateway code.

### Realistic profile (mock provider latency = 800 ms)

| Path | Concurrency | RPS | p50 (ms) | p90 (ms) | p99 (ms) | Errors |
|------|-------------|-----|----------|----------|----------|--------|
| direct | 32 | 39 | 804.60 | 807.16 | 812.68 | 0 |
| gateway | 32 | 39 | 807.40 | 814.93 | 818.76 | 0 |

Added latency: p50 +2.80 ms (0.35% of request time), p90 +7.77 ms (0.96%),
p99 +6.08 ms (0.75%). Throughput is identical with and without the gateway.

## Failure injection

The gateway's design contract: recording is best-effort, proxying is
guaranteed. A dropped record is acceptable. A dropped request is not.

| Scenario | Requests | Succeeded | Verdict |
|----------|----------|-----------|---------|
| Baseline, all services healthy | 20 | 20 | PASS |
| Vault (MinIO) unreachable | 20 | 20 | PASS |
| OTel collector unreachable | 20 | 20 | PASS |
| Vault and collector both unreachable | 20 | 20 | PASS |
| Recovery, services restored | 20 | 20 | PASS |

The witness contract held under every failure scenario: 100/100 requests
succeeded while recording infrastructure was degraded or down.

## Soak / stability

Sustained load with the trust layer enabled, sampling gateway resident
memory between rounds to catch leaks, and verifying the HMAC audit chain
is still intact at the end.

```bash
bash bench/soak.sh                    # 5-minute proof run
SOAK_MINUTES=1440 bash bench/soak.sh  # full 24-hour soak
```

A passing run requires the error rate to stay under 1%, resident memory to
stay under 2x its first sample, and the audit chain to verify after the run.
On a representative short run, memory stayed flat (it drifted slightly down
as the garbage collector reclaimed per-request allocations), the error rate
was 0%, and the chain verified across roughly a thousand appended records.

## What is and is not measured

Measured: proxy handling, request/response hashing, vault writes, AIR record
writes, audit chain append, OTel span emission, guardrails evaluation as
configured in the default stack.

Not measured: streaming responses (planned), ML-DSA-65 signing on the
evidence export path (off the hot path by design), dashboard rendering.

## Honest limitations

- Single-node numbers on developer hardware. Your ceiling depends on your
  hardware and provider rate limits.
- Docker Desktop on macOS adds virtualization overhead. Linux bare-metal
  numbers will be better, not worse.
- The mock provider does not stream. Streaming overhead will be benchmarked
  separately when streaming passthrough is covered by this suite.
