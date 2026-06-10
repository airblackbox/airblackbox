#!/usr/bin/env bash
# Runs the full AIR Blackbox Gateway benchmark suite.
# Usage (from repo root):  bash bench/run-bench.sh
#
# Outputs:
#   - terminal table with direct vs gateway latency and added-latency deltas
#   - bench/results/results.json
#
# Tunables (env vars):
#   REQUESTS=2000  CONCURRENCY=1,8,32  WARMUP=200  MOCK_LATENCY_MS=0

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results

COMPOSE="docker compose -f docker-compose.bench.yaml"

echo "==> Building and starting benchmark stack (gateway, mock provider, vault, collector)..."
$COMPOSE up -d --build gateway mockllm minio collector jaeger

echo "==> Waiting for gateway health..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T gateway wget -q -O- http://localhost:8080/health > /dev/null 2>&1; then
    echo "    gateway healthy."
    break
  fi
  if [ "$i" = "30" ]; then
    echo "ERROR: gateway did not become healthy in 60s. Check: $COMPOSE logs gateway"
    exit 1
  fi
  sleep 2
done

echo "==> Running load test (this takes a few minutes)..."
$COMPOSE run --rm --build loadgen

echo ""
echo "==> Done. Results saved to bench/results/results.json"
echo "    Paste the markdown table above into BENCHMARKS.md."
echo ""
read -p "Tear down the benchmark stack? [y/N] " yn
if [ "${yn:-n}" = "y" ]; then
  $COMPOSE down -v
fi
