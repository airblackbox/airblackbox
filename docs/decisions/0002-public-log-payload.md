# ADR 0002: M2 public-log entry format - rekord with full payload, not hashedrekord

Date: 2026-08-01
Status: Accepted (supersedes the M2 line of ADR 0001)
Context: Roadmap M2 "public transparency-log anchoring", implemented in
`sdk/air_blackbox/anchor/rekor.py`.

## Question

ADR 0001 planned M2 as "Rekor with a dedicated ECDSA P-256 anchor key, entry
type `hashedrekord`". Implementing M2 surfaced a property that decision did
not weigh. Which entry type actually delivers the M2 guarantee?

## Finding

The M2 guarantee is: *a rewritten history - even one freshly re-anchored -
is detected, because old anchors cannot be removed from an append-only log.*
The detection sweep (`audit_runs_against_log`) fetches every entry under the
tenant's anchoring key and recomputes the bounded chain head for each.

- With **`hashedrekord`**, the log stores only `sha256(payload)`. An auditor
  enumerating the key's entries sees opaque digests; interpreting them
  requires the payloads, which only the operator retains. An operator hiding
  a rewrite simply withholds the old payloads - the sweep degrades from
  "detects the lie" to "counts entries it cannot read". The append-only
  property survives, but its *auditability* does not.
- With **`rekord`**, the full canonical payload (`air-chain-anchor-v1`:
  chain head + sequence bound + time) travels inline, ~200 bytes. Every
  anchor ever published is independently interpretable from the public log
  alone, forever, by anyone holding just the anchoring public key. This is
  the property the M2 sweep is built on.

`rekord` verifies the signature against the full payload, which is also what
makes **pure Ed25519** acceptable to Rekor for this type (the ADR 0001
blocker applied to `hashedrekord` only). The merged Go client
(`pkg/trust/anchor.go`) had already reached the same conclusion for the same
reason. No content ever leaves the machine either way: the payload is a hash
commitment plus a sequence number.

## Decision

- **M2 uses `rekord` entries carrying the full `air-chain-anchor-v1` payload,
  signed with a dedicated per-tenant Ed25519 anchor key** (`.air-anchor-key`),
  matching the Go client. No ECDSA key type is introduced.
- The anchor key remains an index handle, not a root of trust: the security
  property comes from the log's append-onlyness. An attacker holding the key
  can only publish permanent, timestamped evidence of their own conflict.
- Anchoring is opt-in (`AIR_REKOR=1` or `AIR_REKOR_SERVER`), because
  publishing to a public log - even hash-only - is a deliberate choice.

## Consequences

- `audit_runs_against_log` needs only the runs directory and the anchoring
  public key; every logged anchor is checkable with no operator cooperation.
- Python and Go publish the same entry type; a future shared verifier reads
  both.
- Rekor retention/policy changes remain a risk for the public instance (as in
  ADR 0001); `AIR_REKOR_SERVER` points at any Rekor-compatible log, and the
  rail abstraction (TSA + log) means neither rail's outage strands exports.
- Full Merkle inclusion-proof verification against the log's signed tree head
  is future work; v1 verifies entry presence, payload commitment, and the
  cross-anchor consistency sweep - which is the check that actually closes
  the re-anchored-rewrite gap.
