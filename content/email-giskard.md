# Email to Giskard

**To**: alex@giskard.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Giskard (111 files scanned)

---

Hey Alex,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Giskard through the scanner and wanted to share what I found. As a Paris-based AI testing company backed by Bpifrance and the EIC Accelerator, you're directly subject to EU AI Act enforcement starting August 2, 2026. Your users are also going to start asking about compliance in the tools they depend on.

**Summary**: 111 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

The good news: your type annotation coverage is excellent at 99%, and your docstring coverage is solid at 69%. The biggest gap is in Article 12 (Record-Keeping), where the scanner didn't detect structured logging or audit trail patterns. For a tool that helps teams evaluate LLM systems, having a traceable record of evaluations run would strengthen both your compliance posture and your product story.

**To be clear**: this doesn't mean Giskard is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There's also something that might be interesting for the Giskard product itself: I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains to LLM calls. If Giskard evaluations could produce signed, tamper-evident records, that's a differentiator for your enterprise customers facing August 2026.

Happy to share more if you're curious.

Best,
Jason Shotwell
https://airblackbox.ai
