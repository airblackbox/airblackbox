# Hacker News Show HN Post

**Post Tuesday, 8-10am EST**

---

## Title

Show HN: I scanned 5 popular Python AI projects for EU AI Act compliance (avg: 17%)

## URL

Link to the Dev.to article (publish Dev.to first, then submit to HN)

## First Comment (post immediately after submitting)

Hey HN, I built AIR Blackbox, an open-source CLI that scans Python AI codebases for EU AI Act technical requirements. It checks for patterns mapped to Articles 9-15 (risk management, data governance, docs, logging, human oversight, security).

I pointed it at Browser Use (79K stars), RAGFlow (76K stars), LiteLLM (23K stars), and Superlinked (15K stars). Results:

- Browser Use: 9.4%
- RAGFlow: 7.9%
- LiteLLM: 48%
- Superlinked: 2.5%
- AIR Blackbox (self-scan): 91%

The weakest area across all projects is Article 12 (record-keeping). Most Python AI projects have basic logging but not structured audit trails. Article 11 (documentation) is consistently the strongest because good Python projects already have docstrings and type hints.

To be clear about what this is and isn't: it's a linter, not a legal compliance tool. It checks whether specific technical patterns exist in your code. It can't tell you "you're compliant." That's a lawyer's job.

Try it:

    pip install air-blackbox
    air-blackbox comply --scan . --no-llm --format table --verbose

Everything runs locally. No API keys, no cloud calls. Apache 2.0.

GitHub: https://github.com/air-blackbox/gateway

Happy to answer questions about the architecture, what patterns it checks for, or how the trust layers work.
