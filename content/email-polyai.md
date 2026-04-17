# Email to PolyAI

**To**: nikola@poly.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PolyAI pheme (22 files scanned)

---

Hey Nikola,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the PolyAI pheme repo through the scanner and wanted to share what I found. Voice agents deployed into customer service, banking, healthcare, and hospitality (all listed on your site) run straight into high-risk and biometric categories under the EU AI Act. With PolyAI's London base, enterprise footprint in regulated industries, and August 2, 2026 enforcement deadline approaching, the governance questions from procurement teams are already starting to show up in RFPs.

**Summary**: 22 Python files scanned, 14/45 checks passing (31%) across Articles 9-15.

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/6 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 7/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

The good news: Article 12 (Record-Keeping) is the standout at 7/9 passing, which is a solid foundation for audit-trail work. The biggest gap is Article 9 (Risk Management) at 0/5, where the scanner didn't find a risk assessment document, a risk classification, or active mitigations. For a speech-generation model that could be misused for voice cloning or impersonation, adding a published risk classification and mitigations file in the repo is low-effort and directly supports the conversations your enterprise buyers will want to have on responsible voice AI.

**To be clear**: this doesn't mean PolyAI is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

One angle worth flagging: I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains to model calls. For PolyAI voice agents operating in banks and healthcare, signed records of each turn (which model, which prompt, which output) would be a strong answer to the compliance questions your enterprise customers are starting to ask about voice AI.

Happy to go deeper if useful.

Best,
Jason Shotwell
https://airblackbox.ai
