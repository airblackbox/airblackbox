# Email to Pyronear

**To**: contact@pyronear.org
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Pyronear (60 files scanned)

---

Hey François-Guillaume (and the Pyronear team),

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the `pyro-engine` repo through the scanner and wanted to share what I found. Wildfire detection running on edge devices for French and southern European public-safety partners is exactly the kind of computer-vision system the EU AI Act treats with extra scrutiny under Annex III (critical infrastructure / public-safety adjacency), and as a French NGO operating directly inside the EU, the Article 9 to Article 15 obligations apply to Pyronear from day one of August 2026.

**Summary**: 60 Python files scanned, 14/57 checks passing (25%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 1/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 4/10 passing |

The strongest result is Article 15 at 4/10, where the scanner picked up retry/backoff in 8 files and confirmed deterministic / hardware-abstraction patterns are clean - that's exactly what edge inference needs. Article 12 (4/9) reflects the structured logging already in the engine and a passing log-retention configuration, which is a good base for Article 12 evidence. The biggest gap is Article 14 (1/9): only the kill switch passes, and the rest of human-oversight surface (operator documentation, action boundaries, token expiry on the autonomous detection loop) is not yet visible to the scanner. For a wildfire alert that lands in front of a sapeurs-pompiers operator, Article 14 evidence is the part EU regulators are going to look at first.

**To be clear**: this doesn't mean Pyronear is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Given how directly Pyronear sits in EU public-safety workflows, even a few upstream changes (an operator-facing OPERATOR.md describing the alert review path, a documented confidence threshold on the detector entry point, an action-bounded autonomous loop) would let downstream deployers point regulators at upstream evidence rather than rebuilding it themselves. Happy to share the full per-check report or open a draft issue at pyronear/pyro-engine if that's easier than email.

Best,
Jason Shotwell
https://airblackbox.ai
