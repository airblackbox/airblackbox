# Risk Assessment for AIR Blackbox Compliance Scanner

## Executive Summary

This document identifies and evaluates key risks associated with the AIR Blackbox EU AI Act compliance scanner. The assessment covers operational, technical, and security risks with documented mitigation strategies.

## Risk Register

| Risk ID | Risk Description | Category | Likelihood | Impact | Severity | Mitigation Strategy |
|---------|------------------|----------|------------|--------|----------|---------------------|
| R-001 | False Positives in Compliance Detection | Technical | High | Medium | High | Implement confidence scoring; require human review for low-confidence results; maintain false positive baseline metrics |
| R-002 | False Negatives in Compliance Detection | Technical | Medium | High | High | Regular model retraining; test against known compliance violations; use ensemble methods with rule-based checks |
| R-003 | LLM Model Hallucination | Technical | High | High | High | Use retrieval-augmented generation (RAG) with canonical EU AI Act text; add confidence thresholds; implement fact-checking layer |
| R-004 | Prompt Injection Attacks Against Scanner | Security | Medium | High | High | Sanitize input code; use separate inference environments; implement input validation; log all scan requests |
| R-005 | Data Privacy Breach During Scanning | Security | Medium | High | High | Scan in isolated environments; never transmit PII to external services; implement data minimization; use local models when possible |
| R-006 | Dependency on Third-Party LLM Providers | Operational | Medium | Medium | Medium | Maintain fallback local models; implement rate limiting; establish SLAs; monitor provider reliability |
| R-007 | Incompatibility with Novel ML Frameworks | Technical | High | Medium | Medium | Maintain framework documentation; enable human override; implement scanner extensibility; community feedback loops |
| R-008 | Misclassification of Edge Cases | Technical | Medium | Medium | Medium | Document known edge cases; maintain case library; require escalation for edge case patterns; continuous monitoring |
| R-009 | Audit Trail Tampering | Security | Low | High | Medium | Immutable audit chain; cryptographic signatures; external audit log storage; access controls on audit records |
| R-010 | Scanning Performance Degradation | Operational | Low | Medium | Low | Implement caching; optimize model inference; horizontal scaling; performance baseline monitoring |

## Detailed Risk Analysis

### R-001: False Positives in Compliance Detection

**Description:** The scanner may incorrectly flag compliant code as non-compliant, leading to false alerts and reduced trust.

**Root Cause:** Model uncertainty, edge cases in EU AI Act interpretation, context limitations in static analysis.

**Likelihood:** High; the fine-tuned model may be overly conservative or misinterpret complex patterns.

**Impact:** Medium; false positives create alert fatigue but do not cause immediate harm if human review is enforced.

**Mitigation:**
- Implement confidence scoring on all classifications
- Require human review for any detection below 85% confidence threshold
- Maintain baseline metrics of false positive rates by article and framework
- User feedback loop to identify and retrain on false positive patterns
- Integration with operator override system

### R-002: False Negatives in Compliance Detection

**Description:** The scanner fails to detect actual compliance violations, creating false confidence.

**Root Cause:** Model blind spots, novel attack patterns, framework-specific compliance issues not seen during training.

**Likelihood:** Medium; likely to occur with new frameworks or novel code patterns.

**Impact:** High; undetected violations could result in regulatory non-compliance and legal liability.

**Mitigation:**
- Regular model retraining with newly discovered violations
- Test suite of known compliance violations; every release must detect 100% of test cases
- Ensemble approach combining fine-tuned model with rule-based checks
- Continuous monitoring of compliance violations in deployed systems
- Community reporting mechanism for suspected false negatives

### R-003: LLM Model Hallucination

**Description:** The model generates plausible but incorrect compliance analysis or cites non-existent EU AI Act provisions.

**Root Cause:** Large language models sometimes generate false information when uncertain or when training data is limited.

**Likelihood:** High; hallucination is common in LLM-based systems.

**Impact:** High; incorrect compliance guidance could lead to regulatory violations.

**Mitigation:**
- Use retrieval-augmented generation (RAG) with canonical EU AI Act text
- Enforce grounding in primary legal sources; model cannot cite articles outside Articles 9-15
- Implement fact-checking layer that validates all article citations
- Confidence threshold enforcement; uncertain analysis is flagged for human review
- Regular testing with adversarial prompts to identify hallucination patterns

### R-004: Prompt Injection Attacks Against Scanner

**Description:** Malicious code embedded in scanned files could manipulate the scanner to produce false results.

**Root Cause:** LLM systems are vulnerable to prompt injection when processing untrusted input.

**Likelihood:** Medium; requires sophisticated attack but is known technique.

**Impact:** High; successful injection could compromise scan integrity or enable evasion.

**Mitigation:**
- Input sanitization: remove or escape prompt-like patterns in code before analysis
- Separate inference environment; scanner runs in isolated container
- Input validation against code syntax; reject malformed inputs
- Comprehensive logging of all scan requests and results
- Regular red team testing of prompt injection resilience

### R-005: Data Privacy Breach During Scanning

**Description:** Personally identifiable information (PII) or confidential code could be exposed during scanning.

**Root Cause:** Transmission to external services, logging of sensitive data, insufficient access controls.

**Likelihood:** Medium; depends on deployment architecture and operational practices.

**Impact:** High; PII breach has legal and reputational consequences.

**Mitigation:**
- All scanning occurs in isolated, secure environments
- Local inference models used for sensitive codebases; no transmission to external services
- Strict data minimization: scanner detects PII patterns but never stores full content
- Encryption of scan results in transit and at rest
- Access controls on audit logs and intermediate results
- Regular privacy impact assessments

### R-006: Dependency on Third-Party LLM Providers

**Description:** Scanner relies on external LLM services which could become unavailable or change terms of service.

**Root Cause:** Operational dependency on cloud-based model providers.

**Likelihood:** Medium; provider outages are intermittent; terms of service changes are infrequent but possible.

**Impact:** Medium; affects scanner availability and may impact compliance monitoring timelines.

**Mitigation:**
- Maintain fallback local model (air-compliance model) for offline operation
- Implement rate limiting to avoid provider quota issues
- Establish SLAs with providers; monitor availability
- Diversify providers where possible
- Regular testing of fallback functionality

### R-007: Incompatibility with Novel ML Frameworks

**Description:** New machine learning frameworks or architectures may not be recognized by the scanner.

**Root Cause:** Training data is limited to frameworks as of training date; new frameworks emerge constantly.

**Likelihood:** High; new ML frameworks are developed regularly.

**Impact:** Medium; scanner cannot assess compliance of novel architectures; requires manual review.

**Mitigation:**
- Comprehensive framework documentation in scanner; enables pattern matching for common frameworks
- Human override mechanism; operators can flag framework-specific concerns
- Extensible scanner architecture; support for custom compliance rules per framework
- Community feedback loop; users report framework gaps
- Regular updates as new frameworks gain adoption

### R-008: Misclassification of Edge Cases

**Description:** Complex code patterns or unusual implementations may be misclassified as compliant or non-compliant.

**Root Cause:** Limited training coverage of edge cases; complexity of EU AI Act interpretation in boundary conditions.

**Likelihood:** Medium; occurs sporadically as new patterns are encountered.

**Impact:** Medium; incorrect classification but may be caught in human review or follow-up audits.

**Mitigation:**
- Document known edge cases and their correct classifications
- Maintain case library of edge case patterns; use in model retraining
- Require escalation for patterns matching known edge cases
- Continuous monitoring; track edge cases observed in production
- Regular case reviews to identify patterns requiring retraining

### R-009: Audit Trail Tampering

**Description:** Malicious actor could modify audit records to hide non-compliance or falsify scan results.

**Root Cause:** Insufficient controls on audit data; insufficient cryptographic protection.

**Likelihood:** Low; requires privileged access; detected by external auditors.

**Impact:** High; audit trail is critical for regulatory compliance.

**Mitigation:**
- Immutable audit chain; use append-only logs
- Cryptographic signatures on all audit records; prevent undetected modification
- External audit log storage; logs replicated to immutable storage service
- Access controls on audit records; restrict to authorized users
- Regular integrity verification; hash chain validation

### R-010: Scanning Performance Degradation

**Description:** Scanner performance may degrade under high load or with large codebases.

**Root Cause:** Model inference latency; inefficient architecture; insufficient infrastructure.

**Likelihood:** Low; can be addressed through optimization and scaling.

**Impact:** Medium; scanner becomes unavailable during critical compliance checks.

**Mitigation:**
- Implement caching for repeated patterns and similar code
- Optimize model inference; use quantization and distillation
- Horizontal scaling; deploy multiple scanner instances
- Performance baseline monitoring; alert on degradation
- Regular load testing to identify bottlenecks

## Risk Monitoring

All risks are monitored through:
- Monthly risk review meetings
- Automated monitoring dashboards for technical risks
- Quarterly assessment updates
- Incident reporting and root cause analysis
- External audit feedback integration
