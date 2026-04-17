# Email to Argilla

**To**: daniel@argilla.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Argilla (951 files scanned)

---

Hey Daniel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Argilla through the scanner and wanted to share what I found. As a data annotation platform now part of Hugging Face, Argilla is core infrastructure for teams building AI systems that will fall under the EU AI Act. The training data quality story maps directly to Article 10 (Data Governance), which makes compliance awareness especially relevant for your users.

**Summary**: 951 Python files scanned, 11/44 checks passing (25%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/7 passing |

On the positive side, Argilla has excellent type annotation coverage at 91% and solid input validation with Pydantic across 141 files. The biggest gap is in Article 14 (Human Oversight), where the scanner found no human-in-the-loop approval patterns, no action boundaries, and no agent-to-user identity binding. For a tool that helps teams curate training data for high-risk AI systems, those oversight patterns could become a selling point.

**To be clear**: this doesn't mean Argilla is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Given the August 2026 enforcement deadline, I'd love to hear how your team thinks about compliance tooling for the Argilla ecosystem. Happy to walk through the scan results in more detail.

Best,
Jason Shotwell
https://airblackbox.ai
