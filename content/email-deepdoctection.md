# Email to deepdoctection

**To**: janis.meyer@deepdoctection.io
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for deepdoctection (256 files scanned)

---

Hey Janis,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran deepdoctection through the scanner and wanted to share what I found. Document AI for financial reports, contracts, and regulatory filings is exactly where the EU AI Act gets sharpest, since extracting figures from a 10-K or a Bundesanzeiger filing into a downstream decision system pulls Article 10 data governance and Article 12 logging directly into scope for whoever ships the pipeline.

**Summary**: 256 Python files scanned, 14/58 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

24% is well above where most Document AI repos land, and the Article 11 result reflects how seriously the codebase is documented (docstrings, type hints, mkdocs site all picked up). The gap I'd actually flag for your users is Article 10 data governance. Because deepdoctection is the bridge between raw scanned PDFs and structured downstream features, a small set of input-shape and PII-marker schemas at the pipeline boundary would let your enterprise users (insurance, banking, legal) point at concrete Article 10 evidence instead of arguing about it. Article 14 at 0/9 is also worth a look in the inference path, since financial document extraction is one of the use cases regulators specifically expect human-in-the-loop review for borderline outputs.

**To be clear**: this doesn't mean deepdoctection is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given the financial-services origin of the project and the fact that you've talked publicly about regulatory and reporting workflows, the Article 10 and Article 12 patterns are the ones I'd suggest looking at first. Happy to share the full per-check report and any of the suggested fixes if it's useful.

Best,
Jason Shotwell
https://airblackbox.ai
