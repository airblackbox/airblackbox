# Email to Adapter-Hub (adapters)

**To**: calpt@mail.de
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for adapters (259 files scanned)

---

Hey Clifton,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the adapter-hub/adapters repo through the scanner and wanted to share what I found. The library has become one of the standard ways enterprise NLP teams in Europe layer parameter-efficient fine-tuning on top of Hugging Face Transformers, which puts adapters in an interesting position: when a regulated downstream user runs a compliance scan on their fine-tuned model, the defaults inherited from this library quietly shape that team's posture. With August 2, 2026 EU AI Act enforcement now three months out, those inheritance paths matter.

**Summary**: 259 Python files scanned, 12/58 checks passing (21%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/11 passing |

The good news first: Article 12 (Record-Keeping) at 5/9 is the strongest section, which makes sense given how much of the library is about tracking and composing adapter state. Adapter loading, unloading, and merging are surfaced through clean state transitions, and the existing logging hooks mean a downstream user can plug in a structured logger without re-architecting.

The loudest signal in the scan is Article 14 at 0/9. Human Oversight isn't usually what a research-rooted library optimizes for, but it's the article EU AI Act audits start with for high-risk systems, and adapter composition is exactly the kind of capability that compliance teams will eventually want gated behind approval workflows or signed config. A small additions list, a documented "approval token" pattern in the AdapterSetup context manager, an opt-in audit log of which adapters were loaded for a given inference call, and a rate-limiter recipe in the docs, would move Article 14 to 3 or 4 of 9 without altering the library's research surface. Same story on Article 15: torch determinism flags, RNG seeding patterns, and adversarial-testing references are the cheapest wins there.

**To be clear**: this doesn't mean adapters is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

The bigger pattern I'm seeing across UKP-adjacent and HuggingFace-adjacent libraries is that the defaults in research-rooted code propagate into a lot of enterprise stacks, and once August 2 lands, those inherited defaults become the first thing pulled into a compliance audit. Happy to share the per-file output, or talk through which Article 14 patterns would be the lowest-friction additions for the maintainer team.

Best,
Jason Shotwell
https://airblackbox.ai
