# FT1000 Pitch: ML6

**To**: info@ml6.eu (Nicolas Deruytter, CEO)
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scanning for ML6's AI deployments

---

Hey Nicolas,

Congratulations on the FT1000 recognition again. Building Europe's largest independent ML engineering team out of Ghent, with offices in Berlin, Amsterdam, and Munich, puts ML6 in a unique position: you're deploying AI systems across the EU for enterprise clients, which means both you and your clients are directly subject to the EU AI Act.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It maps Python code patterns to Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security.

I scanned 8 popular open-source AI frameworks and the average compliance score was 24%. The pattern: documentation and type safety are usually decent, but record-keeping (Art. 12) and human oversight (Art. 14) are nearly always missing. For ML6's enterprise AI deployments, especially Oscar (voice AI for HR) and PalmeChat (investigation tool for cold cases), both of those articles carry serious regulatory weight.

The scanner runs locally with zero data exfiltration:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains and trust layers for 6 frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, RAG). One import adds cryptographically verifiable records of every LLM call and agent action.

For an ML consultancy deploying AI into regulated industries across the EU, being able to hand clients a compliance scan report alongside the deliverable is a differentiator. Happy to walk through how AIR Blackbox could fit into ML6's delivery process.

Best,
Jason Shotwell
https://airblackbox.ai
