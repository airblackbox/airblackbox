# Red-team findings: evidence bundle verifier, August 2026

This document records an adversarial review of `air-evidence verify` and the
`.air-evidence` v1 bundle format, including findings that are **not yet
fixed**.

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
| 4 | No trust root: any key verifies | High | Open — design decision |
| 5 | Signature algorithm downgrade | Medium | Open |
| 6 | Public transparency-log anchor is forgeable | High | Open |
| 7 | Empty record set degenerates the anchor check | Medium | Open |
| 8 | `signature` sub-object excluded from the signed digest | Low | Open |

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

---

## Open

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

**Direction.** The intended fix is not a PKI. A forger can always mint a key;
what they cannot do is obtain a timestamp dated before the dispute. Planned,
in order:

- `--expect-key <fingerprint>`, and an explicit *"signer not pinned"* line in
  the summary when it is absent, so the current guarantee stops being
  overstated.
- Bind the signing key's fingerprint into the anchored head preimage.
  `head_over_entries()` currently hashes only `(chain_seq, chain_hash)` pairs,
  so a genuine anchor survives having the manifest re-signed under a different
  key. It should not.
- Require a verified anchor for a clean verdict; report an unanchored bundle as
  unverified rather than passing it with a note.
- Sigstore keyless signing (OIDC identity via Fulcio) for bundles issued
  through the hosted connector, giving real attribution without key
  management. Self-hosted exports keep the local-key path and the caveat.

### 5. Signature algorithm downgrade (Medium)

Switching the manifest's `signature.alg` to `hmac-sha256` and supplying
`--key` takes a branch that never sets `manifest_pubkey_hex`, weakening the
binding between the manifest and the per-record receipts checked in check 4.

**Mitigation:** treat any bundle whose manifest reports `hmac-sha256` as
requiring a shared secret and therefore not independently verifiable. A
genuine bundle from a normal install is Ed25519 or ML-DSA-65; `cryptography`
is a hard dependency, so the HMAC manifest path should not occur in practice.

### 6. Public transparency-log anchor is forgeable (High)

The Rekor anchor checked in step 6b can be minted by the same party producing
the bundle, committing to whatever head they chose, rather than being
validated against the public log itself.

**Mitigation:** do not treat the public-log line as independent corroboration
until this is fixed. The RFC 3161 anchor in check 6 is the meaningful external
witness today.

### 7. Empty record set degenerates the anchor check (Medium)

`head_over_entries()` returns `""` for an empty set. A bundle stripped of all
records produces an empty head, and the anchor comparison cannot execute
meaningfully.

**Mitigation:** read the record count in the verifier summary. A bundle
claiming to evidence activity should not contain zero records.

### 8. `signature` sub-object excluded from the signed digest (Low)

`canonical_manifest_bytes()` deliberately excludes the `signature` object —
it cannot cover itself. Fields inside it that are not otherwise validated,
such as `public_key_hex` when it disagrees with the bundled PEM, are
attacker-mutable. No break in signature validation follows from this on its
own; it is recorded for completeness.

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
