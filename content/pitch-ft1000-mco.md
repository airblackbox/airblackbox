# FT1000 Pitch: MCO / MyComplianceOffice

**To**: brian.fahey@mycomplianceoffice.com (Brian Fahey, CEO)
**From**: jason@airblackbox.ai
**Subject**: AI compliance for the compliance company (EU AI Act, August 2026)

---

Hey Brian,

Three consecutive years on the FT1000. That's sustained growth, not a spike. Congratulations.

I'm reaching out because MCO sits at an interesting intersection: you build compliance software for financial services, and the EU AI Act is about to create a new compliance requirement for any AI system used in regulated industries. If MCO uses AI for transaction monitoring, anomaly detection, or employee surveillance, your own platform falls under the regulation. And your clients will be asking how their compliance tools are themselves compliant.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It maps Python code patterns to Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security.

I scanned 8 popular AI frameworks and the average score was 24%. The universal gap: almost no one has tamper-evident audit chains (Art. 12). For a compliance platform that monitors 1,500+ companies across 125+ countries, having a provably tamper-proof audit trail isn't just a regulatory requirement, it's your credibility.

The scanner runs locally with zero data leaving your machine:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains that create cryptographically verifiable records of every AI decision. One import adds them to your existing Python codebase.

There might also be a partnership angle here: MCO's clients in financial services will need EU AI Act compliance tooling. AIR Blackbox could be a value-add for your platform. Happy to explore that if it's interesting.

Best,
Jason Shotwell
https://airblackbox.ai
