# Email to LiteLLM Team

**To**: krrish@berri.ai, ishaan@berri.ai
**From**: jason.j.shotwell@gmail.com
**Subject**: Open-source EU AI Act compliance tooling for LiteLLM

---

Hey Krrish and Ishaan,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran LiteLLM through the scanner and wanted to share what I found. Given the scale of LiteLLM's adoption (3.4M daily downloads), I think this could be useful as you're thinking about trust and security going forward.

**What the scan found (48% score, 22/45 checks passing):**

Where LiteLLM is strong:
- Input validation patterns are solid (Art. 10)
- Logging infrastructure exists in many modules (Art. 12)
- Rate limiting and permission checks present in parts of the codebase (Art. 14)

Where the gaps are:
- Risk classification and fallback patterns are sparse (Art. 9)
- Docstring and type hint coverage is uneven across modules (Art. 11)
- Injection defense and output validation could be stronger (Art. 15)

**What the scanner does:** It checks for technical patterns in Python code that map to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. No scanner can tell you "you're compliant," but it can tell you where the technical gaps are. Everything runs locally, no data leaves your machine.

**Why I'm reaching out now:** The EU AI Act enforcement deadline is August 2026. Every major AI project is going to need to demonstrate technical compliance. I built drop-in trust layers for OpenAI SDK (which LiteLLM wraps) that add HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks:

```python
import air_blackbox
air_blackbox.attach("openai")
```

The audit chain produces cryptographically verifiable records of every LLM call. Each entry is hash-chained so tampering is detectable. That's the kind of evidence that holds up in a real audit.

I'd be happy to collaborate on improving LiteLLM's compliance coverage, whether that's a PR with the trust layer, helping your team run the scanner, or just sharing what I've learned building this. Given your scale, any improvements would have massive downstream impact for the whole ecosystem.

Scanner: https://github.com/air-blackbox/gateway
PyPI: pip install air-blackbox
Demo: https://airblackbox.ai/demo

Best,
Jason Shotwell
https://airblackbox.ai
