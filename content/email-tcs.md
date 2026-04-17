# Email to TCS

**To**: sandeep.saxena@tcs.com
**From**: jason@airblackbox.ai
**Subject**: Code-level scanning for EU AI Act compliance engagements

---

Hi Sandeep,

EU AI Act enforcement hits August 2, 2026. Your clients are going to ask how to verify their Python codebases actually comply with Articles 9-15. Most advisory teams don't have a standardized tool for that yet.

AIR Blackbox is an open-source code scanner that checks AI applications against Articles 9-15 (risk management, data governance, documentation, human oversight, security, accuracy). It runs locally — no data leaves the client's machine — and completes in ~30 seconds. Apache 2.0 licensed, so your teams and clients can audit the scan logic.

It's not a linter and not legal compliance. It's a technical pattern scanner that gives your consultants code-level evidence to work with during assessments.

Live demo: https://airblackbox.ai/demo

```
pip install air-blackbox
air-blackbox scan /path/to/codebase
```

~1,700 installs/month on PyPI. Trust layers for LangChain, CrewAI, AutoGen, OpenAI, ADK, and Agno. Engagement license at $299 scales across your client portfolio.

Happy to do a 20-minute walkthrough with your team. Open to a call?

Best,
Jason Shotwell
AIR Blackbox
jason@airblackbox.ai
