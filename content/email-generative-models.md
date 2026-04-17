# Email to Stability AI (generative-models)

**To**: christian@stability.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for generative-models (73 files scanned)

---

Hey Christian,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Stability AI's generative-models repo through the scanner and wanted to share what I found. With 27K+ GitHub stars and Stable Diffusion powering a massive ecosystem of image generation applications, the models and code patterns in this repo cascade through thousands of downstream deployments. When the EU AI Act enforcement deadline hits on August 2, 2026, downstream users building on these models will need compliance evidence.

**Summary**: 73 Python files scanned, 7/48 checks passing (15%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/8 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/8 passing |

Article 12 (Record-Keeping) is the strongest area with logging in 6 files, tracing in 6 files, and retention patterns in place. The LLM call error handling also passed since the repo uses direct model inference rather than API calls.

The biggest gap is Article 14 (Human Oversight) at 0/9. No kill switch, no human-in-the-loop patterns, no execution bounding, no action boundaries. For generative models that produce images, Article 14 oversight mechanisms are exactly what regulators will look for. Article 11 (Documentation) is also low at 1/5 with only 11% docstring coverage and 34% type hints.

**To be clear**: this doesn't mean generative-models is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given Stability AI's position as one of the most visible generative AI companies, demonstrating compliance patterns in the open-source codebase would set a strong precedent for the ecosystem. Happy to discuss the findings in more detail.

Best,
Jason Shotwell
https://airblackbox.ai
