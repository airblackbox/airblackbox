# Email to Phospho

**To**: pierre-louis@phospho.app
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Phospho (233 files scanned)

---

Hey Pierre-Louis,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Phospho platform through the scanner and wanted to share what I found. Paris-based, YC-backed, and sitting at the junction of LLM observability and now agentic robotics. Both of those are exactly the product categories the EU AI Act is going to scrutinize first once enforcement starts on August 2, 2026. Robotics in particular lands squarely under high-risk system requirements.

**Summary**: 233 Python files scanned, 19/58 checks passing (33%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 3/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 5/11 passing |

A few things land well. Art. 12 (Record-Keeping) at 5/9 is among the better scores I've seen on LLM observability platforms, which makes sense given the product. Art. 15 at 5/11 is also solid, with clean retry/backoff patterns and input validation showing up in the static analysis.

The gap I'd flag is Art. 12's "agent identity binding" check. The scanner detected autonomous agent patterns in 11 files (backend/phospho_backend/main.py and several others) but no stable cryptographic identity bound to the agent actions. For phosphobot and the robotics path, being able to prove which agent executed which action, tamper-evident, is effectively Article 12 plus Article 14 combined. That is the exact thing enterprise procurement will ask about when they see the word "robot."

**To be clear**: this doesn't mean Phospho is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

If useful, I can send the full per-file breakdown. The agent-identity angle feels like the most Phospho-shaped gap, and it's also the one that compounds most as you move deeper into the physical-agent space.

Best,
Jason Shotwell
https://airblackbox.ai
