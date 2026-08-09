# Red-team findings: evidence bundle verifier, August 2026

This document records an adversarial review of `air-evidence verify` and the
`.air-evidence` v1 bundle format, including findings that are **not yet
fixed**. All eight root causes have now been addressed. Finding 4 is
mitigated rather than eliminated: what remains is a property of any
self-describing bundle, and is stated plainly below rather than engineered
around.

We publish unfixed findings because of who relies on this tool. The party
reading a `VERIFIED` result is usually an auditor, a regulator, or a customer
checking somebody else's claim — and the threat they care about is a
*dishonest issuer*, not an outside attacker. Telling those readers exactly
what the verifier does and does not establish protects them. Withholding it
protects nobody but us.

## Method

75 attacks across six lenses: ZIP container structure, manifest semantics,
records and chain, receipts and counts, external anchoring, and finding
attribution. Every claimed break went to an independent reviewer instructed to
refute it and to default to "refuted" when it could not be reproduced exactly.
23 attacks were held off by the existing code. 43 were claimed as breaks.
**17 survived refutation**, reducing to 8 distinct root causes.

A break means: `verify_bundle()` returns normally on a bundle whose
evidentiary content has been changed, added to, removed, or misrepresented,
*without access to the signing private key*. Passing with the private key is
not a break — the operator holds that by design.

## Summary

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Duplicate ZIP member names | High | **Fixed** |
| 2 | Unsigned payload disguised as a directory entry | High | **Fixed** |
| 3 | Compliance counts declared but never recomputed | High | **Fixed** |
| 4 | No trust root: any key verifies | High | **Mitigated** — pinning, honest verdict, `--strict`; residual limit documented |
| 5 | Signature algorithm downgrade | Medium | **Fixed** |
| 6 | Public transparency-log anchor is forgeable | High | **Fixed** |
| 7 | Empty record set degenerates the anchor check | Medium | **Fixed** |
| 8 | `signature` sub-object excluded from the signed digest | Low | **Fixed** |

---

## Fixed

### 1. Duplicate ZIP member names (High)

ZIP permits two entries with the same name. Python's `zipfile` resolves reads
to the **last** entry; `unzip -p`, streaming readers, and most other tooling
take the **first**. Writing a forged `records/actions.jsonl` first and the
genuine copy second passed every digest check:

```
verifier:   [1/6]..[6/6] OK — VERIFIED, 0 alterations
unzip -p:   "decision_type": "advance", "human_reviewer": "compliance@corp"
```

One file, certified clean, displaying a fabricated human review to whoever
opens it. The same trick applied to `manifest.json` let a forged compliance
summary sit in front of the genuine signed one.

Duplicate names are now rejected in check 1, before any digest is computed. No
legitimate bundle contains them — the generator writes each member once.

### 2. Unsigned payload disguised as a directory entry (High)

The unsigned-member guard exempted every member name ending in `/` as a
directory entry. ZIP does not enforce that: `attachments/reviewer_signoff.pdf/`
can carry a full payload. The exemption was a way straight back through the
guard it belonged to.

This was introduced by the commit that added the guard, not inherited. The
exemption now additionally requires `file_size == 0`, so genuine directory
entries still verify and payloads do not.

### 3. Compliance counts declared but never recomputed (High)

Check 5 recomputed five of the eight counts the manifest declares. The three it
skipped — `adverse_decisions`, `adverse_decisions_missing_reviewer`, and
`engine_outputs_without_reviewer` — are precisely the ones that exist to
surface human-review gaps, and the manifest's own `review_note` tells auditors
that `adverse_decisions_missing_reviewer` is the number to read first.

A bundle could therefore declare zero unreviewed adverse decisions over records
showing an unreviewed rejection, sign it validly, and verify clean. Signing a
false summary does not make it true; it makes it an attributable lie, which is
only useful if something catches it.

All eight counts are now recomputed, and a manifest that *omits* a count the
records support fails rather than escaping the comparison.

### 5. Signature algorithm downgrade (Medium)

Switching the manifest's `signature.alg` to `hmac-sha256` and supplying `--key`
took a branch that never set `manifest_pubkey_hex`, which silently disabled
check 4's rule that every receipt must be signed by the bundle's own key. The
HMAC branch now derives the key from the bundled PEM, so the receipts stay
bound to it whichever algorithm signed the manifest.

### 6. Public transparency-log anchor is forgeable (High)

`verify_bundle_anchor()` checks the embedded log receipt's signature against a
public key **the receipt itself carries**. Offline that establishes
self-consistency and nothing else: anyone can mint an Ed25519 key, sign a
payload committing to any head, attach a plausible uuid and log index, and the
verifier printed

> Public-log anchor: anchor consistent … The entry is permanent

asserting log membership it had never checked. The receipt was presented as the
stronger of the two anchoring rails while being the weaker one.

`air-evidence verify --rekor-verify` now fetches the claimed entry and confirms
it exists, that its logged payload agrees with the bundle's on `chain_head`,
`chain_seq_max` and `anchored_at`, and that the log index matches. Without the
flag the verifier says so plainly — `NOT checked against the log … this is
self-consistency only` — and the summary reports `public_log:
"embedded-only"` rather than implying corroboration.

**One honest limit remains, and it is inherent.** A public log accepts writes
from anyone. Confirming an entry exists proves the commitment was published at
that index and can never be retracted; it does not prove *who* published it.
Authority still comes from pinning the anchoring key and sweeping every entry
under it (`air-evidence audit-log`, `audit_runs_against_log`) — a rewritten
history fails against the old entries, which is the actual M2 guarantee.

### 7. Empty record set degenerates the anchor check (Medium)

`head_over_entries()` returns `""` for an empty set, so a bundle stripped of
all records produced an empty head and the anchor comparison could not execute
meaningfully. A bundle that claims an anchor but carries no chained records
now fails check 6: the timestamp commits to nothing.

### 8. `signature` sub-object excluded from the signed digest (Low)

`canonical_manifest_bytes()` excludes the `signature` object from the signed
digest — it cannot cover itself. That made its fields attacker-mutable, and
one of them mattered: `signature.public_key_hex` was the source of the
fingerprint that `--expect-key` compares against, so deleting it degraded the
printed identity to a bare algorithm name. The fingerprint is now derived from
the key material actually used to verify the signature.

### Bonus: check 4 could pass over zero receipts

Not in the original findings, surfaced while fixing 5. Records without a
receipt are skipped, so `all signatures valid` was printed over a bundle where
nothing had been checked. Gateway and trust-layer records legitimately carry no
receipts today, so this is reported rather than failed — the verifier now says
`0/N records carry a receipt - NOTHING was checked here`, and the CLI verdict
adds `authorship unevidenced`.

---

## Mitigated, with a residual limit

### 4. No trust root: any key verifies (High)

`air-evidence verify` checks the manifest signature against
`verification/public_key.pem` — a file inside the bundle. An attacker who
generates their own keypair, assembles a bundle from records of their
choosing, and signs it produces a bundle that verifies clean.

**What `VERIFIED` actually means today:** this bundle is internally
consistent and has not been altered since it was signed. **It does not mean**
the bundle was issued by any particular party.

The printed fingerprint (`signed by ed25519:0e80dd4149f3042a`) is the only
defence, and it only helps if the reader compares it to a value obtained
somewhere else.

**If you are relying on a bundle someone gave you, do this now:**

1. Obtain the issuer's expected key fingerprint through a separate channel —
   not from the bundle.
2. Compare it to the fingerprint the verifier prints. If they differ, or you
   have nothing to compare against, treat the result as unattributed.
3. Prefer anchored bundles. Check 6 reporting a verified RFC 3161 anchor means
   an external timestamp authority witnessed the chain head at a point in
   time, which a bundle fabricated later cannot reproduce.

**What changed.**

- `--expect-key <fingerprint>` pins the expected signer and fails check 2 on a
  mismatch, accepting either the full `alg:hex` form or the bare hex.
- The fingerprint is derived from the key material actually used to verify,
  not from the unsigned `signature.public_key_hex` (see finding 8).
- With nothing pinned, the verifier says so on its own line and the headline
  names the gap. The verdict enumerates every weakness it found rather than
  burying them: `VERIFIED (UNATTRIBUTED, UNWITNESSED)`.
- `--strict` exits non-zero unless the issuer was pinned, an external anchor
  verified, and any public-log receipt was checked against the log.

**Why `--strict` is not the default.** Every bundle the CLI produces today is
unanchored, so failing by default would reject the project's own output and
teach users to pass a flag that turns the checking off — the worst possible
outcome. Reporting is the default; enforcement is one flag away and is what
belongs in a procurement checklist or a CI gate.

**A correction to an earlier version of this document**, which proposed
binding the signing key into the anchored head preimage as the next step. That
was investigated and **abandoned as redundant**. Each record's `chain_hash`
covers the record *including its receipt*; receipts carry the signer's
signature; and check 4 requires every receipt to verify against the manifest's
own key. Changing the signing key therefore changes every receipt, every chain
hash, and the head — so a genuine anchor already cannot be inherited by a
bundle re-signed under a different key. Measured directly:

```
v1 head over operator-signed records : bb1c3e30575578b7fc98
v1 head over attacker-signed records : 9830dcee22e7ed7d2535
```

Adding an explicit binding would have introduced a format version marker and a
compatibility path across four call sites for no additional protection.

**The residual limit, stated plainly.** A self-describing bundle cannot
authenticate its own issuer. Pinning moves the trust decision to the reader,
where it belongs, but somebody still has to obtain the right fingerprint out
of band. An *unanchored* bundle is where this bites hardest: there is no
external witness at all, so nothing constrains a wholly fabricated bundle
beyond that comparison.

Two things would close it further, and neither is a verifier change:

- **Anchor by default everywhere.** The MCP export already anchors on every
  run. The CLI does not anchor at all, and does not produce the v1 format that
  has an anchor slot — so a CLI user cannot get an externally witnessed bundle
  today, whatever they pass to the verifier. That is a producer gap.
- **Sigstore keyless signing** (OIDC identity via Fulcio) for bundles issued
  through the hosted connector, so attribution stops depending on out-of-band
  key exchange. Self-hosted exports keep the local-key path and the caveat.




---

## Not verifier bugs: limits of the format

Worth stating plainly, because no amount of verifier hardening addresses them.

**Selective inclusion.** An operator who exports a curated subset of records
produces a bundle with valid digests, a valid chain, and a valid signature.
The verifier confirms that what is present is intact; it cannot know what was
left out. External anchoring at the time of recording is what constrains this,
because the anchored head commits to the chain as it stood then.

**Self-attested review.** A record whose `human_reviewer` names the same
identity as the acting agent is indistinguishable, to the verifier, from one
naming a genuine second person. AIR counts these; it cannot adjudicate them.

## Reporting

Security issues: **jason@airblackbox.ai**, subject `[SECURITY] AIR Blackbox — <description>`.
Please do not open a public issue.
