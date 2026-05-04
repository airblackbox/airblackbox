# Email to Unbabel COMET

**To**: ricardo.rei@unbabel.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Unbabel COMET (51 files scanned)

---

Hey Ricardo,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the COMET repo through the scanner and wanted to share what I found. COMET has become the de facto MT evaluation framework. Every WMT submission, every translation model card, and a growing share of enterprise NMT evaluations cite COMET scores as evidence of model quality. That puts COMET inside the conformity-assessment loop for Annex III high-risk uses of translation systems (migration, asylum, border control, judicial), which makes the framework itself an interesting object of EU AI Act scrutiny: not because COMET is itself a high-risk system, but because COMET scores are increasingly the metric of record.

**Summary**: 51 Python files scanned, 8/57 checks passing (14%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/10 passing |

The good news first: Article 11 at 3/5 is one of the cleaner documentation profiles for a research framework of this scope, and the Article 12 logging surface (3/9) is reasonable for a CLI evaluation tool that runs as a single-shot job rather than a long-lived service.

The biggest lever is Article 15. The scanner flagged that ML framework is in use (numpy, torch_cpu) but no RNG seeds are set, and `torch.use_deterministic_algorithms`, `cudnn.deterministic`, and `cudnn.benchmark` flags aren't being asserted. For COMET specifically, that matters more than it would for most repos: when a translation provider cites a COMET score as Article 17 conformity evidence, an auditor's first question is going to be "can we reproduce this score on a clean machine?" Determinism flags and seed handling are what make that answer "yes." Pinning seeds in the scoring CLI and surfacing a determinism mode that flips the cuDNN switches would move that 0/10 to 4/10 without touching the model code at all.

**To be clear**: this doesn't mean COMET is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

If COMET is going to remain the metric that EU translation providers cite for Article 17 evidence, and I think it is, shipping a reproducibility mode plus a short COMPLIANCE.md mapping the scoring CLI to Articles 11, 12, and 15 would basically make it the only MT eval tool with a written EU AI Act story. Happy to share the full scan output if useful.

Best,
Jason Shotwell
https://airblackbox.ai
