#!/usr/bin/env bash
# M0 spike, public-rail half: anchor a 32-byte chain head to a real RFC 3161
# TSA and verify. Run from any machine with unrestricted egress + openssl.
#   bash spike/anchor_spike.sh [hex-of-32-byte-head]
set -euo pipefail
HEAD="${1:-$(printf 'air-blackbox chain head %s' "$(date -u +%s)" | openssl dgst -sha256 | awk '{print $2}')}"
WORK=$(mktemp -d); cd "$WORK"
echo "chain head: $HEAD"

openssl ts -query -digest "$HEAD" -sha256 -cert -out req.tsq

try_tsa() { # url name
  echo "--- trying $2 ($1)"
  if curl -sS -m 20 -H 'Content-Type: application/timestamp-query' \
       --data-binary @req.tsq "$1" -o resp.tsr && [ -s resp.tsr ]; then
    openssl ts -reply -in resp.tsr -text 2>/dev/null | grep -E "Status:|Time stamp:" && return 0
  fi
  return 1
}

try_tsa "https://timestamp.sigstore.dev/api/v1/timestamp" "sigstore TSA" \
  || try_tsa "https://freetsa.org/tsr" "FreeTSA" \
  || try_tsa "http://timestamp.digicert.com" "DigiCert" \
  || { echo "no TSA reachable"; exit 1; }

echo "--- verify: TSR commits to the head"
# FreeTSA chain (works for freetsa responses); sigstore chain via its certchain
# endpoint. For the spike we verify token structure + imprint match:
openssl ts -verify -digest "$HEAD" -in resp.tsr -no_check_time \
  -CAfile <(curl -sS -m 20 https://freetsa.org/files/cacert.pem 2>/dev/null; \
            curl -sS -m 20 https://timestamp.sigstore.dev/api/v1/timestamp/certchain 2>/dev/null) \
  2>&1 | tail -1 || true

echo "--- THE REWRITE TEST: rewritten head must FAIL against the same TSR"
NEWHEAD=$(printf 'rewritten history' | openssl dgst -sha256 | awk '{print $2}')
openssl ts -verify -digest "$NEWHEAD" -in resp.tsr -no_check_time \
  -CAfile <(curl -sS -m 20 https://freetsa.org/files/cacert.pem 2>/dev/null) \
  2>&1 | grep -E "Verification|imprint" | head -2
echo "artifacts in $WORK (req.tsq, resp.tsr)"
