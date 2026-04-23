# Enterprise Email Template: Consumer-Facing Brands (Retail, CPG, Media, Hospitality)
# EU AI Concern: Consumer interactions + transparency obligations
# Target Buyer: VP CX / CIO / Head of AI

**To**: [EMAIL]
**From**: jason@airblackbox.ai
**Subject**: [COMPANY]'s AI agents — EU AI Act transparency rules start in 104 days

---

Hey [FIRST_NAME],

I'm Jason, the creator of AIR Blackbox — an open-source EU AI Act compliance toolkit (Apache 2.0, ~1,700 installs/month on PyPI).

I saw [COMPANY] is using AI agents for customer interactions [via PLATFORM]. Under the EU AI Act (enforcement starts August 2, 2026), any AI system that interacts directly with consumers in the EU needs to meet specific transparency and disclosure requirements — Article 52 requires that people know they're interacting with AI, and Articles 12–14 require logging and human oversight of those interactions.

For consumer-facing brands, this isn't just a compliance checkbox. It's a trust question: can you show your customers (and regulators) exactly what your AI agents are doing, what data they're using, and that a human can intervene when needed?

**AIR Blackbox scans your AI systems against EU AI Act Articles 9–15** and tells you exactly where you stand:

- **Transparency gaps** — AI disclosure patterns, explainability, consumer notification
- **Logging gaps** — structured audit trails for every agent interaction
- **Human oversight gaps** — kill switches, escalation paths, approval workflows
- **Security gaps** — input validation, output bounding, injection defense

The scanner works on any Python-based AI system. The trust layers drop into LangChain, CrewAI, OpenAI, and other frameworks with two lines of code, adding HMAC-SHA256 tamper-evident audit chains to every agent action.

Everything runs locally — no customer data leaves your environment:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

We also offer an enterprise Verified Scan Package ($299) that generates audit-ready compliance reports — the kind of documentation your legal and compliance teams can actually use.

For brands that depend on consumer trust, being able to say "our AI agents are EU AI Act compliant" is going to become table stakes. Happy to show you what the scanner surfaces for a customer-facing AI stack.

Best,
Jason Shotwell
https://airblackbox.ai
