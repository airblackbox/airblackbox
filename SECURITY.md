# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in AIR Blackbox Gateway, please report it responsibly.

**Email:** jason@airblackbox.ai
**Subject line:** `[SECURITY] AIR Blackbox Gateway — <brief description>`

We will acknowledge your report within 48 hours and aim to provide a fix or mitigation within 7 days for critical issues.

Please **do not** open a public GitHub issue for security vulnerabilities.

## What Data AIR Blackbox Gateway Stores

The gateway records AI system interactions. Here is exactly what is stored and where:

| Data | Where It Goes | Who Controls It |
|---|---|---|
| Raw prompts & completions | **Your** MinIO/S3 vault (never leaves your infrastructure) | You |
| Vault references (URIs, not content) | OTel traces → your collector → your Jaeger/Grafana | You |
| Model name, token counts, timing | OTel span attributes | You |
| Run ID, trace ID, timestamps | `.air.json` record files on your filesystem | You |
| SHA-256 checksums of request/response | `.air.json` record files | You |

## What AIR Blackbox Gateway Does NOT Do

- **No phone-home.** The gateway makes zero network calls except to your configured upstream LLM provider and your own infrastructure (MinIO, OTel Collector).
- **No telemetry.** We do not collect usage data, crash reports, or analytics.
- **No cloud dependency.** Everything runs on your infrastructure. There is no SaaS component.
- **No content in traces.** OTel spans contain vault references, not raw prompts or completions. Your observability stack never sees sensitive content.
- **No credential storage.** API keys are passed through to the upstream provider and are not written to AIR records or vault storage.

## Threat Model

AIR Blackbox Gateway sits in the request path between your AI agent and the LLM provider. The primary security considerations are:

1. **Vault access** — MinIO/S3 credentials control access to stored prompts and completions. Protect these credentials with the same rigor as your LLM API keys.
2. **AIR record files** — These contain vault references and checksums, not raw content. However, metadata (model names, timestamps, token counts) may still be sensitive in some contexts. Apply appropriate filesystem permissions.
3. **Network position** — The gateway terminates your agent's API call and forwards it. It sees the full request and response in transit. Deploy it in the same trust boundary as your agent.

## Threat Model — Evidence Bundles

A `.air-evidence` bundle is meant to be handed to someone who does not trust
the party that produced it. That makes the verifier a different security
problem from the gateway, with a different adversary: usually the **issuer**,
not an outsider.

**What `air-evidence verify` establishes.** The bundle is internally
consistent — records, chain, receipts, per-file digests and declared counts
all agree — and nothing has been altered since it was signed. When check 6
reports a verified RFC 3161 anchor, an external timestamp authority witnessed
the chain head at a point in time, which is the property that makes an
operator rewrite detectable.

**What it does not establish.** That the bundle was issued by any particular
party. The signature is checked against a public key carried *inside* the
bundle, so anyone can generate a key, assemble a bundle, and sign it. The
verifier prints the signing key fingerprint; comparing it against a value
obtained out-of-band is currently the reader's job, and nothing in the tool
says so loudly enough. This is tracked as finding 4 in the red-team review
below.

**What no verifier can establish.** Whether records were left out before
export, and whether a named human reviewer genuinely reviewed anything.
External anchoring at recording time constrains the first. Nothing in the
format resolves the second.

## Published Security Reviews

- [Red-team findings, August 2026](docs/security/red-team-2026-08.md) — 75
  adversarial attacks against the evidence bundle verifier. 17 confirmed
  breaks across 8 root causes: 3 fixed, 5 open with mitigations. Unfixed
  findings are published deliberately, because the people relying on a
  `VERIFIED` result need to know what it does and does not prove.

## Supported Versions

| Version | Supported |
|---|---|
| Latest on `main` | Yes |
| Older commits | Best effort |

## Responsible Disclosure

We follow coordinated disclosure. If you report a vulnerability, we will:

1. Acknowledge receipt within 48 hours
2. Provide an estimated timeline for a fix
3. Credit you in the release notes (unless you prefer anonymity)
4. Not pursue legal action against good-faith security researchers
