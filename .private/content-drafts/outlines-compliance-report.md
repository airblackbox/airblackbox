# EU AI Act Compliance Report: Outlines by .txt (dottxt-ai)

**Generated**: April 7, 2026
**Scanner**: AIR Blackbox v1.6+ (CLI + MCP Trust Layer Analysis)
**Repository**: github.com/dottxt-ai/outlines
**Company**: .txt (dottxt), Paris, France (EU-domiciled)
**GitHub Stars**: 13,400+
**Funding**: $11.9M (Elaia, EQT Ventures)

---

## Executive Summary

Outlines scores **8 out of 45 checks passing (18%)** on the full AIR Blackbox compliance scan. The project has strong foundations in input validation (Pydantic in 52% of files) and type annotations (73%), but has critical gaps in record-keeping, human oversight, and GDPR compliance. As an EU-domiciled company, .txt is directly subject to the EU AI Act enforcement deadline of **August 2, 2026**, with penalties up to **€35M or 7% of global turnover**.

**Frameworks detected**: Anthropic, OpenAI
**Trust layer present**: No

---

## Overall Score Breakdown

| Category | Passing | Warnings | Failing | Total |
|----------|---------|----------|---------|-------|
| Static Analysis (code patterns, docs, config) | 8 | 16 | 10 | 34 |
| Runtime Checks (requires gateway/trust layer) | 0 | 4 | 7 | 11 |
| **Combined** | **8** | **20** | **17** | **45** |

---

## Per-Article Deep Dive

### Article 9 - Risk Management (1/4 passing)

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| Risk assessment document | FAIL | HIGH | No RISK_ASSESSMENT.md found |
| Risk mitigations active | FAIL | HIGH | 0/4 mitigations active |
| LLM call error handling | WARN | AUTO | 6/26 files with LLM calls have error handling |
| Fallback/recovery patterns | PASS | AUTO | Fallback patterns found in 3 files |

**Key finding**: The Anthropic integration (`outlines/models/anthropic.py`) makes API calls to `client.messages.create()` with **no try/except error handling**. If the Anthropic API returns a 500, rate-limit error, or timeout, the entire generation pipeline crashes with an unhandled exception. The OpenAI integration, by contrast, properly wraps calls in `try/except openai.BadRequestError`.

**Missing files with error handling**: `generator.py`, `models/sglang.py`, `models/anthropic.py`, `models/vllm.py`

**Fix**: Create `RISK_ASSESSMENT.md` documenting risks, likelihood, impact, and mitigations. Wrap all LLM API calls in try/except.

---

### Article 10 - Data Governance (1/5 passing)

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| PII detection in prompts | FAIL | AUTO | Gateway not reachable, no runtime PII scanning |
| Data governance documentation | FAIL | HIGH | No DATA_GOVERNANCE.md found |
| Data vault (controlled storage) | FAIL | AUTO | No vault configured |
| Input validation / schema enforcement | PASS | AUTO | Pydantic in 62/119 files (52%) |
| PII handling in code | WARN | AUTO | No PII detection/redaction/masking patterns |

**Key finding**: Outlines' greatest strength is its input validation. As a structured generation library, Pydantic is core to the project. 52% of files use Pydantic, dataclass, or similar validation. However, there is **zero PII handling**. User prompts flow directly to LLM APIs (Anthropic, OpenAI, Gemini, etc.) without any PII detection, redaction, or masking. For an EU company, this is a significant GDPR exposure.

**Fix**: Add PII detection before sending data to LLM providers (e.g., `presidio`, `scrubadub`). Create `DATA_GOVERNANCE.md`.

---

### Article 11 - Technical Documentation (2/5 passing)

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| System description (README) | PASS | HIGH | README.md found |
| Runtime system inventory (AI-BOM) | FAIL | AUTO | No traffic data, no trust layer |
| Model card / system card | WARN | HIGH | No MODEL_CARD.md found |
| Code documentation (docstrings) | WARN | AUTO | 255/428 public functions have docstrings (60%) |
| Type annotations | PASS | AUTO | 240/327 public functions have type hints (73%) |

**Key finding**: Documentation is decent. 60% docstring coverage and 73% type hint coverage are above average for open-source projects. The main gaps are the missing MODEL_CARD.md (required for documenting intended use, limitations, performance, and ethics) and no runtime AI-BOM (Bill of Materials) tracking which models are being called.

**Fix**: Create `MODEL_CARD.md`. Install a trust layer for runtime AI-BOM generation.

---

### Article 12 - Record-Keeping (0/6 passing) ⚠️ CRITICAL GAP

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| Automatic event logging | FAIL | AUTO | Gateway not reachable, no trust layer |
| Tamper-evident audit chain | FAIL | AUTO | No TRUST_SIGNING_KEY set |
| Log detail and traceability | FAIL | AUTO | No logged records |
| Application logging | FAIL | AUTO | No logging framework detected (logging, structlog, loguru) |
| Tracing / observability | WARN | AUTO | No tracing/observability integration |
| Agent action audit trail | WARN | AUTO | No action-level audit trail |

**Key finding**: This is Outlines' worst-performing article. **Zero checks pass.** There is no `import logging` anywhere in the core library. No structlog. No loguru. No OpenTelemetry. When a user calls `Generator(model, output_type)(prompt)`, there is zero record of: what model was called, what prompt was sent, what output was returned, how long it took, or whether it succeeded or failed. For a library processing enterprise LLM requests, this is the single biggest compliance risk.

**What Article 12 requires** (per EU AI Act):
- Automatic logging of system events
- Traceability of AI decisions and actions
- Tamper-evident record storage
- Retention of logs for compliance audits

**Trust layer fix**:
```python
# Install: pip install air-blackbox[openai]
from openai import OpenAI
from air_blackbox import AirTrust

trust = AirTrust()
client = trust.attach(OpenAI())  # Every call now HMAC-logged

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Your prompt here"}]
)
```

This adds HMAC-SHA256 tamper-evident audit logging, ConsentGate for high-risk actions, and DataVault PII tokenization.

---

### Article 14 - Human Oversight (1/9 passing)

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| Human-in-the-loop mechanism | WARN | AUTO | No traffic data |
| Kill switch / stop mechanism | FAIL | AUTO | Gateway not running |
| Operator understanding documentation | WARN | MEDIUM | No OPERATOR_GUIDE.md |
| Human-in-the-loop patterns | WARN | AUTO | No human approval gates |
| Usage limits / budget controls | WARN | AUTO | Basic limits (max_tokens) in 19 files, no budget enforcement |
| Agent-to-user identity binding | PASS | AUTO | Delegation/identity binding in 1 file |
| Token scope / permission validation | WARN | AUTO | No token scope validation |
| Token expiry / execution bounding | FAIL | AUTO | No token expiry, agent may run indefinitely |
| Agent action boundaries | WARN | AUTO | Unrestricted tool/action access |

**Key finding**: Outlines has basic execution limits (max_tokens, max_iterations) referenced in 19 files, and one file with agent identity binding. But there are no human approval gates, no kill switch, no operator documentation, and no explicit budget enforcement. When Outlines is used in production agentic workflows, there is no way for a human operator to intervene, pause, or halt generation.

**What Article 14 requires** (per EU AI Act):
- Enable humans to understand AI system capabilities/limitations
- Allow monitoring of AI operation
- Provide ability to intervene or halt the system
- Maintain human control over automated decisions

**Fix**: Create `OPERATOR_GUIDE.md`. Add explicit budget limits. Implement token expiry/execution timeout.

---

### Article 15 - Accuracy, Robustness & Cybersecurity (2/8 passing)

| Check | Status | Severity | Evidence |
|-------|--------|----------|----------|
| Prompt injection protection | FAIL | AUTO | No runtime injection protection |
| Error resilience | WARN | AUTO | No traffic data |
| API access control | WARN | HIGH | No API keys detected |
| Adversarial robustness testing | WARN | MEDIUM | No red team/adversarial testing evidence |
| Retry / backoff logic | PASS | AUTO | Retry/backoff in 3 files |
| Prompt injection defense | WARN | AUTO | No defense patterns detected |
| Unsafe input handling | WARN | AUTO | Raw user input in prompts in 17 files |
| LLM output validation | PASS | AUTO | Output validation in 14 files |

**Key finding**: Outlines has solid LLM output validation (its core purpose is structured generation), and retry/backoff logic in 3 files. However, **17 files pass raw user input directly into LLM prompts** without sanitization, including: `vllm_offline.py`, `gemini.py`, `dottxt.py`, `sglang.py`, `ollama.py`, and others. There is no prompt injection defense at any layer.

**Injection test result**: AIR Blackbox's injection scanner correctly blocks test payloads like "Ignore all previous instructions" with **90% confidence** and a **BLOCKED** verdict. This level of protection is available but not integrated into Outlines.

**Fix**: Add input sanitization. Install a trust layer for runtime injection scanning.

---

### GDPR Data Protection (1/8 passing)

| Check | Status | Evidence |
|-------|--------|----------|
| Consent management | WARN | No consent tracking for data processing |
| Data minimization | WARN | No data minimization patterns |
| Right to erasure | WARN | No right-to-erasure implementation |
| Data retention policy | PASS | Retention/TTL patterns in 1 file |
| Cross-border transfer safeguards | WARN | No data residency controls |
| Data protection impact assessment | WARN | No DPIA references |
| Records of processing | WARN | No processing activity records |
| Breach notification | WARN | No breach detection/notification |

**Key finding**: As a French company, .txt must comply with GDPR. User prompts sent through Outlines to US-based LLM providers (OpenAI, Anthropic) constitute cross-border data transfer with no safeguards detected. There is no consent management, no data minimization, and no right-to-erasure implementation.

---

## Trust Layer Integration

Outlines uses two frameworks that have AIR Blackbox trust layers available:

### Anthropic Trust Layer
```python
# Install: pip install air-anthropic-trust
from air_blackbox import AirTrust
from anthropic import Anthropic

trust = AirTrust()
client = trust.attach(Anthropic())
# All calls now HMAC-logged with audit trails
```

### OpenAI Trust Layer
```python
# Install: pip install air-openai-trust
from air_blackbox import AirTrust
from openai import OpenAI

trust = AirTrust()
client = trust.attach(OpenAI())
# All calls now HMAC-logged with audit trails
```

**What the trust layer adds**:
- HMAC-SHA256 tamper-evident audit logging (Article 12)
- ConsentGate for high-risk actions (Article 14)
- DataVault PII tokenization (Article 10)
- Runtime prompt injection scanning (Article 15)

---

## Priority Remediation Roadmap

### Immediate (Week 1) - Critical gaps
1. **Add application logging** - `import logging` in generator.py and all model files
2. **Create RISK_ASSESSMENT.md** - Document risks for structured generation
3. **Wrap Anthropic API calls in try/except** - Match OpenAI's error handling pattern

### Short-term (Weeks 2-4) - High-impact fixes
4. **Install trust layers** for Anthropic and OpenAI integrations
5. **Add PII detection** before LLM API calls (presidio or scrubadub)
6. **Create DATA_GOVERNANCE.md** and **MODEL_CARD.md**
7. **Add OpenTelemetry tracing** for observability

### Medium-term (Months 2-3) - Compliance hardening
8. **Implement prompt injection defense** for the 17 files with raw user input
9. **Add GDPR controls** - consent management, data minimization, right to erasure
10. **Create OPERATOR_GUIDE.md** with human oversight documentation
11. **Add budget enforcement** and execution timeouts
12. **Conduct adversarial testing** and document results

---

## Risk Summary

| Risk Level | Count | Examples |
|------------|-------|---------|
| CRITICAL | 2 | No logging at all (Art. 12), No PII handling for EU company (GDPR) |
| HIGH | 5 | No risk assessment, no data governance docs, no human approval gates, no injection defense, raw user input in 17 files |
| MEDIUM | 10 | Missing model card, 60% docstring coverage, no tracing, no budget controls, no action boundaries |
| LOW | 3 | Type hints at 73% (not 100%), retry in only 3 files |

---

*Report generated by AIR Blackbox. The scanner checks for technical patterns mapped to EU AI Act Articles 9 through 15. It's a linter for AI governance, not a legal compliance tool.*

*Scanner: https://github.com/air-blackbox/gateway*
*Website: https://airblackbox.ai*
