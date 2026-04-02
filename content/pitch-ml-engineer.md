# Pitch: The Machine Learning Engineer Newsletter

**To**: a@ethical.institute (Alejandro Saucedo)
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act compliance scanner for Python ML projects

---

Hey Alejandro,

I built an open-source EU AI Act compliance scanner called AIR Blackbox. It's Apache 2.0, pip-installable, and maps static code patterns to EU AI Act Articles 9 through 15 (risk management, data governance, documentation, record-keeping, human oversight, security).

Think of it as a linter for AI governance. It's not a legal compliance tool. It identifies technical gaps so teams know where to prioritize before the August 2026 enforcement deadline.

I've scanned 8 popular Python AI frameworks (342K+ combined GitHub stars). Average score: 24%. The consistent finding: almost no one has tamper-evident audit chains (Art. 12), and human oversight mechanisms (Art. 14) are missing entirely from several major frameworks.

The tool includes HMAC-SHA256 tamper-evident audit chains and drop-in trust layers for 6 frameworks. One import adds compliance hooks:

```python
import air_blackbox
air_blackbox.attach("langchain")  # or crewai, autogen, openai, adk, rag, agno
```

Everything runs locally. Zero data leaves the machine.

Given your newsletter covers production ML tooling, security, and ethical AI, I thought your audience might find this useful. Happy to provide scan data on any popular framework, or write a technical breakdown of the compliance gap patterns I've found across these projects.

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
