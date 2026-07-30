"""The chain head: a single 32-byte value that commits to the entire history.

Defined so it is computable by anyone with the records and NO secret key: it
is the SHA-256 over the ordered list of (chain_seq, chain_hash) pairs. Every
record's chain_hash already commits to that record's content and to the record
before it, so this head changes if any record is altered, added, or removed -
which is exactly what makes a rewritten history fail to match its old anchor.
"""

import glob
import hashlib
import json
import os


def head_over_entries(entries) -> str:
    """SHA-256 over the ordered (chain_seq, chain_hash) pairs - the key-free
    chain head.

    Shared by compute_head (which reads a runs directory) and the
    evidence-bundle verifier (which has an in-memory record list), so the two
    serializations can never drift apart. Returns "" for no entries.
    """
    if not entries:
        return ""
    ordered = sorted(entries, key=lambda e: (e[0], e[1]))
    payload = json.dumps(ordered, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_head(runs_dir: str, up_to_seq: int = None) -> str:
    """Return the hex SHA-256 chain head for a runs directory, or "" if there
    are no chained records.

    Only records carrying a chain_hash participate: unchained records are
    outside the chain (see the verifier), so they are outside the head too.

    up_to_seq bounds the head to records with chain_seq <= up_to_seq. An anchor
    is taken over the head at a sequence point; re-deriving the head over the
    same bounded set later detects any rewrite of that history, while records
    added afterwards legitimately advance the (unbounded) head.
    """
    entries = []
    for path in glob.glob(os.path.join(runs_dir, "*.air.json")):
        try:
            with open(path) as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        ch = rec.get("chain_hash")
        if not ch:
            continue
        seq = rec.get("chain_seq") or 0
        if up_to_seq is not None and seq > up_to_seq:
            continue
        entries.append((seq, ch))

    # Canonical, key-free commitment over the ordered chain.
    return head_over_entries(entries)
