# Email to Mem0

**To**: taranjeet@mem0.ai
**From**: jason@airblackbox.ai
**Subject**: EU AI Act compliance scan results for Mem0 (599 files scanned)

---

Hey Taranjeet,

I'm Jason, the maintainer of AIR Blackbox, an open-source EU AI Act compliance scanner (Apache 2.0, ~1,700 installs this month on PyPI).

I scanned Mem0's entire codebase and wanted to share what I found. With 41K+ stars and AWS selecting Mem0 as their exclusive memory provider, your enterprise customers almost certainly have EU operations that fall under the EU AI Act (enforcement starts August 2, 2026). Memory layers that store personal data are exactly what regulators will focus on under both the EU AI Act and GDPR.

**Summary**: 599 Python files scanned, 12/45 checks passing (27%).

Here's the full scan output:

```
AIR Blackbox - EU AI Act Compliance Check
Scanning: mem0

                    Article 9 - Risk Management
 Check                    | Status |  Evidence
 Risk assessment document |  FAIL  |  No risk assessment document found
 Risk mitigations active  |  FAIL  |  0/4 mitigations active
 LLM call error handling  |  WARN  |  45/72 files with LLM calls have error handling
 Fallback/recovery        |  PASS  |  Fallback patterns found in 34 file(s)

                    Article 10 - Data Governance
 Check                    | Status |  Evidence
 PII detection in prompts |  FAIL  |  Gateway not reachable
 Data governance docs     |  FAIL  |  No data governance documentation found
 Data vault               |  FAIL  |  No vault configured
 Input validation         |  PASS  |  Input validation found in 93/599 Python files
 PII handling in code     |  WARN  |  PII-aware variable names in 8 file(s), but no detection/redaction library

                    Article 11 - Technical Documentation
 Check                    | Status |  Evidence
 System description       |  PASS  |  README.md found
 Runtime system inventory |  FAIL  |  No traffic data
 Model card               |  WARN  |  No model card found
 Code documentation       |  WARN  |  862/1561 public functions have docstrings (55%)
 Type annotations         |  PASS  |  644/1120 public functions have type hints (57%)

                    Article 12 - Record-Keeping
 Check                    | Status |  Evidence
 Automatic event logging  |  FAIL  |  Gateway not reachable
 Tamper-evident audit     |  FAIL  |  No TRUST_SIGNING_KEY set
 Log traceability         |  FAIL  |  No logged records
 Application logging      |  WARN  |  Logging found in 112/599 files (19%)
 Tracing / observability  |  PASS  |  Tracing patterns in 69 file(s)
 Agent action audit trail |  WARN  |  No action-level audit trail detected

                    Article 14 - Human Oversight
 Check                    | Status |  Evidence
 Human-in-the-loop        |  WARN  |  No traffic data
 Kill switch              |  FAIL  |  Gateway not running
 Operator documentation   |  WARN  |  No operator documentation found
 HITL patterns            |  WARN  |  No human approval gates detected
 Usage limits / budget    |  WARN  |  Basic limits in 85 file(s), no explicit budget enforcement
 Agent identity binding   |  WARN  |  User identity in 45 file(s), but no explicit delegation binding
 Token scope validation   |  WARN  |  No token scope validation detected
 Token expiry / bounding  |  PASS  |  Token expiry found in 3 file(s)
 Agent action boundaries  |  PASS  |  Action boundary controls found in 2 file(s)

                    Article 15 - Accuracy, Robustness & Cybersecurity
 Check                    | Status |  Evidence
 Injection protection     |  FAIL  |  No runtime injection protection
 Error resilience         |  WARN  |  No traffic data
 API access control       |  WARN  |  No API keys detected
 Adversarial testing      |  WARN  |  No red team evidence
 Retry / backoff logic    |  PASS  |  Retry/backoff in 9 file(s)
 Injection defense        |  PASS  |  Injection defense patterns in 1 file(s)
 Unsafe input handling    |  WARN  |  Possible raw user input in 18 file(s)
 LLM output validation    |  PASS  |  Output parsing/validation in 50 file(s)

                    Compliance Summary
 12 passing  22 warnings  11 failing  out of 45 checks

   Static analysis:  12/34 passing  (code patterns, docs, config)
   Runtime checks:    0/11 passing  (requires gateway or trust layer)

 Detected frameworks: anthropic, langchain, openai
```

Three things stood out:

1. **55% docstring coverage** (862/1,561 functions). That's well above average across the 30+ projects I've scanned. Combined with 57% type hints, Mem0's codebase is more documented than most.

2. **The PII gap is the critical one.** Mem0 stores personal memories -- names, preferences, conversation history. The scanner found PII-aware variable names in 8 files but no detection or redaction library. For a memory layer handling personal data, this is the check EU regulators (and GDPR enforcers) will open with. Article 10 (Data Governance) shows 1/5 passing.

3. **Article 12 (Record-Keeping) is wide open.** Tracing patterns exist in 69 files, which is a solid foundation. But there's no tamper-evident audit chain and no action-level audit trail. When an agent stores or retrieves a memory, there's no verifiable record of what happened.

**To be clear**: this doesn't mean Mem0 is non-compliant. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool. But it shows where the gaps are so teams can prioritize.

The scanner is open source: https://github.com/air-blackbox/gateway

Run it yourselves:

```bash
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

Everything runs locally. No data leaves your machine.

I also built trust layers for Anthropic, LangChain, and OpenAI (all three frameworks detected in Mem0) that add HMAC-SHA256 tamper-evident audit chains:

```python
import air_blackbox
air_blackbox.attach("langchain")  # or "anthropic" or "openai"
```

This would close the Article 12 gap and give Mem0 users a path to audit-ready memory systems. Given that Mem0 handles personal data by design, having a compliance story baked in would be a strong signal to enterprise buyers evaluating memory layers for EU deployments. Happy to walk through it.

Best,
Jason Shotwell
https://airblackbox.ai
