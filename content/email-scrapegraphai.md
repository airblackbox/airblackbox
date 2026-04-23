# Email to ScrapeGraphAI

**To**: marco@scrapegraphai.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Scrapegraph-ai (258 files scanned)

---

Hey Marco,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Scrapegraph-ai through the scanner and wanted to share what I found. ScrapeGraphAI is one of the fastest-growing Italian open-source AI projects (17K+ GitHub stars), and the library is increasingly used inside EU enterprises to orchestrate LLM-driven scraping pipelines. That use case sits right in the crosshairs of the EU AI Act when enforcement begins August 2, 2026, because scraping agents combine web input, LLM inference, and structured data extraction in ways that trigger both the AI Act and GDPR.

**Summary**: 258 Python files scanned, 21/58 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 6/11 passing |

Honestly, 21/58 is one of the better opening scores I have seen from an EU-based agent framework in this batch. Articles 11, 12, and 15 are all pulling their weight, with good docstrings, strong logging patterns, and solid output validation. The weakest area is Article 10 (Data Governance) at 1/5. For a library whose whole job is pulling unstructured content off the web, PII handling and input validation are exactly where compliance reviewers will push hardest, particularly when EU customers use Scrapegraph-ai over pages containing personal data.

**To be clear**: this does not mean Scrapegraph-ai is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It is a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

ScrapeGraphAI is one of the highest-leverage agent frameworks coming out of Italy right now. Shipping an explicit EU AI Act compliance posture would help customers adopt faster, especially in regulated verticals. Happy to help you close the Article 10 gap if useful.

Best,
Jason Shotwell
https://airblackbox.ai
