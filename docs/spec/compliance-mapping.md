# AIR Blackbox Compliance Mapping

**Version:** 1.0.0
**Date:** 2026-03-13
**Author:** Jason Shotwell

Maps AIR Blackbox's 6-article EU AI Act checks to ISO/IEC 42001, NIST AI RMF, and NIST AI 600-1.

---

## EU AI Act → ISO/IEC 42001 (AI Management System)

ISO/IEC 42001:2023 defines requirements for an AI management system (AIMS). AIR Blackbox checks map to ISO controls as follows:

| AIR Check | EU AI Act Article | ISO 42001 Control | Coverage | How AIR Satisfies It |
|-----------|-------------------|-------------------|----------|---------------------|
| Risk classification (ConsentGate) | Art. 9 - Risk Management | 6.1.2 AI risk assessment | Full | Tool calls classified CRITICAL/HIGH/MEDIUM/LOW with gating |
| PII scanning (DataVault) | Art. 10 - Data Governance | A.8.5 Data quality for AI | Full | Regex-based PII detection (email, SSN, phone, credit card, IBAN) |
| Structured logging (TrustHandler) | Art. 11 - Technical Documentation | A.6.2.5 Documenting AI system | Full | Every operation logged as structured .air.json with timestamps |
| HMAC audit chain (AuditLedger) | Art. 12 - Record-Keeping | A.6.2.6 Recording activity logs | Full | Tamper-evident HMAC-SHA256 chain per Audit Chain Spec v1.0 |
| Approval gates (ConsentGate) | Art. 14 - Human Oversight | A.8.4 Human oversight of AI | Full | Permission handler blocks CRITICAL tools, requires approval for HIGH |
| Injection scanning (InjectionDetector) | Art. 15 - Cybersecurity | A.8.6 AI system security | Full | 15 weighted injection patterns with confidence scoring |

**Additional ISO 42001 coverage:**

| ISO 42001 Control | AIR Feature | Notes |
|-------------------|-------------|-------|
| A.5.4 AI system life cycle | Compliance history (SQLite) | Tracks compliance scores over time |
| A.6.2.4 AI system inventory | `air-blackbox discover` + AI-BOM | CycloneDX AI-BOM generation |
| A.8.2 Intended use documentation | Compliance scan report | Documents what the AI system does and checks |
| A.9.3 System performance monitoring | `air-blackbox replay` | Incident reconstruction from audit trail |
| A.10.2 Third-party risk | Deep scan (LLM analysis) | Analyzes third-party framework usage |

---

## EU AI Act → NIST AI Risk Management Framework (AI RMF 1.0)

NIST AI RMF organizes AI risk management into four functions: Govern, Map, Measure, Manage.

| AIR Check | EU AI Act Article | NIST AI RMF Function | NIST AI RMF Category | Coverage |
|-----------|-------------------|---------------------|---------------------|----------|
| Risk classification | Art. 9 | MAP | MAP 5: Risk assessment | Full |
| PII scanning | Art. 10 | GOVERN | GOVERN 1.5: Privacy and data governance | Full |
| Structured logging | Art. 11 | GOVERN | GOVERN 4.1: Organizational documentation | Full |
| HMAC audit chain | Art. 12 | MEASURE | MEASURE 2.6: Evaluation and monitoring | Full |
| Approval gates | Art. 14 | MANAGE | MANAGE 1.3: Risk response | Full |
| Injection scanning | Art. 15 | MANAGE | MANAGE 2.2: Security and resilience | Full |

**NIST AI RMF subcategory detail:**

| NIST Subcategory | AIR Feature | Evidence |
|------------------|-------------|----------|
| MAP 1.1: Intended purpose defined | Compliance scan | Scanner identifies framework, model, and tool usage |
| MAP 5.1: Likelihood of identified risks | Risk classification | CRITICAL/HIGH/MEDIUM/LOW mapping with automated gating |
| MEASURE 2.5: AI system monitored | Audit chain + replay | Real-time event recording with chain verification |
| MEASURE 2.6: Regular evaluation | Compliance history | SQLite tracks score trends, scan diffs over time |
| MANAGE 1.1: Risk prioritization | Risk classification | Tool calls prioritized by risk level |
| MANAGE 2.4: Mechanisms for feedback | Pre-commit hooks + CI | Developers get compliance feedback on every commit |

---

## EU AI Act → NIST AI 600-1 (Generative AI Profile)

NIST AI 600-1 extends the AI RMF specifically for generative AI systems. AIR Blackbox addresses GenAI-specific risks:

| NIST AI 600-1 Risk | AIR Check | How It's Addressed |
|--------------------|-----------|-------------------|
| **CBRN Information** | Injection scanning | Detects and blocks prompt injection attempts that could extract dangerous information |
| **Confabulation** | Deep scan (LLM) | Identifies hallucination risk in agent outputs via local model analysis |
| **Data Privacy** | PII scanning | Detects PII in prompts before they reach LLM APIs |
| **Information Integrity** | HMAC audit chain | Tamper-evident logging prevents post-hoc manipulation of AI outputs |
| **Information Security** | Injection scanning + risk gating | Multi-layer defense: pattern matching + confidence scoring + tool blocking |
| **Intellectual Property** | AI-BOM generation | CycloneDX inventory tracks all AI components and their licenses |
| **Obscene/Degrading Content** | Content policy scanner | Static analysis detects missing content filters |
| **Value Chain / Component** | `air-blackbox discover` | Shadow AI inventory identifies all AI components in the codebase |
| **Human-AI Configuration** | Approval gates | ConsentGate requires human approval for high-risk agent operations |

---

## EU AI Act → OECD AI Principles

| OECD Principle | AIR Check | Coverage |
|----------------|-----------|----------|
| 1.1 Inclusive growth | - | Not directly applicable (policy, not technical) |
| 1.2 Human-centered values | Approval gates, PII scanning | Ensures human oversight and data protection |
| 1.3 Transparency | Structured logging, audit chain | Full operation transparency via .air.json records |
| 1.4 Robustness and security | Injection scanning, risk classification | Multi-layer security with pattern matching |
| 1.5 Accountability | HMAC audit chain, evidence bundle | Tamper-evident records + signed evidence packages |

---

## How to Reference This Mapping

When writing compliance documentation for your AI system, you can reference specific AIR Blackbox checks:

```
Risk Management (ISO 42001 §6.1.2 / EU AI Act Art. 9):
  Tool: AIR Blackbox v1.2.6 - ConsentGate risk classification
  Evidence: .air.json records with risk_level field
  Verification: python verify_chain.py ./runs --key <signing-key>
```

For ISO 42001 certification auditors, the evidence bundle generated by `air-blackbox export` contains:
- Compliance scan results mapped to Articles 9-15
- CycloneDX AI-BOM (software bill of materials for AI)
- Audit trail statistics with chain verification status
- HMAC-SHA256 signed attestation

---

## Limitations

This mapping covers **technical** controls only. AIR Blackbox does not address:

- Organizational policies or governance structures (ISO 42001 §5, §7)
- Bias testing or fairness evaluation (NIST AI RMF MEASURE 2.7)
- Environmental impact assessment (EU AI Act Art. 40)
- Legal compliance review (consult qualified legal counsel)
- Human resource training requirements (ISO 42001 §7.2)

AIR Blackbox is a technical compliance scanner - it checks code, not processes. Use it alongside organizational compliance frameworks, not as a replacement for them.
