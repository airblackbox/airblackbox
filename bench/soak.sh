#!/usr/bin/env bash
# Soak test for the AIR Blackbox Gateway.
#
# Runs sustained load for SOAK_MINUTES, sampling gateway memory between rounds
# to catch leaks, and verifies at the end that:
#   1. the error rate stayed below ERR_THRESHOLD_PCT
#   2. resident memory did not grow beyond MEM_GROWTH_LIMIT x the first sample
#   3. the HMAC audit chain is still intact after the full run
#
# Usage (from repo root):
#   bash bench/soak.sh                      # default 5-minute proof run
#   SOAK_MINUTES=1440 bash bench/soak.sh    # full 24-hour soak
#
# Tunables:
#   SOAK_MINUTES=5  CONCURRENCY=16  ROUND_REQUESTS=2000
#   ERR_THRESHOLD_PCT=1  MEM_GROWTH_LIMIT=2.0

set -euo pipefail
cd "$(dirname "$0")"

SOAK_MINUTES="${SOAK_MINUTES:-5}"
CONCURRENCY="${CONCURRENCY:-16}"
ROUND_REQUESTS="${ROUND_REQUESTS:-2000}"
ERR_THRESHOLD_PCT="${ERR_THRESHOLD_PCT:-1}"
MEM_GROWTH_LIMIT="${MEM_GROWTH_LIMIT:-2.0}"

COMPOSE="docker compose -f docker-compose.bench.yaml -f docker-compose.soak.yaml"
mkdir -p results
SAMPLES="results/soak-samples.csv"
echo "round,elapsed_s,rss_bytes,round_requests,round_errors" > "$SAMPLES"

echo "==> Starting soak stack (gateway+trust, mock provider, vault, collector)..."
$COMPOSE up -d --build gateway mockllm minio collector jaeger

echo "==> Waiting for gateway health and trust layer..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T gateway wget -q -O- http://localhost:8080/health >/dev/null 2>&1; then
    break
  fi
  [ "$i" = "30" ] && { echo "ERROR: gateway not healthy in 60s"; $COMPOSE logs gateway; exit 1; }
  sleep 2
done
# Confirm the trust layer is actually on, otherwise the chain check is meaningless.
if ! $COMPOSE exec -T gateway wget -q -O- http://localhost:8080/v1/audit >/dev/null 2>&1; then
  echo "ERROR: /v1/audit not available - trust layer did not enable. Check guardrails mount."
  exit 1
fi
echo "    gateway healthy, trust layer enabled."

START_EPOCH=$(date +%s)
DEADLINE=$(( START_EPOCH + SOAK_MINUTES * 60 ))

total_requests=0; total_errors=0; first_rss=0; last_rss=0; round=0

rss_bytes() {
  # Read the gateway process RSS straight from /proc inside the container.
  # VmRSS is reported in kB; convert to bytes. This avoids any reliance on a
  # container ID that can change when compose recreates the service.
  local kb
  kb="$($COMPOSE exec -T gateway sh -c 'cat /proc/1/status' 2>/dev/null | awk '/VmRSS/{print $2}')"
  if [ -z "$kb" ]; then echo 0; else echo $(( kb * 1024 )); fi
}

sum_field() { # $1=json file, $2=field
  python3 -c "import json;d=json.load(open('$1'));print(sum(r.get('$2',0) for r in (d if isinstance(d,list) else [d])))" 2>/dev/null || echo 0
}

echo "==> Soaking ${SOAK_MINUTES} min at concurrency ${CONCURRENCY} (${ROUND_REQUESTS} reqs/round)..."
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  round=$((round + 1))
  $COMPOSE run --rm --build \
    -e REQUESTS="$ROUND_REQUESTS" -e CONCURRENCY="$CONCURRENCY" -e WARMUP=0 \
    loadgen >/dev/null 2>&1 || true

  # loadgen's entrypoint writes results/results.json; copy it aside immediately
  # so a soak run never clobbers the committed benchmark file.
  cp -f results/results.json results/soak-round.json 2>/dev/null || true
  rerr=$(sum_field results/soak-round.json errors)
  rreq=$(sum_field results/soak-round.json requests)
  rss=$(rss_bytes)
  [ "$first_rss" = "0" ] && first_rss="$rss"
  last_rss="$rss"
  elapsed=$(( $(date +%s) - START_EPOCH ))
  total_requests=$(( total_requests + rreq ))
  total_errors=$(( total_errors + rerr ))
  echo "$round,$elapsed,$rss,$rreq,$rerr" >> "$SAMPLES"
  printf "    round %2d | %4ds | rss %6.1f MiB | reqs %d | errs %d\n" \
    "$round" "$elapsed" "$(python3 -c "print($rss/1048576)")" "$rreq" "$rerr"
done

echo ""
echo "==> Verifying audit chain integrity after soak..."
chain_json="$($COMPOSE exec -T gateway wget -q -O- http://localhost:8080/v1/audit 2>/dev/null || echo '{}')"
chain_valid="$(printf '%s' "$chain_json" | python3 -c "import json,sys;print(json.load(sys.stdin).get('chain_valid'))" 2>/dev/null || echo unknown)"
chain_len="$(printf '%s' "$chain_json" | python3 -c "import json,sys;print(json.load(sys.stdin).get('chain_length'))" 2>/dev/null || echo '?')"

err_pct=$(python3 -c "print(round(100*$total_errors/max($total_requests,1),3))")
mem_ratio=$(python3 -c "print(round($last_rss/max($first_rss,1),3))")

echo ""
echo "================ SOAK SUMMARY ================"
echo "  duration:        ${SOAK_MINUTES} min, ${round} rounds"
echo "  total requests:  ${total_requests}"
echo "  total errors:    ${total_errors} (${err_pct}%)"
echo "  rss first/last:  $(python3 -c "print(round($first_rss/1048576,1))") / $(python3 -c "print(round($last_rss/1048576,1))") MiB (x${mem_ratio})"
echo "  chain valid:     ${chain_valid} (length ${chain_len})"
echo "============================================="

fail=0
python3 -c "import sys;sys.exit(0 if $err_pct <= $ERR_THRESHOLD_PCT else 1)" || { echo "FAIL: error rate ${err_pct}% > ${ERR_THRESHOLD_PCT}%"; fail=1; }
python3 -c "import sys;sys.exit(0 if $mem_ratio <= $MEM_GROWTH_LIMIT else 1)" || { echo "FAIL: memory grew x${mem_ratio} > ${MEM_GROWTH_LIMIT}x"; fail=1; }
[ "$chain_valid" = "True" ] || { echo "FAIL: audit chain not valid after soak"; fail=1; }

[ "$fail" = "0" ] && echo "RESULT: PASS" || { echo "RESULT: FAIL"; exit 1; }
