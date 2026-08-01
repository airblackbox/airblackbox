"""Binding history - anchor the chain head to an external, operator-independent
authority so a rewritten-and-re-signed history is detectable.

AIR's chain + receipts prove nothing was ALTERED. But the operator holds the
keys and could rewrite the whole chain and re-sign it. Anchoring the chain
head to an RFC 3161 timestamp authority closes that: the TSA countersigns
"this exact head existed at time T" with a key the operator does not control,
so a rewritten head cannot inherit the old anchor.

The claim this enables: "you can still lie, but not invisibly."

Two rails:
  - M1 (tsa.py): RFC 3161 timestamp. Proves the head existed at time T. Limit:
    an attacker who rewrites AND re-timestamps produces a self-consistent
    bundle.
  - M2 (rekor.py): public append-only transparency log. Closes the M1 limit -
    old anchors can never be removed, so a re-anchored rewrite still fails
    against them.

See docs/decisions/0001-anchor-rail.md (rail choice) and
docs/decisions/0002-public-log-payload.md (M2 entry format).
"""

from air_blackbox.anchor.head import compute_head
from air_blackbox.anchor.rekor import (
    RekorAnchor,
    RekorClient,
    anchor_head_to_rekor,
    audit_runs_against_log,
    verify_bundle_anchor,
)
from air_blackbox.anchor.tsa import (
    AnchorResult,
    timestamp_head,
    verify_anchor_bytes,
)

__all__ = [
    "compute_head", "timestamp_head", "verify_anchor_bytes", "AnchorResult",
    "RekorAnchor", "RekorClient", "anchor_head_to_rekor",
    "audit_runs_against_log", "verify_bundle_anchor",
]
