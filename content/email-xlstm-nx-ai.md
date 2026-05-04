# Email to xLSTM (NX-AI)

**To**: beck@ml.jku.at
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for xLSTM (56 files scanned)

---

Hey Maximilian,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran xLSTM through the scanner and wanted to share what I found. The xLSTM 7B release positioned NXAI as the European answer to Transformer-only labs, and that framing lands on a regulatory environment where every EU enterprise that fine-tunes or deploys a model from this repo inherits Article 9 to Article 15 obligations directly.

**Summary**: 56 Python files scanned, 8/58 checks passing (14%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 0/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 2/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 0/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 1/11 passing |

The repo is intentionally focused on the architecture and reference kernels, so several of these gaps are expected. The one I'd flag for an EU-funded lab is Article 12 record-keeping. The training and inference paths don't currently emit structured run records (model version, config hash, dataset reference, host/device, seed state) which is exactly the artifact a downstream operator in Germany or Austria needs to satisfy Article 12 logging when they put an xLSTM-derived model behind a regulated workflow. Article 9 came back at 0/5 because the scanner can't see explicit error-handling or fallback patterns in the kernel paths, which is honest for low-level architecture code, but it's also the easiest thing to address with a thin wrapper around the public API.

**To be clear**: this doesn't mean xLSTM is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given that xLSTM is being pitched as European AI infrastructure, having a clean Article 12 logging surface and a documented Article 9 risk story baked into the repo would be a real differentiator vs. the US labs your prospects are comparing you against. Happy to share the full per-check report and walk through any of the failing patterns with you or Korbinian.

Best,
Jason Shotwell
https://airblackbox.ai
