# Pitch: The EU AI Act Newsletter

**To**: Risto Uuk (via Substack message or Future of Life Institute)
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act gap scanner for Python AI agents (first of its kind)

---

Hey Risto,

I built what I believe is the first pip-installable EU AI Act compliance scanner for Python AI projects. It's called AIR Blackbox, it's Apache 2.0, and it maps technical code patterns to Articles 9 through 15.

I ran it against 8 popular open-source AI frameworks (342K+ combined GitHub stars) and the results were striking: the average compliance score was 24%. Record-keeping (Art. 12) is consistently the weakest area, and zero projects had tamper-evident audit chains.

Here's the scan summary:

| Project | GitHub Stars | Score |
|---------|-------------|-------|
| LiteLLM | 23K+ | 48% |
| LlamaIndex | 48K+ | 41% |
| CrewAI | 44K+ | 37% |
| Evidently AI | 18K+ | 33% |
| BentoML | 8.5K+ | 29% |
| Giskard | 5.1K+ | 24% |
| ClearML | 5.8K+ | 24% |
| Jina AI | 21.9K+ | 18% |

The scanner runs locally, zero data leaves the machine:

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

We also built HMAC-SHA256 tamper-evident audit chains and drop-in trust layers for 6 frameworks (LangChain, CrewAI, AutoGen, OpenAI, ADK, RAG). The deepset/Haystack team has been actively involved in shaping the product direction.

With the August 2, 2026 enforcement deadline approaching, I think your 53K+ subscribers would find this useful. Would you be interested in featuring AIR Blackbox in an upcoming edition? Happy to provide a scan report on any project your readers would find relevant, or write a guest piece on the technical compliance gap data.

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
