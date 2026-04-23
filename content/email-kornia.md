# Email to Kornia

**To**: edgar@kornia.org
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Kornia (764 files scanned)

---

Hey Edgar,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Kornia through the scanner and wanted to share what I found. Kornia sits underneath a lot of the real-world computer vision that's about to fall inside the EU AI Act's high-risk annex: biometrics, safety components in vehicles, and image-based identification in border and law-enforcement contexts. Downstream teams shipping those systems will be pointing to upstream libraries like Kornia in their Article 10 data-governance and Article 15 robustness evidence, which is why I thought a scan would be useful to share with the maintainers directly.

**Summary**: 764 Python files scanned, 14/58 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/11 passing |

The strong side: Art. 13 transparency actually comes in at 4/6. Kornia's README, AUTHORS, LICENSE, and semantic versioning all register cleanly, and that's a real asset when downstream teams need to cite provenance for an upstream library. Art. 12 at 3/9 is also better than most ML library codebases I've scanned; there's structured logging in enough modules to register.

The biggest gap is Art. 15 at 1/11, and with a CV library that's mostly where downstream compliance teams will focus. The scanner didn't find RNG-seed determinism flags, deterministic algorithm pinning, or hardware abstraction signals at the API level. For a differentiable CV library that's explicitly a building block for PyTorch models, a short "reproducibility and determinism" section in the docs plus a kornia.set_deterministic() helper would be meaningful, because Article 15 explicitly calls out reproducibility of outputs.

Art. 10 at 1/5 is the other one worth a look. Kornia processes image tensors, which are the data type most likely to carry biometric or face data in downstream pipelines. A one-page DATA_GOVERNANCE.md explaining that Kornia operators are stateless and don't persist tensors would close most of the Art. 10 gap for users who need to cite Kornia in their own DPIAs.

**To be clear**: this doesn't mean Kornia is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given Kornia's role as a non-profit maintained by an international contributor base, a visible compliance posture could actually help the foundation pitch for sponsorship from EU-based autonomous-driving, medical imaging, and biometrics companies who now have a procurement checklist that includes "does this library help us prove Article 15 compliance." Happy to share the full scan output, open a PR against the docs, or walk through the results together.

Best,
Jason Shotwell
https://airblackbox.ai
