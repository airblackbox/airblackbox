#!/usr/bin/env bash
# Failure injection suite for AIR Blackbox Gateway.
#
# Proves the witness contract under real failure conditions:
#   "AIR is a witness, not a gatekeeper. It cannot cause your AI system to fail."
#
# Scenarios:
#   1. Vault (MinIO) down       -> proxying must continue, zero request failures
#   2. OTel collector down       -> proxying must continue, zero request failures
#   3. Vault AND collector down  -> proxying must continue, zero request failures
#   4. Recovery                  -> services restored, proxying still healthy
#
# Usage (from repo root):  bash bench/failure-injection.sh
# Requires the benchmark stack: bash bench/run-bench.sh first, or it starts one.

set -uo pipefail
cd "$(dirname "$0")"
mkdir -p results

COMPOSE="docker compose -f docker-compose.bench.yaml"
PASS=0
FAIL=0

probe() {
  # Sends N requests through the gateway from inside the network.
  # Prints "<ok_count> <total>".
  local n="$1"
  $COMPOSE exec -T gateway sh -c '
    ok=0
    for i in $(seq 1 '"$n"'); do
      code=$(wget -q -O /dev/null -S --header="Content-Type: application/json" \
        --post-data="{\"model\":\"bench\",\"messages\":[{\"role\":\"user\",\"content\":\"failure injection probe\"}]}" \
        http://localhost:8080/v1/chat/completions 2>&1 | awk "/HTTP\//{print \$2}" | tail -1)
      [ "$code" = "200" ] && ok=$((ok+1))
    done
    echo "$ok '"$n"'"
  '
}

scenario() {
  local name="$1" n="$2"
  echo ""
  echo "== SCENARIO: $name =="
  result=$(probe "$n")
  ok=$(echo "$result" | awk '{print $1}')
  total=$(echo "$result" | awk '{print $2}')
  if [ "$ok" = "$total" ]; then
    echo "   PASS: $ok/$total requests succeeded."
    PASS=$((PASS+1))
  else
    echo "   FAIL: only $ok/$total requests succeeded. The witness contract is broken."
    FAIL=$((FAIL+1))
  fi
}

echo "==> Ensuring benchmark stack is up..."
$COMPOSE up -d --build gateway mockllm minio collector jaeger
sleep 5

scenario "baseline (all services healthy)" 20

echo ""
echo "==> Stopping vault (MinIO)..."
$COMPOSE stop minio
sleep 2
scenario "vault unreachable" 20

echo ""
echo "==> Restarting vault, stopping OTel collector..."
$COMPOSE start minio
$COMPOSE stop collector
sleep 2
scenario "collector unreachable" 20

echo ""
echo "==> Stopping vault AND collector..."
$COMPOSE stop minio
sleep 2
scenario "vault and collector both unreachable" 20

echo ""
echo "==> Restoring all services..."
$COMPOSE start minio collector
sleep 5
scenario "recovery (all services restored)" 20

echo ""
echo "=============================================="
echo " FAILURE INJECTION RESULTS: $PASS passed, $FAIL failed"
echo "=============================================="
if [ "$FAIL" = "0" ]; then
  echo " The witness contract held under every failure scenario."
  echo " Record these results in BENCHMARKS.md."
else
  echo " One or more scenarios broke the witness contract. Fix before publishing."
  exit 1
fi
