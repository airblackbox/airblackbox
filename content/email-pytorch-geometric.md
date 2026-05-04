# Email to PyTorch Geometric (PyG)

**To**: matthias@pyg.org
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for PyTorch Geometric (1,328 files scanned)

---

Hey Matthias,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran PyTorch Geometric through the scanner and wanted to share what I found. PyG is the default Python graph neural network library across European pharma (drug discovery), banking (graph fraud and AML), telecom (network anomaly), and energy (grid forecasting). All of those are Annex III high-risk territory under the EU AI Act, and the moment one of those models lands in production, every downstream EU deployer has to assemble Article 9 to Article 15 evidence with PyG sitting at the bottom of their stack. That makes PyG's API surface an unusually high-leverage place to fix things upstream.

**Summary**: 1,328 Python files scanned, 20/58 checks passing (34%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 2/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 4/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/11 passing |

The strongest result is Article 12 at 4/9: PyG passes on logging infrastructure, tracing/observability, and action-level audit patterns, which makes sense given how seriously the project takes reproducibility. Article 15 also benefits from a clean determinism story (RNG seeding, deterministic algorithm flags, hardware abstraction, retry/backoff all pass). The lowest-scoring article is Article 11 at 2/5, and that's the one with the most practical impact for regulated EU users: docstring coverage on public functions is below threshold, and the scanner can't find a model card / system card next to the README. Article 11 is what every EU deployer points at when they need to show "Technical Documentation" evidence to their notified body, and right now the boilerplate has to come from each downstream user instead of being inherited from PyG.

**To be clear**: this doesn't mean PyTorch Geometric is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Two upstream changes would shift the score noticeably and make life easier for every regulated EU graph-ML team building on top of PyG: (1) a `MODEL_CARD.md` template covering intended use, limitations, and known failure modes for the canonical PyG models in `torch_geometric.nn.models`, and (2) docstring coverage on the public `Data`, `HeteroData`, `MessagePassing`, and `GNNExplainer` entry points. Both are small, but they let downstream Article 11 evidence collection move from "rewrite from scratch" to "library default." Happy to share the full per-check report, or - given Kumo.AI's enterprise customer base - talk through what an "Article 9 to 15 ready" PyG distribution might look like for those deployers.

Best,
Jason Shotwell
https://airblackbox.ai
