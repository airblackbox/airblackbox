# Email to BCG

**To**: steven.mills@bcg.com
**From**: jason@airblackbox.ai
**Subject**: Technical tool for EU AI Act code-level compliance

---

Hi Steve,

Clients get a compliance strategy from advisory. Then they ask: how do we actually verify the codebase meets Articles 9-15? That's the technical gap.

AIR Blackbox is an open-source code scanner that checks Python AI applications against EU AI Act Articles 9-15 — risk management, data governance, documentation, human oversight, security, accuracy. Runs on the client's machine, no data leaves their environment, scans in ~30 seconds. Apache 2.0, so your teams and clients can inspect the logic.

It's a technical pattern scanner, not a linter or legal tool. Think of it as the diagnostic scan that feeds into your compliance strategy conversations.

Live demo: https://airblackbox.ai/demo

```
pip install air-blackbox
air-blackbox scan /path/to/codebase
```

~1,700 installs/month on PyPI. Trust layers for LangChain, CrewAI, AutoGen, OpenAI, ADK, and Agno. Engagement license at $299.

August 2, 2026 deadline is creating urgency. Would a brief walkthrough be useful?

Best,
Jason Shotwell
AIR Blackbox
jason@airblackbox.ai
