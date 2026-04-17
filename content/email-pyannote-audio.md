# Email to pyannote.audio (pyannoteAI)

**To**: herve@pyannote.ai
**CC**: vincent@pyannote.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for pyannote.audio (102 files scanned)

---

Hey Hervé,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran pyannote.audio through the scanner and wanted to share what I found. Speaker diarization is core infrastructure for voice AI, meeting intelligence, and call-center analytics, which means pyannoteAI's customers are almost certainly processing biometric voice data that sits squarely inside the EU AI Act's high-risk and GDPR special-category zones. With pyannoteAI's $9M round and an EU-based founding team, the August 2026 enforcement deadline lands on you directly.

**Summary**: 102 Python files scanned, 14/44 checks passing (32%) across Articles 9-15.

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 4/6 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/10 passing |

The good news: Article 11 is strong, your docstrings and type hints carry real signal. The biggest gap is Article 14 (Human Oversight) at 0/9 passing, where the scanner didn't detect rate limiting, approval workflows, or agent action boundaries. For a library that processes voice biometric data at scale, this is the area regulators and enterprise buyers will probe first. Article 15 also flags missing RNG seed determinism and cuDNN deterministic flags, which matter because voice diarization outputs need to be reproducible for audit and dispute resolution.

**To be clear**: this doesn't mean pyannote.audio is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

There's also something that might be interesting on the pyannoteAI commercial side: I built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains. For a diarization API handling regulated voice data, signed records of each inference would be a differentiator for enterprise and public-sector buyers facing August 2026.

Happy to share more if useful.

Best,
Jason Shotwell
https://airblackbox.ai
