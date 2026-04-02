# FT1000 Pitch: LoanTube

**To**: gurprit@loantube.com (Gurprit Singh Gujral, CEO/Founder)
**From**: jason@airblackbox.ai
**Subject**: EU AI Act high-risk classification for AI credit decisions (August 2026 deadline)

---

Hey Gurprit,

Congratulations on the FT1000 recognition. Processing 10,000+ loan applications per day with an AI-driven decision engine is impressive growth.

I'm reaching out because AI-powered credit scoring and lending decisions are explicitly classified as HIGH-RISK under the EU AI Act (Annex III, Section 5b). That means LoanTube's AI systems will need to meet the full requirements of Articles 9 through 15 before the August 2, 2026 enforcement deadline. The penalties are up to 7% of global turnover.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It checks Python AI codebases against the technical requirements: risk management documentation, data governance, audit trails, human oversight mechanisms, and security.

For a fintech making automated credit decisions, the three most critical articles are:

- **Art. 10 (Data Governance)**: How training data is sourced, validated, and governed. Bias in credit data directly translates to discriminatory lending.
- **Art. 12 (Record-Keeping)**: Every AI credit decision needs a tamper-evident audit trail. Not just logs. Cryptographically verifiable records.
- **Art. 14 (Human Oversight)**: Regulators need to see that a human can review, override, or halt AI credit decisions.

The scanner runs entirely on your infrastructure. Zero data leaves your machine:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains that create non-repudiable records of every decision your AI makes. For an FCA-authorized lender that will also need to comply with the EU AI Act, that's the kind of infrastructure your compliance team will need.

Happy to do a quick walkthrough of what the scanner finds and what it means for LoanTube's specific risk classification.

Best,
Jason Shotwell
https://airblackbox.ai
