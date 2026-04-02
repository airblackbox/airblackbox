# FT1000 Pitch: Phyron

**To**: mattias.kellquist@phyron.com (Mattias Kellquist, CEO)
**From**: jason@airblackbox.ai
**Subject**: EU AI Act transparency requirements for AI-generated video content

---

Hey Mattias,

Congratulations on the FT1000 ranking and the CEO transition. Generating 700,000 AI videos per month for automotive retail is serious scale.

I'm reaching out because generative AI content has specific transparency requirements under the EU AI Act. Article 50 requires that AI-generated content must be clearly disclosed as such, and the systems producing it must be documented. For Phyron, that means every AI-generated vehicle video needs a provable chain of documentation showing how it was created, what models were used, and that it's been disclosed as AI-generated.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It checks Python AI codebases against Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security.

The scanner runs locally with zero data leaving your machine:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains that create cryptographically verifiable records of every AI generation. For a company producing 700K videos/month, having a tamper-proof record of what was generated, when, and by which model is exactly what regulators will ask for.

The August 2, 2026 enforcement deadline is approaching fast. Happy to do a quick walkthrough of what the scanner finds on your codebase.

Best,
Jason Shotwell
https://airblackbox.ai
