---
description: Export a signed compliance evidence package as JSON or PDF for regulatory handoff
---

# /air-evidence

Generate a signed evidence package for regulatory audits.

## Steps

1. Export the evidence package as JSON:

```bash
evidencectl export --secret $GATEWAY_SECRET --output evidence-package.json
```

2. Generate a PDF compliance report:

```bash
evidencectl pdf --input evidence-package.json --output evidence-report.pdf --company "Your Company Name"
```

3. The PDF report includes:
   - Cover page with gateway ID, chain integrity status, and time range
   - Executive summary with aggregate compliance stats
   - Compliance controls table (SOC 2 + ISO 27001) with pass/fail/partial status
   - Audit chain verification summary
   - Recent audit entries with sequence numbers and record hashes
   - HMAC-SHA256 attestation for tamper verification

4. To verify the attestation hasn't been tampered with:
   - The attestation field is an HMAC-SHA256 hash of the entire package
   - Clear the attestation field, re-hash the JSON with the gateway secret
   - If the hashes match, the package is authentic

5. Remind the user:
   - This is technical evidence, not a legal compliance certificate
   - Pair with legal counsel for regulatory submissions
   - The evidence package is signed — any modification breaks the attestation
