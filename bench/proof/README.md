# AIR Blackbox proof harness

Don't trust the claims. Run the attacks.

```bash
python bench/proof/prove.py
```

This runs real attacks against three systems and prints a scorecard. Every
"AIR Blackbox" cell executes the actual product code (the HMAC-SHA256 audit
chain, `verify_chain`, the key-free chain head plus RFC 3161 anchor
verification, and the Gate covenant). Nothing is mocked.

## What it compares

| system | what it is |
|---|---|
| **plain log** | an append-only list. No integrity, no policy. What most teams have today. |
| **hash chain** | a genuine HMAC-SHA256 tamper-evident chain with no external anchor. A fair stand-in for a well-built audit-log product (including the Rust HMAC-hash-chain tools now on the market). |
| **AIR Blackbox** | the hash chain **plus** the external timestamp anchor, the covenant, and public-key-verifiable evidence. |

## The scorecard

```
attack                            plain log      hash chain     AIR Blackbox
edit a past record                MISSED         DETECTED       DETECTED
delete a record from history      MISSED         DETECTED       DETECTED
rewrite + re-sign entire history  MISSED         MISSED         DETECTED
forbidden action attempted        RECORDED       RECORDED       BLOCKED
verify with no secret             n/a            NO             YES
```

The row that matters is **rewrite + re-sign entire history**. A plain hash
chain cannot catch it: the operator holds the signing key, so they can rewrite
the whole history and re-sign it, and the chain still verifies. AIR catches it
because the chain head was countersigned by an external timestamp authority, a
key the operator does not hold. This is the "you can still lie, but not
invisibly" guarantee, made runnable.

## Honest limits

- The harness stands up a throwaway local `openssl` timestamp authority so it
  runs offline. If `openssl` is absent, the anchor-dependent rows report `SKIP`
  rather than fake a pass.
- The `rewrite` detection shown here is for a rewrite that was not
  re-anchored. An attacker who rewrites **and** obtains a fresh timestamp for
  the new head produces a self-consistent bundle; defeating that requires the
  public append-only log (roadmap M2). See
  [docs/security/cryptographic-posture.md](../../docs/security/cryptographic-posture.md).

## Exit code

`0` iff AIR delivered every guarantee. CI runs it (`sdk/tests/test_proof_harness.py`)
and also asserts the comparison stays real, i.e. the bare hash chain still
misses the rewrite, so the harness can never quietly become a rigged demo.
