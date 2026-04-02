# Pitch: AI Safety Newsletter (CAIS)

**To**: contact@safe.ai
**From**: jason@airblackbox.ai
**Subject**: Open-source compliance scanner with HMAC-SHA256 tamper-evident audit chains for AI systems

---

Hi,

I'm Jason Shotwell, the maintainer of AIR Blackbox, an open-source (Apache 2.0) EU AI Act compliance scanner for Python AI projects.

I'm reaching out because AIR Blackbox addresses a concrete AI safety concern: the lack of verifiable, tamper-evident records in AI agent systems. I scanned 8 popular open-source AI frameworks (342K+ combined GitHub stars) and found that zero had tamper-evident audit chains. Record-keeping (EU AI Act Art. 12) was consistently the weakest area across every project.

What the scanner does: it maps static code patterns to EU AI Act Articles 9 through 15, covering risk management, data governance, documentation, record-keeping, human oversight, and cybersecurity. It runs locally with zero data exfiltration.

What makes it relevant to AI safety beyond compliance:

The tool includes HMAC-SHA256 tamper-evident audit chains that create cryptographically verifiable records of every LLM call, agent action, and tool invocation. If an AI agent takes an action, there's a signed, non-repudiable log of exactly what happened. This is the technical infrastructure needed for meaningful AI accountability, not just regulatory checkboxes.

We also built drop-in trust layers for 7 agent frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, RAG, Agno) that add these safety mechanisms with a single import:

```python
import air_blackbox
air_blackbox.attach("crewai")
```

The deepset/Haystack team has been collaborating on the product direction. The August 2, 2026 EU AI Act enforcement deadline is creating urgency, but the underlying safety gaps exist regardless of regulation.

Would this be relevant for your newsletter? Happy to provide scan data or a technical deep-dive on the audit chain architecture.

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
