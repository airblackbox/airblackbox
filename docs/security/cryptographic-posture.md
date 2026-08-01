# AIR Blackbox: Cryptographic Agility and Post-Quantum Posture

Status: living document. Last updated 2026-08-01.

AIR Blackbox is a trust product: its guarantees rest entirely on cryptography.
This document states, honestly, which primitives we use, what each one is
exposed to (including AI-assisted cryptanalysis and quantum computers), how the
system is designed to replace a primitive without a rewrite, and what is not yet
production-ready. It is both engineering reference and the answer we give a
buyer who forwards us a scary crypto headline.

The short version: no primitive is assumed unbreakable. The design assumption is
that any one of them may need to be replaced, so the architecture is
crypto-agile (the algorithm is data, not a hard-coded assumption) and relies on
more than one independent root of trust.

## Primitives in use

| Primitive | Where | Purpose |
|---|---|---|
| HMAC-SHA256 | audit chain (`trust/chain.py`) | Tamper-evident links between records. Symmetric; key from `TRUST_SIGNING_KEY` or a per-tenant key file. |
| SHA-256 | chain head (`anchor/head.py`), payload hashes, manifest digest | Key-free commitments over ordered records and over bundle contents. |
| Ed25519 | Gate receipts (classical default), evidence-bundle manifest signature | Non-repudiable signatures verifiable with the public key alone. |
| ML-DSA-65 (Dilithium3, FIPS 204) | Gate receipts + manifest signature — **the default when the `pqc` extra is installed** | Post-quantum signature via `pqcrypto` (PQClean; prebuilt wheels), with liboqs honored as a fallback provider. Keypairs persist per tenant, so identities survive restarts. CI runs the full suite under this path. |
| HMAC-SHA256 (fallback) | receipts, when no asymmetric library is present | Last-resort signing. Requires a shared secret; not third-party verifiable. |
| RFC 3161 timestamp (external) | anchor (`anchor/tsa.py`) | A timestamp authority countersigns the chain head with the authority's own key. Key we do not hold. |

## Threat exposure

### AI-assisted cryptanalysis
The recent "AI broke AES" style results target **reduced-round variants** of
ciphers, an established academic activity that does not threaten the full-round
primitives in production. Full AES-256, SHA-256, and HMAC-SHA256 are not
affected by that class of result. We track the field, but it does not change our
current posture.

### Quantum computers
This is the real long-horizon exposure, and it is uneven across our primitives:

| Primitive | Quantum exposure | Consequence |
|---|---|---|
| HMAC-SHA256 / SHA-256 | Grover gives only a quadratic speedup | 256-bit width leaves ~128-bit effective security. Robust; no action needed. |
| Ed25519 | Shor's algorithm breaks elliptic-curve signatures on a large quantum computer | **This is the primitive to migrate.** Mitigation: the ML-DSA-65 path. |
| RFC 3161 TSA signature | Depends on the authority's key (often RSA/ECDSA) | Quantum-exposed, but it is the authority's key to migrate, and the anchor is a secondary time-binding root, not the sole guarantee. |

## Why a single break is not a collapse

AIR does not rest on one primitive or one key. It has independent roots of trust:

1. **Chain integrity** is symmetric (HMAC-SHA256), quantum-robust.
2. **Receipts** are asymmetric (Ed25519, migrating to ML-DSA-65).
3. **The external anchor** is a timestamp authority's signature over the head, a
   key the operator does not hold.
4. **A public transparency log** (roadmap M2) will add a fourth root that no
   single party controls.

If Ed25519 fell tomorrow, the HMAC chain and the external anchor would still
detect tampering. That layering is the actual defense.

## Crypto-agility: the algorithm is data

- Every receipt carries a `signing_method` field (`ed25519`, `ML-DSA-65`, or
  `hmac-sha256`) and its public key, so a verifier adapts to whatever signed it.
- The chain's construction is recorded in each evidence bundle
  (`verification/chain.json`), so the hashing scheme is documented, not implied.
- Because the method travels with the data, migrating a signature algorithm does
  not require rewriting historical records or the verifier.

## Not yet production-ready (stated plainly)

- **ML-DSA-65 is production-ready and the default when installed** (issue #63,
  resolved): keypairs persist per tenant and survive restarts; a provided key is
  always honored, never silently replaced; and CI runs the entire suite under
  the post-quantum path (`python-test-pqc`), made cheap by switching the
  provider to `pqcrypto` (PQClean, prebuilt wheels — no native build).
  Existing Ed25519 tenants keep their Ed25519 identity forever; rotating them
  to ML-DSA would change their published public key, so migration is a
  deliberate operator action, not an upgrade side effect. Installations
  without the `pqc` extra still default to Ed25519.
- **The HMAC fallback uses a well-known default key** (`air-blackbox-default`)
  when no signing key is configured. Any real deployment must set
  `TRUST_SIGNING_KEY`. This fallback is not third-party verifiable and should be
  treated as development-only.
- **Public transparency-log anchoring (M2) is roadmap, not shipped.** External
  RFC 3161 anchoring (M1) is shipped and is now enforced by the evidence verifier
  (`air-evidence verify`), which fails on a rewritten history whose anchor does
  not match. Its documented limitation: an attacker who rewrites history *and*
  obtains a fresh timestamp for the new head produces a self-consistent bundle.
  Closing that gap is exactly what the public append-only log (M2) is for.

## Migration plan

1. ~~Fix ML-DSA-65 key persistence (#63) and put the path under CI, then make
   ML-DSA-65 the default signature for hosted and high-assurance deployments.~~
   **Done.** ML-DSA-65 is the default wherever the `pqc` extra is installed.
2. Ship M2 public transparency-log anchoring, removing sole dependence on
   operator-held keys.
3. Keep this document current as the cryptographic bill of materials for AIR
   itself. If a primitive's exposure changes, it is recorded here first.

## What we do not claim

We do not claim any primitive is unbreakable, that AIR is quantum-proof today,
or that using it makes an organization compliant. We claim that AIR is built to
replace its cryptography, that it does not depend on any single algorithm or key,
and that its current gaps are written down rather than hidden.
