# TASK: Wire up the self-verifying evidence bundle (Path A)

Status: NOT STARTED. Queued from the May 30 2026 session. Do this fresh, not at
the end of a long session. This is the trust anchor of the whole product.

## Goal
Make `air-blackbox export --format evidence` produce a real `.air-evidence.zip`
containing a `verify.py` that an auditor runs offline to get PASS/FAIL, matching
what the README describes. Today `export` only writes flat JSON or a PDF.

## The core problem (why this is NOT a simple wire-up)
Two audit-chain formats currently disagree, and the verifier must match the real
one. If you skip this, the bundle will report FAIL on genuine evidence.

- CANONICAL / PRODUCTION format (DO NOT CHANGE): defined in
  sdk/air_blackbox/trust/chain.py. Each record's chain_hash =
  HMAC-SHA256(key, prev_hash || JSON(record)). prev_hash starts at the GENESIS
  value and advances to the raw digest h.digest() of each record. This is what
  the trust layers and gateway actually write. It is correct. Leave it alone.

- SPECULATIVE format (currently WRONG): the embedded _VERIFY_SCRIPT in
  sdk/air_blackbox/export/evidence_bundle.py checks a different scheme:
  signature = HMAC(key, "sequence|run_id|record_hash|prev_hash"), prev_hash
  starts at "". This does NOT match production records, so as-is it reports FAIL
  on genuine untampered evidence. This is the file to rewrite.

## The three things that must agree, byte for byte
1. trust/chain.py        the writer. SOURCE OF TRUTH. Read it, do not change it.
2. the new verify.py     must recompute exactly what trust/chain.py computes:
                         identical JSON serialization (separators, sort_keys,
                         encoding), the same GENESIS value, the same prev_hash
                         advancement (digest vs hexdigest).
3. the export wiring     must emit the real records (via ReplayEngine reading
                         .air.json) into the ZIP unchanged, in the exact form
                         the new verify.py reads back.

## Files involved
- sdk/air_blackbox/trust/chain.py             READ ONLY, source of truth
- sdk/air_blackbox/replay/engine.py           source of raw records: load()/filter()
- sdk/air_blackbox/export/evidence_bundle.py  rewrite _VERIFY_SCRIPT + generator
- sdk/air_blackbox/cli.py  (export command)   add --format evidence that calls it

## Acceptance test (this GATES completion, feature is not done until it passes)
1. Generate real .air.json records (run a trust-layer example or the demo).
2. air-blackbox export --format evidence  -> produces air-evidence-*.zip
3. Unzip to a clean temp dir. Run: python verify.py
   MUST print RESULT: PASS and exit 0.
4. Flip one byte in audit_chain.json inside the extracted dir. Run verify.py.
   MUST print RESULT: FAIL and exit 1.
5. Run verify.py on a machine with NO air-blackbox installed (stdlib only).
   MUST still work; verify.py is self-contained by design.

If step 4 ever says PASS, the verifier is broken and worthless. Stop and fix.

## Open decision before shipping
verify.py defaults to signing key "air-blackbox-default". Decide whether the
bundle embeds nothing (auditor supplies the key) or whether chain verification
is key-independent via the hash linkage. Resolve this before publishing.

## Only AFTER the tamper test passes
Update the README to promise the verify.py PASS/FAIL flow. Not before.
