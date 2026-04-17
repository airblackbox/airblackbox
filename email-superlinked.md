# Email to Superlinked Team

**To**: daniel@superlinked.com
**From**: jason.j.shotwell@gmail.com
**Subject**: EU AI Act compliance scan results for Superlinked

---

Hey Daniel,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Superlinked's Python framework through the scanner and wanted to share what I found. Since Superlinked handles search and recommendations for enterprise customers, the EU AI Act technical requirements are going to be directly relevant to your users as the August 2026 deadline approaches.

**Summary**: 500 Python files scanned, 2.5% aggregate compliance score (75/3000 checks).

Per-article breakdown:

| EU AI Act Article | What It Checks | Files Passing |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0.0% (0/500) |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 3.2% (16/500) |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 8.8% (44/500) |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 0.0% (0/500) |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0.0% (0/500) |
| Art. 15 (Security) | Injection defense, output validation | 3.0% (15/500) |

The biggest gaps are in record-keeping (Art. 12), risk management (Art. 9), and human oversight (Art. 14), all at 0%. For a framework powering enterprise search and recommendation systems, the lack of audit trails and oversight hooks could become a blocker for your customers who need to demonstrate EU AI Act compliance.

**To be clear**: this doesn't mean Superlinked is non-compliant. The scanner checks for technical patterns that map to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the technical gaps are so teams can prioritize fixes.

The scanner is open source (Apache 2.0): https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built drop-in trust layers for OpenAI SDK (which Superlinked integrates with) that add HMAC-SHA256 tamper-evident audit chains, input validation, and oversight hooks. Single import, no changes to application code:

```python
import air_blackbox
air_blackbox.attach("openai")
```

Happy to collaborate on getting Superlinked's compliance coverage up. Your enterprise customers are going to start asking about this, and having audit-ready infrastructure baked into the framework would be a real differentiator.

Best,
Jason Shotwell
https://airblackbox.ai
