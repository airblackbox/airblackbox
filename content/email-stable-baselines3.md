# Email to Stable-Baselines3

**To**: antonin.raffin@dlr.de
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Stable-Baselines3 (97 files scanned)

---

Hey Antonin,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Stable-Baselines3 through the scanner and wanted to share what I found. SB3 sits underneath a huge amount of European RL research and applied work, and as DLR-RM ships it to robotics labs and industrial RL teams across the EU, the same Article 9 to Article 15 obligations that apply to any high-risk AI controller increasingly trace back to the training and policy code that came out of this repo.

**Summary**: 97 Python files scanned, 9/57 checks passing (16%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 3/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 0/10 passing |

The Article 11 result is genuinely strong for an RL library: docstrings, type hints, and a documentation site are all in place and the scanner picks them up. The Article 15 number is where downstream EU users most often get caught. Specifically the scanner flagged hardcoded CUDA device strings in `stable_baselines3/common/utils.py` with no capability fallback, plus missing `torch.use_deterministic_algorithms` and `torch.backends.cudnn.benchmark=False` defaults. Even with seeds set, cuDNN picks non-deterministic kernels, so the same trained policy can produce different outputs across A100 vs H100, which is exactly the failure mode Article 15 robustness language is written to prevent for deployed models.

**To be clear**: this doesn't mean Stable-Baselines3 is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how many EU groups are now wrapping SB3 inside Annex III deployments (energy, mobility, robotics) where Articles 9, 12, and 14 obligations land on the deploying organization, even a couple of upstream patterns (deterministic flags by default in `set_random_seed`, a structured run-record hook in `BaseAlgorithm.learn`) would meaningfully reduce evidence collection burden for everyone using SB3 in production. Happy to share the full per-check report if useful, and would love your read on whether any of this is worth a small upstream PR vs. a documentation note.

Best,
Jason Shotwell
https://airblackbox.ai
