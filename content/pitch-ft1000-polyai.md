# FT1000 Pitch: PolyAI

**To**: contact@poly.ai (Nikola Mrkšić, CEO/Co-founder)
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance for PolyAI (FT1000 #32 + August 2026 deadline)

---

Hey Nikola,

Congratulations on the FT1000 ranking and the Series D. #1 enterprise AI company in Europe is a strong position to be in.

It also means PolyAI is exactly the kind of company the EU AI Act was built for. Enterprise conversational AI agents processing millions of customer interactions fall squarely into the high-risk category, and your enterprise customers (many of whom have EU operations) will start asking about compliance well before the August 2, 2026 enforcement deadline.

I built AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs/month on PyPI). It maps Python code patterns to Articles 9 through 15: risk management, data governance, documentation, record-keeping, human oversight, and security.

I scanned 8 popular open-source AI agent frameworks and the average score was 24%. The consistent gap: almost no one has tamper-evident audit chains (Art. 12) or adequate human oversight mechanisms (Art. 14). For a voice AI system like Agent Studio handling live enterprise customer conversations, those two articles are the most critical.

The scanner runs entirely locally. Zero data leaves your machine:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I also built HMAC-SHA256 tamper-evident audit chains and drop-in trust layers for 6 frameworks that add compliance hooks with a single import. If PolyAI uses LangChain, OpenAI SDK, or similar under the hood, integration is one line.

Happy to do a 30-minute walkthrough of what the scanner finds on your codebase and what it means for your August deadline. At 343 people and a $750M valuation, getting ahead of this is a competitive signal to enterprise buyers.

Best,
Jason Shotwell
https://airblackbox.ai
