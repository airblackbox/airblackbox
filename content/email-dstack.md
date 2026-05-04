# Email to dstack

**To**: andrey@dstack.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for dstack (938 files scanned)

---

Hey Andrey,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran dstackai/dstack through the scanner and wanted to share what I found. dstack sits one layer below where most EU AI Act conversations happen: when a team in Munich, Paris, or Amsterdam runs a high-risk training or inference job in 2026, dstack is what's actually scheduling it across their cloud and on-prem GPUs. That makes the run records, fleet-level config, and access patterns dstack persists a natural carrier for Article 12 record-keeping evidence and Article 14 oversight controls, on behalf of every customer who sits inside the EU AI Act perimeter.

**Summary**: 938 Python files scanned, 18/57 checks passing (32%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 2/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 5/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 5/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/10 passing |

The good news first: Article 14 at 5/9 is the strongest result in this batch and is genuinely uncommon for infra. The fact that dstack already has fleet-level rate-limiting, role/scope plumbing, and approval-style flows around fleet operations means the bones of an Article 14 story are already in the codebase rather than something a customer has to bolt on. Article 12 at 5/9 reflects the structured run-record / job-history primitives the scheduler emits - exactly the surface a notified body wants to read.

The biggest lever is Article 15, currently 2/10. The scanner flagged that the dstack control plane handles user-supplied YAML configurations, environment variables, and command strings that get rendered into shell invocations on remote runners - that's a real attack surface, and the scanner detected gaps around input sanitization, prompt/template injection defense in the `agent` and `service` paths, and adversarial-robustness testing scaffolding. A documented `dstack.security` posture that (a) treats every user-supplied YAML field as untrusted and runs it through a single validation seam, (b) ships a small red-team test suite as part of CI for the runner-templating layer, and (c) exposes a per-fleet "block external egress except allowlisted domains" toggle would push Article 15 from 2/10 toward 6/10 and remove the most likely line of audit questioning from EU enterprise reviewers.

**To be clear**: this doesn't mean dstack is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Infrastructure is the layer where Article 12 and Article 14 evidence either gets produced for free, or has to be reconstructed by every customer separately at great pain. If dstack ships a thoughtful `dstack.compliance` posture before August 2026 - run records that include risk tags, kill-switch and approval primitives surfaced in the YAML schema, hardened runner templating - it becomes the obvious orchestrator for EU teams that don't want to be the one writing their own Article 12 evidence pipeline. Happy to share the full scan output, or to compare notes on what a compliance roadmap could look like, if useful.

Best,
Jason Shotwell
https://airblackbox.ai
