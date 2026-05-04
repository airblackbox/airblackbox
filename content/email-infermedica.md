# Email to Infermedica

**To**: piotr.orzechowski@infermedica.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Infermedica python-api (52 files scanned)

---

Hey Piotr,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the infermedica/python-api repo through the scanner and wanted to share what I found. Symptom checking and patient triage is one of the cleanest examples of an Annex III high-risk use case under the EU AI Act: AI that influences access to essential healthcare services. Infermedica's customers (insurers, health systems, telehealth platforms) will be on the hook for conformity-assessment evidence by August 2, 2026, and the Python SDK is the artifact every one of them embeds. Whatever compliance posture the SDK ships with becomes the floor for the customer's own technical documentation.

**Summary**: 52 Python files scanned, 13/57 checks passing (23%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/10 passing |

The good news first: Article 11 at 3/5 reflects a docstring-heavy, type-hinted SDK that is clearly written for integrators rather than just internal use. Article 15 at 3/10 picks up structured response handling and HTTP error patterns in the API client that already give downstream apps a reasonable robustness baseline.

The biggest lever for a triage SDK is Article 14. Right now the scanner flags 0/9 on Human Oversight: no approval workflows, no rate limiting on the client side, no explicit human-in-the-loop hooks around the diagnostic recommendation surface. Article 14 is exactly the article healthcare AI gets graded on hardest, because the entire policy intent is that a clinician (not the model) decides next-step care. A small, well-scoped SDK pattern, for example a `confidence_threshold` parameter that forces a "refer to clinician" path for low-confidence recommendations, plus a documented escalation hook integrators can wire into their EHR, would move that 0/9 toward 4-5/9 and give your customers' compliance teams a concrete artifact to point to in their own Article 11 technical documentation.

**To be clear**: this doesn't mean Infermedica is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that every Infermedica customer is going to need to produce technical documentation (Article 11) and conformity-assessment evidence (Article 17) for their deployed triage system, a publicly visible Article 14 posture on the SDK itself becomes a real selling point in your enterprise pipeline. Happy to share the full scan output or walk through which checks are easy wins on the SDK side versus things that belong in customer-facing docs.

Best,
Jason Shotwell
https://airblackbox.ai
