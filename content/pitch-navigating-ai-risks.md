# Pitch: Navigating AI Risks

**To**: Siméon Campos (via Substack message at navigatingairisks.substack.com)
**From**: jason@airblackbox.ai
**Subject**: Quantified compliance gaps across 8 major AI frameworks (data for your readers)

---

Hey Siméon,

I built AIR Blackbox, an open-source EU AI Act compliance scanner that maps Python code patterns to Articles 9 through 15. I've been scanning popular AI frameworks and quantifying their compliance gaps.

The data tells a clear risk story: across 8 major open-source AI frameworks (342K+ combined GitHub stars), the average compliance score is 24%. The riskiest finding: human oversight mechanisms (Art. 14) are completely absent from some frameworks, and none have tamper-evident audit chains for record-keeping (Art. 12).

This matters because these are the frameworks powering enterprise AI deployments. When a Fortune 500 company builds a RAG pipeline on LlamaIndex or deploys multi-agent workflows on CrewAI, they're inheriting these compliance gaps.

The scanner is open source (Apache 2.0) and runs locally:

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I think the scan data and the patterns it reveals would be relevant to your readers who are thinking about AI risk in practical terms. Happy to share the full scan reports or write a guest piece on the risk implications.

Best,
Jason Shotwell
https://airblackbox.ai
