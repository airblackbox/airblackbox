# Pitch: Turing Post

**To**: ks@turingpost.com (Ksenia Se)
**From**: jason@airblackbox.ai
**Subject**: I scanned 8 popular AI frameworks for EU AI Act compliance. The results surprised me.

---

Hey Ksenia,

I built AIR Blackbox, an open-source EU AI Act compliance scanner for Python AI projects. Think of it as a linter for AI governance: it maps code patterns to Articles 9 through 15 and tells you where the gaps are.

I've scanned 8 popular open-source AI frameworks and the data is interesting:

| Project | GitHub Stars | Compliance Score |
|---------|-------------|-----------------|
| LiteLLM | 23K+ | 48% |
| LlamaIndex | 48K+ | 41% |
| CrewAI | 44K+ | 37% |
| Evidently AI | 18K+ | 33% |
| BentoML | 8.5K+ | 29% |
| Giskard | 5.1K+ | 24% |
| ClearML | 5.8K+ | 24% |
| Jina AI | 21.9K+ | 18% |

Average: 24%. Record-keeping and human oversight are the weakest areas across the board. One major agent framework scored 0/9 on human oversight. Zero frameworks had tamper-evident audit chains.

The tool is Apache 2.0, runs locally, and ~1,700 developers install it each month from PyPI. The deepset/Haystack team has been involved in shaping the product.

I think your 100K+ readers would find the scan data useful, especially with the August 2026 enforcement deadline approaching. Happy to write a guest post breaking down the findings, or provide a scan on any framework your audience uses.

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
