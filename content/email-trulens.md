# Email to TruLens (Snowflake)

**To**: josh.reini@snowflake.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for TruLens (461 files scanned)

---

Hey Josh,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran TruLens through the scanner and wanted to share what I found. TruLens sits on the evaluation path for a lot of teams shipping LLM and agent apps into production, and now that it's part of Snowflake, a meaningful chunk of those users are enterprises with EU operations. Under the August 2, 2026 EU AI Act enforcement deadline, those customers are going to start asking what parts of Articles 9 through 15 TruLens already helps them cover. A lot of the answers look strong.

**Summary**: 461 Python files scanned, 23/58 checks passing (40%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 6/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/11 passing |

The strong side: Art. 12 (6/9) is one of the best scores the scanner has produced on any evaluation library. Tracing, feedback runs, structured logging, and the Snowflake connector all give you a real audit trail surface. Art. 10 at 2/5 also picked up input validation and a schema layer, and Art. 15 had retry/backoff and output validation passing cleanly. The 40% static score puts TruLens in the top tier of the 80+ AI libraries the scanner has run against.

The gap that will matter most to your users is Art. 14 human oversight (2/9). The scanner didn't find explicit approval workflows, rate limits, or identity-binding patterns, and those are the checks that most enterprise AI platform teams at Snowflake customers are going to have to produce evidence for. Since TruLens is already the library producing the evaluation signal, a thin oversight layer (configurable threshold that routes low-score runs to a human review queue) would let downstream teams cite TruLens for both the eval and the oversight mechanism in one place. Same story on Art. 11: the docstring coverage is strong, but a short model card section on each built-in feedback function (purpose, known failure modes, eval limits) would let users inherit Article 11 documentation directly.

**To be clear**: this doesn't mean TruLens is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

TruLens is already the evaluation layer that most serious LLM teams reach for, and inside Snowflake it's about to be cited in a lot of EU customers' conformity assessments whether the team plans for it or not. A small pass on Art. 14 oversight patterns and per-feedback-function model cards would let those customers point to TruLens directly instead of bolting their own oversight layer on top. Happy to share the full scan output or open a PR against the docs if useful.

Best,
Jason Shotwell
https://airblackbox.ai
