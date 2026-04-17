# Outreach: LiteLLM / BerriAI Team

**To**: Krrish Dholakia, Ishaan Jaffer (BerriAI/litellm maintainers)
**Emails**: krrish@berri.ai, ishaan@berri.ai (publicly listed in LiteLLM contributing guidelines)
**LinkedIn**: linkedin.com/in/krish-d, linkedin.com/in/reffajnaahsi
**Channel**: GitHub Issue on BerriAI/litellm first, then direct email same day
**Subject**: EU AI Act compliance scan + trust layer offering (timely given recent events)
**Timing**: URGENT. The Delve/supply chain scandal is still front-page news. LiteLLM is actively rebuilding trust. This is the moment.

---

## Context (for Jason, not for the email)

LiteLLM just got hit with a double crisis:
1. **Supply chain attack**: Malicious PyPI packages (v1.82.7, v1.82.8) compromised with credential stealers. Mandiant investigation ongoing.
2. **Delve scandal**: LiteLLM's SOC2 and ISO 27001 certifications were done through Delve, the YC startup accused of generating fake compliance data and rubber-stamping audits. TechCrunch broke this March 26.

This means LiteLLM NEEDS to demonstrate real, verifiable technical compliance. Not another checkbox vendor. Open-source, auditable tooling. That's exactly what AIR Blackbox is.

---

## GitHub Issue Title

EU AI Act Technical Compliance Scan: Results and Open-Source Trust Layer

## Body

Hey Krrish and Ishaan,

First: respect for how you're handling the supply chain incident. Rebuilding trust after something like that is hard, and doing it transparently matters.

I ran LiteLLM through AIR Blackbox, an open-source EU AI Act compliance scanner. Given everything happening right now, I thought you might find verifiable, open-source compliance tooling useful.

**Summary**: 48% compliance score from the GitHub Actions scan (22/45 aggregate checks passing).

Here's what stood out:

**Where LiteLLM is strong:**
- Input validation patterns are solid (Art. 10)
- Logging infrastructure exists in many modules (Art. 12)
- Some rate limiting and permission checks present (Art. 14)

**Where the gaps are:**
- Risk classification and fallback patterns are sparse (Art. 9)
- Docstring and type hint coverage is uneven (Art. 11)
- Injection defense and output validation could be stronger (Art. 15)

**To be clear**: the scanner checks for technical patterns that map to EU AI Act Articles 9-15. It's a linter, not a legal compliance tool. No scanner can tell you "you're compliant." But it can tell you where the technical gaps are.

The scanner is already seeing adoption (1,700+ installs this month, 400+/day) and all trust layers are open source (Apache 2.0): https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

We also have drop-in trust layers for OpenAI SDK (which LiteLLM wraps) that add HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks. Single import, no changes to your application code:

```python
import air_blackbox
air_blackbox.attach("openai")
```

The audit chain produces cryptographically verifiable records of every LLM call. Every entry is hash-chained so tampering is detectable. That's the kind of evidence that holds up in an actual audit, not a checkbox from a vendor.

Happy to collaborate on getting LiteLLM's score up. Given your scale (3.4M daily downloads), any improvements you make would have massive downstream impact.

Best,
Jason Shotwell
https://airblackbox.ai

---

## Follow-up Strategy (for Jason)

1. **Post the GitHub issue first** (public, builds credibility)
2. **Share the TechCrunch article on Twitter/LinkedIn** with commentary about how open-source compliance tooling is the answer to the Delve problem, tag @LiteLLM
3. **If they engage**: offer to PR the trust layer directly into LiteLLM's codebase
4. **If they don't respond in 5 days**: follow up on Twitter, reference the issue
5. **Nuclear option**: Write a Dev.to article "I Scanned LiteLLM After the Delve Scandal" with the results. They'll see it.
