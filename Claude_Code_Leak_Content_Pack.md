# Claude Code Leak — Content Distribution Pack

> Context: On March 31, 2026, Anthropic accidentally shipped a 59.8MB source map file in their npm package, exposing ~512,000 lines of Claude Code's internal TypeScript. The leak revealed MCP server orchestration logic. Separately, CVE-2025-59536 showed that malicious .mcp.json files in repos can execute arbitrary commands and exfiltrate API keys before users even see a trust prompt. Between 00:21 and 03:29 UTC on March 31, a malicious axios dependency with a RAT was also pulled in.

---

## 1. DEV.TO ARTICLE

**Title:** The Claude Code Leak Proved What We've Been Building For

**Tags:** #ai #security #python #opensource

---

Today Anthropic accidentally shipped 512,000 lines of Claude Code's source code to npm. A source map file that should have been stripped from the build made it into version 2.1.88 of the @anthropic-ai/claude-code package. Within hours, the entire codebase was mirrored on GitHub and dissected by thousands of developers.

The leak itself was a packaging error. Human mistake. It happens.

But what the leak *revealed* is the part that matters.

### The Real Problem Isn't the Leak

Check Point Research had already disclosed CVE-2025-59536 back in October — a vulnerability where malicious `.mcp.json` files in a repository could execute arbitrary shell commands the moment you open Claude Code. No trust prompt. No confirmation dialog. The MCP server initializes, runs whatever commands are in the config, and your API keys are gone before you've read a single line of code.

The leaked source code made this worse. Now attackers have the exact orchestration logic for Hooks and MCP servers. They can see precisely how trust prompts are triggered, when they're skipped, and where the gaps are. That's a blueprint for exploitation.

And between 00:21 and 03:29 UTC on March 31, anyone who installed Claude Code pulled in a compromised version of axios containing a Remote Access Trojan. A supply chain attack riding the same wave.

Three problems, one root cause: **AI agents execute before humans verify.**

### This Is an Architecture Problem

Every one of these vulnerabilities follows the same pattern:

1. An AI agent receives instructions (from a config file, a prompt, a dependency)
2. It executes those instructions
3. The human finds out afterward — if they find out at all

This isn't unique to Claude Code. It's the fundamental architecture of every AI agent framework shipping today. LangChain agents, CrewAI crews, AutoGen groups, OpenAI Agents — they all execute first and ask questions never.

The missing piece isn't better prompts or more careful packaging. It's an infrastructure layer that sits between intent and execution and enforces verification before action.

### What Trust Infrastructure Actually Looks Like

This is what I've been building with AIR Blackbox. The trust layers intercept every AI call at the execution level — not after the fact, not in a dashboard, at the moment of the call.

Here's what that looks like in practice with the OpenAI SDK:

```python
from air_openai_trust import attach_trust

client = attach_trust(OpenAI())
# Every call through this client now gets:
# - HMAC-SHA256 tamper-evident audit record
# - PII detection (catches API keys being exfiltrated)
# - Prompt injection scanning
# - Human delegation flags for sensitive operations
```

One import. The client works exactly the same way. But now every call is logged with a cryptographic audit trail, credentials are flagged before they leave your environment, and injection attempts are caught at the point of execution.

Applied to the Claude Code vulnerabilities:

**Malicious MCP config tries to exfiltrate API keys?** The PII detection layer catches credentials in outbound payloads before they're transmitted.

**Poisoned dependency runs arbitrary commands?** The audit chain logs every action with HMAC-SHA256 signatures. You can't tamper with the record after the fact. Forensic teams can reconstruct exactly what happened.

**Prompt injection hidden in a repo's config?** The injection scanner catches 20 known attack patterns across 5 categories before they reach the model.

**Agent executes without human approval?** The human delegation system flags sensitive operations and requires explicit sign-off.

### This Isn't About Compliance Anymore

I started building AIR Blackbox for EU AI Act compliance. That's still the wedge — the regulation creates urgency. But today's leak shows the real category:

**Trust infrastructure for AI operations.**

Compliance is one use case. The bigger picture is that every AI agent deployment needs an interception layer that verifies, filters, stabilizes, and protects every call. Not a dashboard that shows you what went wrong yesterday. An active layer that prevents it from going wrong right now.

### The Uncomfortable Truth

Anthropic is one of the most safety-focused AI companies on the planet. They employ some of the best security engineers in the industry. And a packaging error exposed their entire codebase, a malicious dependency slipped into their supply chain, and a months-old vulnerability in their MCP architecture had already shown that trust prompts could be bypassed entirely.

If it happened to Anthropic, it will happen to every company deploying AI agents.

The question isn't whether your AI systems will face these problems. It's whether you'll have the infrastructure in place to catch them when they do.

```
pip install air-compliance && air-compliance scan .
```

11 PyPI packages. Runs locally. Your code never leaves your machine. Apache 2.0.

**GitHub:** [github.com/airblackbox](https://github.com/airblackbox)
**Site:** [airblackbox.ai](https://airblackbox.ai)
**Audit Chain Spec:** [airblackbox.ai/spec](https://airblackbox.ai/spec)

---

## 2. LINKEDIN POST

The Claude Code source code leaked today.

A source map file that should have been stripped from the build shipped to npm. 512,000 lines of TypeScript. The entire codebase mirrored on GitHub within hours.

Anthropic says it was human error. I believe them. But the leak isn't the story.

The story is what was already known. Check Point Research disclosed CVE-2025-59536 months ago: malicious MCP server configs in a repository could execute arbitrary commands before users see a trust prompt. The leaked source code gave attackers the exact orchestration logic to exploit it further.

Same morning, anyone who installed Claude Code between 00:21 and 03:29 UTC pulled in a compromised axios dependency containing a Remote Access Trojan.

Three problems. One pattern: AI agents execute before humans verify.

This is the architecture problem I've been building against with AIR Blackbox. Our trust layers sit inside every AI call — intercepting at the execution level, not auditing after the fact.

PII detection catches credentials before they leave your environment. HMAC-SHA256 audit chains create tamper-evident records of every action. Injection scanning catches poisoned configs before they reach the model. Human delegation enforcement requires approval before sensitive operations execute.

If the most safety-focused AI company in the world can ship a source code leak, a supply chain compromise, and an MCP bypass vulnerability in the same news cycle, every team deploying AI agents needs trust infrastructure.

This isn't a compliance problem. It's an architecture problem. And compliance is just the first use case.

11 open-source PyPI packages. Runs locally. Apache 2.0.

Link in comments.

#AIGovernance #AISecurity #EUAIAct #OpenSource #TrustInfrastructure

---

## 3. TWITTER/X THREAD

**Tweet 1:**
Claude Code's entire source code leaked today via an npm source map.

512,000 lines of TypeScript. Mirrored on GitHub in hours.

But the leak isn't the scary part. What it revealed is. 🧵

**Tweet 2:**
CVE-2025-59536 (disclosed months ago): malicious .mcp.json files in a repo can execute arbitrary commands BEFORE you see a trust prompt.

The leaked source code? It's a blueprint showing attackers exactly how trust prompts work and where they're skipped.

**Tweet 3:**
Same morning, a compromised axios dependency with a RAT slipped into the npm install window.

Three attack vectors. One root cause:

AI agents execute before humans verify.

**Tweet 4:**
This is the architecture problem I've been building against.

AIR Blackbox trust layers sit inside every AI call:
→ Catch credentials before they're exfiltrated
→ HMAC-SHA256 audit chains that can't be tampered with
→ Injection scanning at the point of execution
→ Human delegation enforcement

**Tweet 5:**
If Anthropic — arguably the most safety-focused AI company — ships a source code leak, a supply chain compromise, and an MCP bypass in the same news cycle...

Every team deploying AI agents needs trust infrastructure. Not a dashboard. An interception layer.

github.com/airblackbox
airblackbox.ai

---

## 4. REDDIT r/ClaudeAI POST

**Title:** The MCP vulnerability CVE-2025-59536 + today's source code leak = why AI agents need an interception layer

**Body:**

The leak is getting a lot of attention today (rightfully so), but I want to talk about the vulnerability it made worse.

CVE-2025-59536 showed that a malicious `.mcp.json` config in a repo could execute arbitrary commands when you open Claude Code — before the trust prompt appears. Check Point Research disclosed this months ago. Anthropic patched it.

But today's source map leak exposed the exact orchestration logic for Hooks and MCP servers. That's the internal code that determines when trust prompts fire, when they're bypassed, and how MCP servers initialize. For anyone building exploits against Claude Code, this is the playbook.

Combined with the compromised axios dependency that shipped in the same window, it paints a picture of a fundamental architecture problem: AI agents execute instructions before humans verify them.

I've been building an open-source project called AIR Blackbox that addresses this at the architecture level. Instead of patching individual vulnerabilities, it adds a trust layer that intercepts every AI call:

- **PII/credential detection** — catches API keys and tokens in outbound payloads before they're transmitted
- **HMAC-SHA256 audit chains** — tamper-evident logs of every action. If something slips through, forensic teams can reconstruct what happened and prove the record hasn't been modified
- **Prompt injection scanning** — catches malicious instructions (like those hidden in .mcp.json configs) before they reach the model
- **Human delegation enforcement** — flags sensitive operations that need human sign-off

It works as drop-in trust layers for existing frameworks. One import wraps your existing client:

```python
from air_openai_trust import attach_trust
client = attach_trust(OpenAI())
```

Everything works the same, but now every call is verified, logged, and protected.

11 PyPI packages, all open source (Apache 2.0), runs entirely locally.

Not posting this to self-promote — posting because today's leak is a concrete example of the problem this is designed to solve. Happy to answer any technical questions about the architecture.

GitHub: https://github.com/airblackbox
Site: https://airblackbox.ai

---

## 5. HACKER NEWS COMMENT (for existing leak thread)

Don't submit a new post — comment on the existing thread (https://news.ycombinator.com/item?id=47584540)

**Comment:**

The source map leak is embarrassing but ultimately a packaging mistake. The more interesting thread is what it exposed about the MCP architecture.

CVE-2025-59536 already showed that .mcp.json configs could execute before trust prompts. Now the orchestration logic is public. Anyone building against Claude Code's MCP system has the source to find the next bypass.

This is the same pattern across every agent framework: agents execute instructions before humans verify them. The Claude Code Hooks system, LangChain tool calls, CrewAI task execution — they all share this architecture.

I've been working on interception layers that sit inside the call itself (HMAC-SHA256 audit chains, PII detection on outbound payloads, injection scanning at point of execution). The idea is that trust verification happens at the execution layer, not in a UI prompt that can be bypassed or a dashboard that shows you what went wrong yesterday.

Open source, runs locally: https://github.com/airblackbox

Would be interested to hear how others are approaching this. The post-hoc audit approach (Langfuse, Helicone) gives you observability but not prevention. The firewall approach (Arthur, Lasso) filters threats but doesn't give you cryptographic traceability. There's a gap.
