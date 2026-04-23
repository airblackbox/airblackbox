# Enterprise Email Template: General Enterprise (Workflows + Governance Risk)
# EU AI Concern: Employee/customer workflows + governance risk
# Target Buyer: CTO / CIO / Head of AI Platform
# NOTE: This is the largest segment (73 companies)

**To**: [EMAIL]
**From**: jason@airblackbox.ai
**Subject**: [COMPANY] + EU AI Act — do you know where all your AI agents are?

---

Hey [FIRST_NAME],

I'm Jason, the creator of AIR Blackbox — an open-source EU AI Act compliance toolkit (Apache 2.0, ~1,700 installs/month on PyPI).

I saw that [COMPANY] is using AI agents in production [via PLATFORM]. That's great — but with the EU AI Act enforcement starting August 2, 2026, every company with AI touching EU customers or employees needs to answer a question most can't yet: *where are all our AI agents, and can we prove they're compliant?*

The challenge isn't whether your agents work. It's whether you can show a regulator — or your own board — that they have the right controls:

- **Risk classification** — which of your AI systems are high-risk under the Act?
- **Audit trails** — can you produce tamper-evident logs of what your agents did, when, and why?
- **Human oversight** — do your agent workflows have kill switches and approval gates?
- **Data governance** — is there documentation on how training data was sourced and validated?
- **Security** — are inputs validated and outputs bounded?

**AIR Blackbox is a compliance scanner and trust layer built for exactly this.** It scans Python codebases and AI pipelines against EU AI Act Articles 9–15, surfaces the gaps, and gives you a clear picture of what's covered and what's not. The trust layers drop into LangChain, CrewAI, OpenAI, and other frameworks to add HMAC-SHA256 audit chains — so every agent action has a cryptographically signed evidence trail.

Everything runs locally. No data leaves your machine.

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

For teams managing AI across multiple vendors and internal builds, the cross-vendor inventory and compliance mapping is usually what clicks first — it turns "we think we're covered" into "here's exactly where we stand, article by article."

We also offer an enterprise Verified Scan Package ($299) that generates audit-ready reports your compliance team can hand to regulators.

Happy to show you what the scanner finds across a real enterprise stack. 15 minutes, no pitch.

Best,
Jason Shotwell
https://airblackbox.ai
