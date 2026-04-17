# Email to DSPy (Stanford)

**To**: okhattab@mit.edu
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for DSPy (239 files scanned)

---

Hey Omar,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran DSPy through the scanner and wanted to share what I found. DSPy is quickly becoming the default way production teams compose and optimize LLM pipelines, and a lot of those teams have EU footprints. The AI Act enforcement window in August 2026 is going to make "show me the compliance surface of your prompt pipeline" a real question, and DSPy sits right in the middle of that conversation.

**Summary**: 239 Python files scanned, 11/45 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/8 passing |

Documentation and type-hint coverage are the relative strengths, which tracks with how carefully Signatures are specified in the codebase. The biggest gaps are Article 14 (Human Oversight) and Article 12 (Record-Keeping): the scanner did not find explicit approval workflows, token-scope validation, or structured audit trails for compile/optimization runs. Given that DSPy programs are iteratively optimized against training data, the provenance of those optimization traces is exactly the kind of thing an EU auditor will want to inspect.

**To be clear**: this doesn't mean DSPy is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

If any of this is useful, I'd be happy to share the full per-file report or to contribute a small docs section on compile-time audit logging for DSPy programs. No ask beyond that — just wanted to put the data in front of you before downstream teams start asking the same questions.

Best,
Jason Shotwell
https://airblackbox.ai
