# Email to PwC

**To**: hendrik.reese@pwc.com
**From**: jason@airblackbox.ai
**Subject**: Code-level compliance scanning for EU AI Act engagements

---

Hi Hendrik,

Governance frameworks tell clients what to do. The hard part is verifying the actual codebases meet Articles 9-15. That's where most advisory engagements hit a technical gap.

AIR Blackbox is an open-source Python code scanner that checks AI applications against EU AI Act Articles 9-15 (risk management, data governance, documentation, human oversight, security, accuracy). Runs entirely on client machines — zero data exposure — and completes in ~30 seconds. Apache 2.0, so your team can inspect and modify it.

It's a technical pattern scanner, not a linter or legal tool. Your consultants get code-level findings to feed into compliance assessments without building custom scanning infrastructure.

Live demo: https://airblackbox.ai/demo

```
pip install air-blackbox
air-blackbox scan /path/to/codebase
```

~1,700 monthly PyPI installs. Trust layers for LangChain, CrewAI, AutoGen, OpenAI, ADK, and Agno. Engagement license at $299.

August 2, 2026 is driving real demand. Could this be useful as a standardized assessment tool for your practice? Happy to walk through it.

Best,
Jason Shotwell
AIR Blackbox
jason@airblackbox.ai
