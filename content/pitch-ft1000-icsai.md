# FT1000 Pitch: ICS.AI

**To**: info@ics.ai (Martin Neale, Founder/CEO)
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance for public sector AI (high-risk classification)

---

Hey Martin,

Congratulations on the FT1000 recognition. Processing 11 million resident interactions and identifying £12M in savings for Derby City Council shows real impact.

I'm reaching out because public sector AI deployments are classified as HIGH-RISK under the EU AI Act. AI systems used in public administration, benefits assessment, and citizen services fall under Annex III. While the UK isn't directly subject to the EU AI Act, the UK government's own AI regulation framework is aligning closely with EU standards, and any ICS.AI deployments for EU-based public sector organizations would be directly regulated.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It maps Python code patterns to Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security.

For public sector AI, the most critical requirements are:

- **Art. 14 (Human Oversight)**: Citizens must have recourse to human review of AI decisions that affect them
- **Art. 12 (Record-Keeping)**: Every AI-influenced decision about a resident needs a tamper-evident audit trail
- **Art. 10 (Data Governance)**: Resident data used to train or operate AI must be governed with transparency

The scanner runs locally with zero data leaving your machine:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains that create non-repudiable records of every AI decision. For a platform processing millions of resident interactions, that's the kind of evidence councils need when constituents or regulators ask questions.

Happy to walk through what a scan looks like for ICS.AI's SMART platform.

Best,
Jason Shotwell
https://airblackbox.ai
