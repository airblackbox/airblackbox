"""Binding history - anchor the chain head to an external, operator-independent
authority so a rewritten-and-re-signed history is detectable.

AIR's chain + receipts prove nothing was ALTERED. But the operator holds the
keys and could rewrite the whole chain and re-sign it. Anchoring the chain
head to an RFC 3161 timestamp authority closes that: the TSA countersigns
"this exact head existed at time T" with a key the operator does not control,
so a rewritten head cannot inherit the old anchor.

The claim this enables: "you can still lie, but not invisibly."

See docs/decisions/0001-anchor-rail.md for why RFC 3161 (M1) over Rekor.
"""

from air_blackbox.anchor.head import compute_head
from air_blackbox.anchor.tsa import (
    AnchorResult,
    timestamp_head,
    verify_anchor_bytes,
)

__all__ = ["compute_head", "timestamp_head", "verify_anchor_bytes", "AnchorResult"]
