# Monday March 30, 2026 — AIR Blackbox Outreach Action Plan

---

## Morning: Send 3 New Outreach Emails

All three emails are drafted and ready to copy-paste. Scan results are real.

### Email 1: LlamaIndex
- **To**: jerry@llamaindex.ai (Jerry Liu, CEO/Founder)
- **Score**: 41% (21/51 checks) — 4,154 Python files scanned
- **Hook**: Record-keeping gap despite strong tracing infra; enterprise customers (KPMG, Salesforce, Rakuten) will need compliance
- **Trust layer angle**: `air_blackbox.attach("langchain")`
- **File**: [email-llamaindex.md](content/email-llamaindex.md)

### Email 2: CrewAI
- **To**: joao@crewai.com (João Moura, CEO/Founder)
- **Score**: 37% (19/51 checks) — 1,051 Python files scanned
- **Hook**: Best human oversight of any framework scanned (6/9), but data governance at 1/5; 40-60% Fortune 500 adoption means compliance pressure
- **Trust layer angle**: `air_blackbox.attach("crewai")` — dedicated trust layer
- **File**: [email-crewai.md](content/email-crewai.md)

### Email 3: Jina AI
- **To**: han.xiao@jina.ai (Han Xiao, Founder, now VP AI at Elastic)
- **Score**: 18% (9/50 checks) — 643 Python files scanned
- **Hook**: 0/9 on human oversight, Berlin-based (directly subject to EU AI Act), just acquired by Elastic (Fortune 500 customers)
- **Trust layer angle**: `air_blackbox.attach("openai")`
- **File**: [email-jina.md](content/email-jina.md)

---

## Tuesday 8-10am EST: Content Launch (Already Drafted)

Execute the Tuesday launch checklist:
1. **8:00am** — Publish Dev.to article → [devto-scan-results-article.md](content/devto-scan-results-article.md)
2. **8:15am** — Submit to Hacker News → [hn-show-post.md](content/hn-show-post.md)
3. **8:30am** — Post Twitter thread (4 tweets)
4. **9:00am** — Post LinkedIn
5. Monitor HN comments for 3 hours

Full checklist: [tuesday-launch-checklist.md](content/tuesday-launch-checklist.md)

---

## Full Pipeline Scoreboard (8 Targets)

| # | Project | Stars | Score | Contact | Email | Status |
|---|---------|-------|-------|---------|-------|--------|
| 1 | LiteLLM | 23K+ | 48% | Krrish Dholakia (CEO) | krrish@berri.ai | Sent |
| 2 | Superlinked | 15K+ | 2.5% | Daniel Svonava (CEO) | daniel@superlinked.com | Sent |
| 3 | Browser Use | 79K+ | 9.4% | Gregor Zunic (Co-Founder) | gregor@browser-use.com | Sent |
| 4 | RAGFlow | 76K+ | 7.9% | Yingfeng Zhang (CEO) | yingfeng.zhang@infiniflow.org | Sent |
| 5 | MetaGPT | 35K+ | 5.9% | Alexander Wu (CEO) | alexanderwu@deepwisdom.ai | Sent |
| 6 | LlamaIndex | 48K+ | 41% | Jerry Liu (CEO) | jerry@llamaindex.ai | **Ready to Send** |
| 7 | CrewAI | 44K+ | 37% | João Moura (CEO) | joao@crewai.com | **Ready to Send** |
| 8 | Jina AI | 21.9K+ | 18% | Han Xiao (Founder) | han.xiao@jina.ai | **Ready to Send** |

**Combined reach**: 342K+ GitHub stars across 8 projects

---

## Follow-Up Queue (5+ Days Since First Email)

Check for responses from the first 5 targets. If no response, draft follow-up emails:

| Project | Sent Date | Follow-up Due |
|---------|-----------|---------------|
| LiteLLM | ~March 26 | March 31+ |
| Superlinked | ~March 27 | April 1+ |
| Browser Use | ~March 28 | April 2+ |
| RAGFlow | ~March 28 | April 2+ |
| MetaGPT | ~March 29 | April 3+ |

---

## Next Batch: Prioritized Target List (Week 2)

### Tier 1: EU-Based Python AI (Directly Subject to EU AI Act)
| Company | City | Country | Why Target |
|---------|------|---------|------------|
| Giskard | Paris | France | AI testing/compliance-adjacent, €3M EU AI Act grant, AXA/BNP customers |
| Evidently AI | London | UK | ML monitoring, open source Python, enterprise customers |
| Weaviate | Amsterdam | Netherlands | Vector DB, Python client, enterprise adoption |
| Neptune.ai | Warsaw | Poland | MLOps platform, Python, enterprise customers |
| Qdrant | Berlin | Germany | Vector DB (core is Rust, scan Python client only) |
| Kern AI | Berlin | Germany | Data-centric AI, Python |
| Resistant AI | Prague | Czech Rep | AI fraud detection, directly regulated |
| Seldon | London | UK | ML serving, Python, enterprise |
| Humanloop | London | UK | LLM ops, Python |
| Lakera | Zurich | Switzerland | AI security (potential partner, not just target) |

### Tier 2: US-Based High-Star Python AI
| Company | Stars (est.) | Why Target |
|---------|-------------|------------|
| LangChain | 100K+ | Biggest framework, trust layer exists |
| BentoML | 7K+ | ML serving, pure Python |
| Letta (MemGPT) | 15K+ | Agent framework, Python |
| Composio | 15K+ | AI agent tools, Python |
| AgentOps | 3K+ | Agent observability, Python |
| Portkey | 7K+ | AI gateway, Python |
| Cleanlab | 10K+ | Data quality, Python |
| Unstructured | 10K+ | Document processing, Python |
| MindsDB | 25K+ | AI-SQL, Python |
| Lightning AI | 28K+ | PyTorch Lightning, Python |

### Off-Limits
- **Haystack (deepset)** — Jason's collaborators, do not contact

---

## GitHub Actions Scan Workflow

For repos too large to clone locally, fork into the `airblackbox` GitHub org and run this workflow:

```bash
# Fork the repo
gh repo fork run-llama/llama_index --org airblackbox --clone=false
gh repo fork crewaiinc/crewai --org airblackbox --clone=false
gh repo fork jina-ai/jina --org airblackbox --clone=false
```

Then add the compliance scan GitHub Action from the sales agent skill.
