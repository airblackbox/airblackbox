# Data Governance Framework for AIR Blackbox

## Overview

This document establishes data governance policies for the AIR Blackbox EU AI Act compliance scanner. It covers data sources, collection, retention, quality, privacy, and ethical handling practices.

## 1. Data Sources and Collection

### 1.1 Primary Data Sources

**Code Files**
- Python source code files (.py) submitted for compliance scanning
- Framework configuration files (pyproject.toml, requirements.txt, setup.py)
- Code comments and docstrings that document system behavior
- Import statements and dependency declarations
- Collection method: File upload or repository integration (GitHub, GitLab, Bitbucket)
- Frequency: On-demand per scan request; continuous monitoring for enrolled systems

**Gateway Logs**
- Scan request metadata (timestamp, user ID, file hash, scan parameters)
- Scan results (detected violations, confidence scores, remediation suggestions)
- Performance metrics (inference latency, model version, resource consumption)
- Audit events (user actions, configuration changes, system health)
- Collection method: Automatic capture during scan execution
- Retention: 90 days standard; 1 year for production systems under audit

**Audit Chain Records**
- Immutable ledger of all compliance determinations
- Cryptographic signatures binding results to input code
- User identities and timestamps for compliance events
- Evidence snapshots for regulatory reporting
- Collection method: Automatically generated during scan completion
- Retention: 7 years minimum (EU data retention requirements for compliance)

**Model Performance Data**
- Inference metrics: latency, throughput, model version
- Confidence score distributions for classifications
- False positive/negative feedback from human reviewers
- Framework and code pattern statistics
- Collection method: Automatic telemetry during operation
- Frequency: Continuous; aggregated weekly

### 1.2 Data Minimization

The scanner employs strict data minimization:
- Code content is analyzed in-memory; not stored permanently
- Scan results capture only the locations and types of violations
- Sensitive patterns (API keys, credentials) are detected but never logged
- PII detection identifies presence only; content is not retained
- Intermediate model outputs are discarded after inference
- Only aggregated metrics and anonymized patterns are retained long-term

## 2. Consent and Authorization

### 2.1 Consent Mechanisms

**Explicit Consent Required For:**
- Uploading code for scanning
- Continuous monitoring enrollment
- Data sharing with external auditors
- Telemetry collection for model improvements
- Integration with third-party compliance systems

**Consent Implementation:**
- Scanner requires explicit opt-in before any data collection
- Consent is documented per scan request
- Users can revoke consent; revocation disables further data collection
- Consent status is logged in audit chain
- Privacy policy available and must be acknowledged before scanning

**Default Behavior:**
- Scanning is local-first; no data transmitted by default
- Cloud integration is opt-in only
- Third-party LLM usage requires explicit approval
- Community analytics is opt-in

### 2.2 Data Sharing Authorization

**Authorized Recipients:**
- Internal compliance review team (to improve scanner accuracy)
- External auditors (upon enterprise customer request; under NDA)
- Regulatory authorities (only via proper legal process)
- Research institutions (only anonymized aggregate data)

**Unauthorized Sharing:**
- Never shares with marketing or advertising services
- Never sells user data or scan results
- Never shares with competitor analysis firms
- Never discloses customer identities to external parties
- Never transfers data outside EU without explicit consent

## 3. Data Quality Assurance

### 3.1 Validation Procedures

**Input Validation:**
- File format validation: ensure submitted files are valid Python code
- Size limits: reject files exceeding 100MB (timeout prevention)
- Encoding validation: verify UTF-8 compliance
- Schema validation: code must be parseable Python AST

**Data Quality Checks:**
- Verify scan results reference valid line numbers in input code
- Confidence scores normalized between 0.0 and 1.0
- Article references validated against EU AI Act Articles 9-15
- Timestamp consistency: scan completion time >= scan start time
- No contradictory classifications for same code pattern

**Quality Metrics:**
- 99.5% uptime SLA for scanner availability
- <5% false positive rate (validated quarterly)
- <2% false negative rate on test suite (100% on known violations)
- Model drift detection: alert if performance degrades >3% month-over-month

### 3.2 Schema Enforcement

**Scan Result Schema:**
```
{
  "scan_id": "UUID",
  "timestamp": "ISO8601",
  "file_hash": "SHA256",
  "framework": "string",
  "violations": [
    {
      "article": "9|10|11|12|14|15",
      "severity": "critical|high|medium|low",
      "confidence": 0.0-1.0,
      "line_numbers": [int],
      "recommendation": "string"
    }
  ],
  "metadata": {
    "model_version": "string",
    "inference_latency_ms": int,
    "code_lines": int
  }
}
```

**Audit Record Schema:**
```
{
  "event_id": "UUID",
  "event_type": "scan_completed|override_applied|escalation_created",
  "timestamp": "ISO8601",
  "user_id": "string (hashed)",
  "scan_id": "UUID",
  "signature": "HMAC-SHA256",
  "previous_signature": "HMAC-SHA256",
  "details": "object"
}
```

## 4. Data Retention Policies

### 4.1 Retention Schedule

| Data Type | Retention Period | Justification |
|-----------|------------------|---------------|
| Code content | 0 days (immediate deletion) | Minimization; user retains original |
| Scan results | 30 days default, 1 year enterprise | Operational; audit trail requirements |
| Audit chain records | 7 years minimum | EU regulatory compliance requirement |
| Gateway logs | 90 days | Operational troubleshooting; security investigation |
| Model performance telemetry | Indefinite (aggregated) | Model improvement and training |
| User feedback | 1 year | Continuous model improvement cycle |
| False positive reports | 3 years | Training data for retraining cycles |
| Compliance incident logs | 7 years | Regulatory audit trail |

### 4.2 Deletion Procedures

**Automated Deletion:**
- Code content: deleted immediately after scan completion
- Gateway logs: automated purge after 90 days
- Scan results: automated purge after retention period expires
- Deletion logged to audit chain before execution

**Manual Deletion:**
- User can request deletion of their scan results anytime
- Deletion requests processed within 30 days
- Deletion recorded in audit chain with user approval
- Cannot delete audit chain records (immutable by design)

**Data Subject Requests:**
- Right to access: user can download all their scans and results
- Right to erasure: user can request deletion of non-audit data
- Right to portability: scan results exported in standard format
- Right to rectification: user can dispute false positives; logged as corrections

## 5. Personally Identifiable Information (PII)

### 5.1 PII Detection and Handling

The scanner detects but never stores PII:

**Detected PII Patterns:**
- Email addresses in code comments or strings
- API keys, credentials, tokens
- Phone numbers embedded in code
- Social Security numbers or similar identifiers
- Names and addresses in test data
- Database connection strings with credentials

**Handling Procedure:**
1. Detect presence of PII patterns
2. Flag in scan results as "PII detected: <category>"
3. Report to operator that human review recommended
4. DO NOT capture or log the actual PII content
5. Immediately delete any detected content from memory
6. Log only the fact that PII was present, not the content

### 5.2 PII Operator Guidance

**When PII is Detected:**
- Scan results include alert: "This code contains credentials or PII"
- Operator should review code directly in their secure environment
- Never transmit the code to external services if PII is present
- Use local scanning model if PII is detected
- Recommend removing PII before production deployment

**Operator Controls:**
- Ability to scan locally without any data transmission
- Ability to exclude folders containing known PII (test data directories)
- Ability to disable telemetry if PII in repository structure itself
- Fallback to offline mode if PII detection triggers

### 5.3 Credential and Secret Handling

**Secrets Never Collected:**
- API keys are never captured in scan results
- Database passwords are never logged
- OAuth tokens are never stored
- SSH keys are never transmitted

**Detection Methodology:**
- Pattern matching for common credential formats (AWS key prefix, Bearer tokens)
- Entropy analysis for password-like strings
- Vendor-specific secret detection (GitHub, Stripe, Twilio formats)

## 6. Data Privacy Practices

### 6.1 Privacy by Design

**Principles:**
1. **Local-first scanning:** Code analyzed on user's infrastructure by default
2. **No transmission without consent:** Cloud features opt-in only
3. **Minimization:** Only necessary data collected and stored
4. **Purpose limitation:** Data used only for stated compliance purpose
5. **Anonymization:** Telemetry data stripped of identifiers
6. **Encryption:** All data in transit and at rest

### 6.2 Data Anonymization

**Anonymization Procedure:**
- User IDs: hashed with salt; cannot be reversed
- Company names: replaced with company size category (startup, SME, enterprise)
- File paths: stripped to directory depth only
- Code snippets: converted to abstract syntax tree representation
- Timestamps: rounded to day-level for aggregated metrics

**Anonymized Data Uses:**
- Model performance benchmarking
- Vulnerability pattern research
- Framework adoption analysis
- Compliance trend reporting

### 6.3 Encryption Standards

**Data In Transit:**
- TLS 1.3 minimum for all network communication
- Certificate pinning for critical endpoints
- Perfect forward secrecy enabled

**Data At Rest:**
- AES-256 encryption for stored scan results
- Database-level encryption for audit chain
- Key management via AWS KMS or HashiCorp Vault
- Separate encryption keys per customer for enterprise

### 6.4 User Privacy Controls

**Available Controls:**
- Local-only mode: all processing on user's machine
- Data retention override: request deletion before standard period
- Telemetry opt-out: disable analytics collection
- Anonymization settings: choose anonymization level
- Audit log access: view own compliance records

## 7. Compliance and Oversight

### 7.1 Data Protection Compliance

**Applicable Regulations:**
- GDPR (EU data protection regulation)
- CCPA/CPRA (California data privacy)
- LGPD (Brazil data protection)
- Enterprise data protection agreements (customer NDAs)

**Compliance Measures:**
- Data Protection Impact Assessment (DPIA) completed
- Privacy policy available at all time
- Data Processing Agreements signed with customers
- Regular privacy audits by external firm
- Incident response plan for data breaches

### 7.2 Audit and Accountability

**Audit Logging:**
- All data access logged to immutable audit chain
- Audit logs retained 7 years
- Quarterly audit log reviews
- Anomaly detection for unusual access patterns

**Governance:**
- Data Governance Committee meets monthly
- Privacy impact assessments for new features
- Regular training on data handling procedures
- Incident response procedures documented and tested

### 7.3 Breach Response

**Incident Response Timeline:**
- Immediate: Isolate affected systems; log incident
- 24 hours: Initial assessment; identify affected users
- 72 hours: Notification to affected users and regulators (if required)
- 7 days: Root cause analysis and containment plan
- 30 days: Remediation plan and communications

**Communication:**
- Transparent notification to affected users
- Details of what data was accessed
- Steps to protect themselves
- Monitoring for misuse of their data

## 8. Data Governance Accountability

**Data Governance Owner:** Chief Compliance Officer
**Review Schedule:** Quarterly review; annual comprehensive audit
**Contact:** compliance@airblackbox.dev
**Last Updated:** 2026-01-15
**Next Review:** 2026-04-15
