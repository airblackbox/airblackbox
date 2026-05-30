# AIR Blackbox North Star: The Audit Layer for AI Transactions

Status: Living document. Written May 30 2026. This is the project's compass.
When a decision is unclear, it should serve this vision or it is out of scope.

## The one sentence

AIR Blackbox makes every consequential AI decision carry verifiable proof that
it was made compliantly, the same way every material financial event carries an
audit trail. We call that proof a transaction receipt.

## The core noun: the transaction receipt

Competitors sign "agent actions." We certify "transactions." Only one of those
is a category a regulated industry (lending, insurance, hiring, valuations,
diagnostics) already understands and already has to audit. The receipt is the
atom of the whole product. Everything else is the receipt applied or packaged.

A transaction receipt answers four questions about one AI decision:
  1. Under what rules was it made?        (the covenant, hashed into the receipt)
  2. What was authorized?                  (permit / forbid / require_approval)
  3. What actually happened?               (the sealed execution result)
  4. Can a stranger verify all of the above without trusting us?  (the signature)

The code already has this class: ActionReceipt in sdk/air_blackbox/gate/receipt.py.
The vision is not a new build. It is finishing and naming what already exists.

## The four layers (build inward-out, never skip)

    [ Layer 4: PLATFORM ]      hosted receipts, dashboards, per-industry packs
            ^                  (a real business; DO NOT build until 1-3 have users)
            |
    [ Layer 3: SCANNER ]       air-blackbox comply, the free pre-deploy funnel
            ^                  (already shipped; how developers find us)
            |
    [ Layer 2: BUNDLE  ]       receipts + scan, zipped with an offline verifier
            ^                  (the "every transaction carries evidence" artifact)
            |
    [ Layer 1: RECEIPT ]       the verifiable transaction receipt. THE ATOM.
                               (gate shipped; verifiable signing is the gap)

If Layer 1 is bulletproof, the rest is thin glue. If Layer 1 is not real, no
amount of Layer 4 makes the vision true. Build the atom first.

## Honest current state (verified May 30 2026)

REAL and shipped (in air-blackbox 1.12.2 on PyPI):
  - The gate: authorize() returns permit/forbid/require_approval, bilateral
    ActionReceipt binds authorization to execution, seal + verify works.
  - The scanner: air-blackbox comply runs 50+ checks across Articles 9-16 + GDPR.
  - CLI: comply, discover, export, history, validate. CI gate on every push.

NOT real yet (the gap between vision and fact):
  - Default install signs HMAC-SHA256, which is NOT third-party verifiable.
    So "verifiable receipt" is not true by default today. This is THE gap.
  - The self-verifying evidence bundle is built but unwired, and its verifier
    checks a different chain format than production writes (would FAIL on real
    evidence). So "every transaction carries a verifiable bundle" is not true yet.

The two gaps above are already specced as gated tasks (see Build sequence).

## Build sequence (each phase ends with something real and is gated by a test)

PHASE 1 — The verifiable receipt
  Spec: docs/TASK-verifiable-signing.md
  Goal: a default `pip install` signs Ed25519, each receipt carries its own
        method + public key, and a stranger verifies it from the JSON alone.
  Ship criteria: the acceptance test in that spec passes (sign, verify from JSON
        with no signer object, tamper one byte -> FAIL). Release as 1.12.3.
  Why first: "verifiable" is the center of gravity of the whole vision. Until a
        default install produces a verifiable receipt, everything above is words.

PHASE 2 — The self-verifying bundle
  Spec: docs/TASK-evidence-bundle-wiring.md
  Goal: air-blackbox export --format evidence produces a .air-evidence.zip whose
        bundled verify.py gives an auditor PASS/FAIL offline, stdlib only.
  Depends on: Phase 1 (the bundle packages real verifiable receipts).
  Ship criteria: the acceptance test passes (real bundle -> PASS; one byte
        flipped -> FAIL; runs on a clean machine with nothing installed).

PHASE 3 — Name it the transaction layer
  Goal: position the receipt + bundle as "the audit layer for AI transactions."
        Lead with recruiting/hiring AI as the worked example (the one vertical
        Jason can speak natively and that the EU AI Act names high-risk), and
        present other industries as the expanding frontier, not equal claims.
  Depends on: Phases 1 and 2 (the claim must be backed by working capability).
  Ship criteria: README + site + the flagship post describe only what the
        product actually does, deadline language matches the Omnibus reality,
        and the verify.py / signing claims are true by default.

  -------------------- CUT HERE if time or focus runs short --------------------
  Everything above is the defensible product. Everything below is the business
  built on top of it, and only earns attention once Phases 1-3 have real users.

PHASE 4+ — The platform (NOT NOW)
  Hosted receipt storage, dashboards, per-industry templates, a public registry
  of verifiable transactions. This is where the revenue and the acquisition
  story live. It is a real future. It is also the trap if built early. Revisit
  only when Phases 1-3 are done and people are generating receipts in the wild.

## Positioning (why "receipt" beats "agent action")

  - asqav and Armorer sign agent actions for developers. Horizontal, crowded.
  - AIR Blackbox certifies transactions for regulated industries. The receipt
    maps to a thing auditors, insurers, and regulators already demand proof of.
  - Defensible edge = the combination none of them has all of: free pre-deploy
    scanner (funnel) + verifiable signed receipt + self-verifying bundle +
    multi-framework mapping + open source + a named vertical (hiring) where the
    founder has 13 years of domain expertise a generalist tool cannot fake.
  - The horizontal players prove the tech is competitive. The transaction frame
    and the hiring vertical are the lanes that are ours alone.

## The discipline rule (the lesson that produced this doc)

Never claim a capability the installed package does not deliver. Every layer
ships only after its tamper/acceptance test passes. The product does the
arguing; we do not write checks the code cannot cash. This rule exists because
the project once shipped broken releases that passed CI by never testing the
thing users install. That class of failure is now closed. Keep it closed.

## Technical decisions log

Decision: The receipt is the core noun, not the scan.
  Alternatives: stay a "compliance scanner" (developer tool framing).
  Rationale: "scan" is a tool; "receipt/transaction" is infrastructure under an
    industry. The latter is the category competitors cannot easily enter.
  Revisit when: a regulated buyer tells us a different noun lands better.

Decision: Build the atom (receipt) before the platform.
  Alternatives: build hosted dashboards now to look like a product.
  Rationale: an unverifiable receipt with a beautiful dashboard is still
    unverifiable. The primitive is the moat; the platform is glue.
  Revisit when: Phases 1-3 done and receipts exist in the wild.

Decision: Ed25519 as the signing floor, ML-DSA-65 as opt-in extra.
  Alternatives: HMAC default (current), or oqs hard dependency.
  Rationale: Ed25519 is third-party verifiable and installs cleanly everywhere;
    oqs can be finicky per-platform, so make post-quantum an explicit [pqc] opt-in.
  Revisit when: oqs packaging is reliably installable as a hard dependency.
