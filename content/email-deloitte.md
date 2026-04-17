# Email to Deloitte

**To**: gstrojin@deloittelegal.si
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act scanner your compliance teams might find useful

---

Hey Gregor,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I've been following the work your AI Regulatory Center of Excellence is doing on EU AI Act readiness across Central Europe. With the August 2026 enforcement deadline four months out, I imagine your teams are getting a lot of client requests for technical compliance assessments.

AIR Blackbox scans Python AI codebases and maps technical patterns to Articles 9 through 15. It checks for things like error handling and fallback patterns (Art. 9), input validation and PII handling (Art. 10), docstrings and type hints (Art. 11), structured logging and audit trails (Art. 12), human oversight controls (Art. 14), and injection defense and output validation (Art. 15). It generates a per-article compliance breakdown in about 30 seconds.

I've scanned 30+ major open-source AI projects so far. The average static compliance score is around 25%. Most teams don't know where their gaps are until they see the report.

**Why this might matter for Deloitte's practice:**

- **No client data leaves the machine.** The scanner runs entirely locally. No API calls, no cloud processing, no data exfiltration risk. Your clients' code stays on their servers.
- **Open source (Apache 2.0).** Your teams can inspect the source, validate the methodology, and recommend it with confidence.
- **Scales across engagements.** One `pip install` and your consultants can scan any Python AI project in a client's environment.

You can try the live demo without installing anything: https://airblackbox.ai/demo

Or run it locally:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built trust layers that add HMAC-SHA256 tamper-evident audit chains for popular agent frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, Agno). These generate the kind of cryptographically verifiable compliance artifacts that hold up in regulatory review.

**To be clear**: the scanner is a linter for AI governance, not a legal compliance tool. It identifies technical patterns mapped to EU AI Act requirements. It's the technical layer that complements the legal and policy work your teams already do.

Would love to get your take on whether this fits into the advisory work you're doing with clients. Happy to do a walkthrough or scan a sample project together.

Best,
Jason Shotwell
https://airblackbox.ai
