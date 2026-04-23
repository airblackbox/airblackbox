# Email to Silo AI / LumiOpen (Megatron-LM-lumi)

**To**: peter.sarlin@silo.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Megatron-LM-lumi (282 files scanned)

---

Hey Peter,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran Megatron-LM-lumi (the LumiOpen training fork behind Poro and Viking) through the scanner and wanted to share what I found. Silo AI under AMD is uniquely positioned as one of the loudest voices for European AI sovereignty, and the Poro and Viking families are the flagship open models for Nordic languages. Once the EU AI Act enforcement deadline hits August 2, 2026, the training pipelines used to produce those models will be exactly what auditors ask about first, especially when public-sector customers deploy these models under GPAI rules.

**Summary**: 282 Python files scanned, 14/58 checks passing (24%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/5 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/9 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 2/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 2/11 passing |

Good news up front: Article 12 (Record-Keeping) has the highest pass rate of the set (3/9), driven by structured logging and processing-record patterns in training scripts. The biggest gap is Article 10 (Data Governance) at 1/5. For a pretraining stack that ingests a trillion-token multilingual corpus, data-governance evidence is the area regulators will scrutinize hardest under GPAI transparency obligations, and it is also the area where the NVIDIA upstream inherits the least EU-specific hygiene.

**To be clear**: this does not mean Megatron-LM-lumi is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It is a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

Nordic public-sector buyers care a lot about sovereign, auditable model provenance. Having Poro and Viking ship with an explicit EU AI Act compliance report attached to the training code would be a real differentiator. Would be glad to walk through the details with the LumiOpen team.

Best,
Jason Shotwell
https://airblackbox.ai
