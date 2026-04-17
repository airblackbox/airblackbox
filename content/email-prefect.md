# Email to Prefect

**To**: jeremiah@prefect.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Prefect (1,762 files scanned)

---

Hey Jeremiah,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Prefect through the scanner and wanted to share what I found. With 18K+ stars and enterprise customers like Progressive Insurance and Cash App running 200M+ data tasks monthly, Prefect is infrastructure that regulated teams depend on. As the EU AI Act enforcement deadline hits in August, those enterprise customers will start asking about compliance.

**Summary**: 1,762 Python files scanned, 18/45 checks passing (40%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 6/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/7 passing |

Prefect scored the highest of any project I've scanned this week, and one of the strongest overall. Article 14 (Human Oversight) is especially impressive: the scanner found human-in-the-loop patterns, rate limiting, agent identity binding, token expiry, and action boundaries. That's rare. Article 15 is also solid with retry/backoff in 173 files, injection defense patterns, and output validation in 41 files.

The main opportunity is Article 10 (Data Governance). With 426 files using Pydantic validation, the input side is covered, but there's no data governance documentation or PII handling patterns. For a platform that orchestrates data workflows, making that explicit would round out an already strong compliance story.

**To be clear**: this doesn't mean Prefect is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Prefect is positioning as AI infrastructure with MCP server support, building compliance visibility into the platform could be a powerful differentiator for enterprise sales. Happy to chat about how other orchestration frameworks are approaching this.

Best,
Jason Shotwell
https://airblackbox.ai
