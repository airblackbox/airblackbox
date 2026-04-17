# Email to Accenture

**To**: arnab.chakraborty@accenture.com
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act compliance scanner for responsible AI assessments

---

Hey Arnab,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

Congratulations on the Chief Responsible AI Officer role. Building an enterprise-wide responsible AI program across a company the size of Accenture is no small thing, and the framework you've put in place for tracking, assessing, and monitoring AI systems is exactly what most organizations need to be doing before August 2026.

I built AIR Blackbox to give teams a fast, concrete answer to the question "where are we on EU AI Act compliance at the code level?" The scanner analyzes Python AI codebases and maps technical patterns to Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security. It produces a per-article breakdown in about 30 seconds.

I've scanned 30+ major open-source AI projects. The average static compliance score is 25%. The gaps are usually in record-keeping and human oversight, which are exactly the areas regulators will focus on first.

**Why this might fit into Accenture's Responsible AI practice:**

- **Zero data exfiltration.** The scanner runs entirely locally. No API calls, no cloud uploads. Client code stays on their infrastructure. For the clients Accenture advises, this is non-negotiable.
- **Open source (Apache 2.0).** Fully inspectable. Your Responsible AI team can validate every check against the regulation, adapt the methodology, and recommend it with full transparency.
- **Bridges policy and implementation.** Accenture's advisory work establishes AI governance policies. AIR Blackbox checks whether the code actually implements them. Policy says "maintain audit trails" and the scanner verifies structured logging exists.

You can try the live demo without installing anything: https://airblackbox.ai/demo

Or run it locally:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built trust layers for popular agent frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, Agno) that add HMAC-SHA256 tamper-evident audit chains. These produce the kind of cryptographically verifiable compliance artifacts that hold up under regulatory scrutiny.

**To be clear**: the scanner is a technical linter for AI governance, not a legal compliance tool. It identifies code patterns mapped to EU AI Act requirements and gives engineering teams a prioritized remediation path.

Would love to hear if this aligns with what your team is seeing in client engagements. Happy to do a live walkthrough or scan a sample codebase together.

Best,
Jason Shotwell
https://airblackbox.ai
