# Email to Speechmatics

**To**: katy.wigdahl@speechmatics.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for the Speechmatics Python SDK (91 files scanned)

---

Hey Katy,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the speechmatics-python-sdk repo through the scanner and wanted to share what I found. ASR and conversational voice agents sit in a particularly interesting spot under the EU AI Act because the audio stream itself is biometric data under GDPR Article 9, and any voice agent operating into the EU is in scope on August 2, 2026, even if the company is UK-headquartered. That makes the SDK that enterprise customers integrate with one of the natural attack surfaces an auditor will inspect.

**Summary**: 91 Python files scanned, 18/57 checks passing (32%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/10 passing |

The good news first: Article 11 (Documentation) at 3/5 and Article 12 (Record-Keeping) at 5/9 are above median for the libraries I've scanned in this pipeline. Public-API docstrings are clean, type hints are consistent, and the SDK already surfaces the structured logging hooks an enterprise integrator needs to wire into their own audit trail. That's a real head start on Article 11 evidence.

The two biggest gaps are Article 9 and Article 10, both at 1/5. For an ASR client SDK specifically, this matters because the call sites where audio streams are constructed and where partial transcripts are emitted are exactly the places EU AI Act auditors will look for input validation, PII redaction hooks, retention-policy plumbing, and consent metadata. The scanner currently flags no PII handling patterns, no schema-level input validation, no documented data minimization stance, and no fallback model configuration on transcription errors. Adding a small "voice data governance" section to the README that maps each public method to its Article 10 obligation, plus a redaction or PII filter hook in the result handler, would shift Article 10 from 1/5 to 3 or 4 of 5 without changing the API surface.

**To be clear**: this doesn't mean Speechmatics is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that Speechmatics already wins on accuracy benchmarks against the US incumbents, a public Article 10 and Article 12 posture on the SDK could be a real wedge with European banks, public-sector buyers, and call-center platforms that have to produce conformity evidence on every voice AI vendor in their stack. Happy to share the full scan output or walk through which checks are cheap SDK-side wins versus things that belong in the cloud-platform docs.

Best,
Jason Shotwell
https://airblackbox.ai
