# Email to Ray (Anyscale)

**To**: robert@anyscale.com
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Ray (4,531 files scanned)

---

Hey Robert,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I ran the Ray codebase through the scanner and wanted to share what I found. This was the largest scan I've done across 40+ projects: 4,531 Python files. Ray powers AI infrastructure at Uber, Spotify, Canva, and Coinbase, with 27 million monthly downloads. With Anyscale now going GA on Azure in 2026 and the NVIDIA partnership for LLM training, the enterprise footprint is expanding fast. Many of those enterprises operate in the EU, and the August 2026 enforcement deadline means compliance requirements flow up the stack. When a customer's AI system is classified as high-risk under the EU AI Act, every layer of infrastructure, including the compute engine, falls under scrutiny.

**Summary**: 4,531 Python files scanned, 16/45 checks passing (36%).

Per-article breakdown:

| EU AI Act Article | What It Checks | Status |
|---|---|---|
| Art. 9 (Risk Management) | Error handling, fallbacks, risk classification | 1/4 passing |
| Art. 10 (Data Governance) | Input validation, PII handling, schemas | 1/5 passing |
| Art. 11 (Documentation) | Docstrings, type hints, system docs | 1/5 passing |
| Art. 12 (Record-Keeping) | Structured logging, audit trails | 3/6 passing |
| Art. 14 (Human Oversight) | Approval workflows, rate limiting | 4/9 passing |
| Art. 15 (Security) | Injection defense, output validation | 3/8 passing |

**Where Ray is genuinely impressive:**

Ray's scan results are among the strongest I've seen across all 40+ projects in my pipeline. The infrastructure-level patterns are exceptional:

- **Article 12 (Record-Keeping)**: Application logging in 1,026 of 4,531 files (23%). Production-grade tracing infrastructure in 505 files with 25 instances of production-grade distributed tracing. Action-level audit logging in 96 files. This is the best record-keeping surface I've scanned.
- **Article 9 (Risk Management)**: Fallback/recovery patterns in 523 files. That's not a typo. Ray's fault-tolerance architecture inherently provides the kind of error resilience the EU AI Act calls for.
- **Article 15 (Security)**: Retry/backoff logic in 394 files, injection defense patterns found, LLM output validation in 73 files.
- **Article 14 (Human Oversight)**: 4/9 passing, including rate limiting/budget controls, agent-to-user identity binding in 9 files, token expiry/execution timeout in 3 files, and action boundary controls. This is well above average.

Ray also showed GDPR-relevant patterns: consent management in 2 files, data retention/TTL patterns in 121 files, and records of processing in 204 files.

**Where the gaps are:**

Article 10 (Data Governance) and Article 11 (Documentation) are the weakest areas:

- No data governance documentation found. For a compute engine that handles training data pipelines, enterprise customers will need to demonstrate data provenance.
- No risk assessment document. Given Ray's scale, a formal risk assessment mapped to the EU AI Act's Article 9 requirements would strengthen the compliance story.
- Docstring coverage is 45% (8,524/19,087 public functions). The type annotation coverage is better at 64% (9,623/14,923 functions), but both could be higher for a project of Ray's significance.
- 47 files flagged for possible raw user input in prompts, including `collective_node.py`, `compiled_dag_node.py`, and various DAG test files. These are likely safe in context but worth reviewing.

**To be clear**: this doesn't mean Ray is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it quantifies where the gaps are so teams can prioritize, and for Ray, the story is largely positive.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built a drop-in trust layer that adds HMAC-SHA256 tamper-evident audit chains for LangChain (which was detected in Ray's AI libraries):

```python
import air_blackbox
air_blackbox.attach("langchain")
```

Given Ray's position as the compute foundation for enterprise AI, the compliance narrative is a differentiator, not a burden. Anyscale can tell enterprise customers: "Ray's infrastructure already passes 36% of EU AI Act compliance checks out of the box, and here's the roadmap for the rest." That's a powerful enterprise sales story as August 2026 approaches.

Would be great to discuss how compliance tooling fits into Anyscale's enterprise roadmap.

Best,
Jason Shotwell
https://airblackbox.ai
