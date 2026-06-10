# Signed Checkpoints and External Anchoring

The HMAC audit chain proves internal consistency: nobody can modify a record
without breaking the chain. But the operator holds the HMAC secret, so a
regulator still has to trust that the operator never rewrote the whole chain.
Signed checkpoints close that gap.

## How it works

1. **Checkpoint**: a snapshot of the chain head, its length, the hash of the
   latest entry, and a timestamp, signed with two algorithms:
   - **ML-DSA-65** (FIPS 204, post-quantum) for long-horizon local verification
   - **Ed25519** for compatibility with today's transparency logs
2. **Anchor**: the Ed25519 signature is published to
   [Rekor](https://docs.sigstore.dev/logging/overview/), Sigstore's public
   append-only transparency log. Once accepted, the entry cannot be removed.
3. **Verify**: anyone can confirm the chain head existed at the integrated
   time by fetching the public log entry, without trusting this machine.

## Usage

```bash
# Cut a dual-signed checkpoint from the running gateway
evidencectl checkpoint

# Publish it to the public transparency log
evidencectl anchor

# Verify signatures locally and confirm the anchor is in the public log
evidencectl verify-checkpoint --rekor
```

Keys are generated on first use in `~/.airblackbox/keys` and never leave the
machine. Anchor regularly (for example, daily via cron) so every day's chain
head has an independent, public existence proof.

## What this proves

| Layer | Proves | Trust required |
|-------|--------|----------------|
| HMAC chain | Records not modified since written | Operator holds the secret |
| ML-DSA-65 checkpoint | Chain head signed by this key, quantum-safe | Operator's key |
| Rekor anchor | Chain head existed at time T | None, the log is public |
