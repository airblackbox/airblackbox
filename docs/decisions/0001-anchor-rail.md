# ADR 0001: Anchor rail for binding history

Date: 2026-07-17
Status: Accepted
Context: Roadmap "Binding History (external anchoring + detectable omission)", M0 spike.

## Question

AIR's chain + receipts prove nothing was *altered*, but the operator holds the
keys and could rewrite the whole chain and re-sign it. External anchoring
closes that. Which rail, and does it accept our Ed25519 signing key?

## Findings (M0 spike, 2026-07-17)

**1. Rekor `hashedrekord` does NOT accept pure Ed25519 — by design, not by bug.**
Pure Ed25519 must see the full message to verify; `hashedrekord` carries only
the artifact hash, so verification is structurally impossible
([sigstore/rekor#851](https://github.com/sigstore/rekor/issues/851)).
`ed25519ph` (SHA-512-prehashed) support was merged March 2024
([sigstore/rekor#1945](https://github.com/sigstore/rekor/pull/1945), depends on
[sigstore/sigstore#1595](https://github.com/sigstore/sigstore/pull/1595)), so
`hashedrekord` accepts: ECDSA (SHA256/384/512) and Ed25519ph.

**2. Our stack cannot produce ed25519ph today.** Receipts are signed with
Python `cryptography`'s `Ed25519PrivateKey`, which exposes only pure Ed25519
(no prehashed variant). Switching receipt signing to ed25519ph would change the
receipt format and its verification story for zero user-visible benefit.

**3. RFC 3161 TSA is key-agnostic and the full flow is proven.** The spike ran
the complete cycle with openssl only — no new dependencies:
a 32-byte chain head → timestamp query (`openssl ts -query -digest ...`) →
TSA response (`Status: Granted`) → `Verification: OK` against the head →
and the decisive rewrite test: verifying the same TSR against a
rewritten-and-re-signed head fails with `message imprint mismatch`,
`Verification: FAILED`. Transcript: `spike/anchor-spike-transcript.txt`;
reproduce against public rails with `spike/anchor_spike.sh` (the build sandbox's
egress proxy blocks public TSA/Rekor endpoints, so the public-rail transcript
is produced by running the script from any unrestricted machine; DigiCert's
endpoint answered 403-at-proxy, confirming blocking is local policy, not rail
availability).

## Decision

- **M1 anchors to RFC 3161 TSA** via openssl subprocess (no new Python deps).
  Multiple TSA URLs configurable, tried in order, the responder recorded:
  default order `timestamp.sigstore.dev/api/v1/timestamp`, `freetsa.org/tsr`,
  `timestamp.digicert.com`.
- **M2 anchors to Rekor with a dedicated ECDSA P-256 anchor key**, entry type
  `hashedrekord`. The anchor key signs only chain heads; receipts remain pure
  Ed25519, unchanged. A separate anchor key is acceptable because the anchor's
  job is to bind head→public log, not to identify the operator — the receipt
  key does that.
- **Do not adopt ed25519ph** unless/until the Python tooling exposes it and
  there is a concrete reason to unify keys.

## Consequences

- No changes to receipt signing or verification (backward compatible).
- The evidence bundle gains `anchors/` (M1: TSR + TSA cert chain; M2: Rekor
  entry UUID + inclusion proof).
- Anchor-rail abstraction: one interface, two implementations (TSA, Rekor),
  so a policy shift on the public Rekor instance cannot strand the feature.
