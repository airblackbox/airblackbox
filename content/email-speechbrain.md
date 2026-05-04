# Email to SpeechBrain

**To**: mirco.ravanelli@concordia.ca
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for SpeechBrain (727 files scanned)

---

Hey Mirco,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran SpeechBrain through the scanner and wanted to share what I found. The toolkit has become a default building block for European speech systems (ASR, speaker recognition, voice biometrics) used by labs and companies across Italy, France, the Netherlands, Germany, and the UK, and the maintainer base in Bologna, Trento, FBK, Avignon, INRIA, and Telecom Paris means SpeechBrain is right in the EU AI Act's line of sight when biometric identification (Annex III) and emotion-recognition obligations come online.

**Summary**: 727 Python files scanned, 19/58 checks passing (33%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 5/11 passing |

33% is one of the highest scan scores I've seen on a research-grade speech toolkit, and Article 15 (5/11) reflects the discipline already in the codebase: RNG seeding, deterministic flags, output validation, retry/backoff, and a passing prompt-injection-defense pattern all came back clean. Article 12 (4/9) caught the logging in 326/727 files plus a tracing/observability pattern in 137 files, which is rare upstream of the embedding stack. The two gaps that stand out for EU deployers are Article 11 - type annotations (379/4,344 public functions) and the missing model card - and Article 14, which is at 0/9: speaker recognition and emotion recognition both end up needing operator-facing documentation, low-confidence thresholds, and human-review hooks under Annex III, and none of those patterns are visible in the source today.

**To be clear**: this doesn't mean SpeechBrain is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how many EU research labs and downstream products inherit straight from `speechbrain`, even small upstream changes (a `MODEL_CARD.md` for flagship recipes, a documented `confidence_threshold` parameter on the speaker / emotion modules, type hints on the public Brain/Stage entry points) would let every EU deployer collect Article 11 and Article 14 evidence by reference rather than reimplementing it. Happy to share the full per-check report or open a draft issue at speechbrain/speechbrain if you'd like to triage with the wider maintainer team.

Best,
Jason Shotwell
https://airblackbox.ai
