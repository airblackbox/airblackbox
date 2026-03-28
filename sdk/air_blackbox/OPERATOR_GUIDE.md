# AIR Blackbox Operator Guide

This guide is for compliance officers, security engineers, and operations teams responsible for running and interpreting AIR Blackbox compliance scans in production environments.

## 1. System Overview and Capabilities

### What AIR Blackbox Does

AIR Blackbox automatically scans Python code to identify potential EU AI Act compliance violations. It analyzes code against six key articles (9, 10, 11, 12, 14, 15) and provides:

- Violation detection with confidence scores (0.0 to 1.0)
- Severity classification (critical, high, medium, low)
- Specific code locations (file path, line numbers)
- Remediation guidance for each violation
- Immutable audit trail of all scanning activities

### Key Constraints and Limitations

**What AIR Blackbox Cannot Do:**
- Assess business context or determine if AI Act compliance is legally required for your system
- Make final compliance determinations (requires human judgment and legal review)
- Evaluate non-code compliance requirements (governance structures, accountability systems, etc.)
- Scan non-Python code or infrastructure configurations
- Detect violations requiring multi-file or cross-service analysis
- Assess real-time system behavior or model performance in production

**Accuracy Profile:**
- Detects 92% of true violations (high recall)
- False positive rate approximately 5% at 0.7 confidence threshold (medium precision)
- Confidence scores are calibrated; use them to guide human review effort
- Strongest performance on common frameworks (PyTorch, TensorFlow); weaker on niche tools

**Applicable to EU AI Act High-Risk AI Systems:**
- Systems that make decisions affecting fundamental rights or freedoms
- Systems that significantly impact employment, education, or public services
- Systems that could amplify discrimination or bias
- Not applicable to low-risk AI systems (e.g., spam filters, autocomplete)
- Not applicable to general-purpose AI models without deployment context

## 2. Operating Procedures

### 2.1 Deployment Modes

AIR Blackbox can be deployed in three modes depending on your infrastructure and security requirements:

**Local Mode (Default)**
- Scanner runs entirely on user's machine
- No network communication
- No data transmission outside your organization
- Suitable for: sensitive code, air-gapped environments, initial assessment
- Setup time: 5 minutes (install, download model)
- Cost: Minimal (one-time model download)

```bash
air-blackbox scan --local /path/to/code
```

**Gateway Mode (Enterprise)**
- Scanner runs on centralized compliance gateway
- Single source of truth for scan results
- Audit logs aggregated in central location
- Role-based access controls
- Suitable for: organizations with multiple teams, regulatory compliance tracking
- Setup time: 1-2 weeks (deployment, integration)
- Cost: Infrastructure + licensing

```bash
air-blackbox scan --gateway https://compliance.company.com --api-key XXXXX /path/to/code
```

**Hybrid Mode**
- Local scanning for code review; gateway for final compliance reporting
- Balances speed (local) with auditability (gateway)
- Suitable for: organizations with both development and compliance teams
- Setup time: 1 week

```bash
# Local scan during development
air-blackbox scan /path/to/code

# Report results to central gateway after code review
air-blackbox report --gateway https://compliance.company.com scan_id
```

### 2.2 Scan Initiation

**Manual Scans**

Trigger scans on demand for code review or audit purposes:

```bash
# Single file scan
air-blackbox scan ai_model.py

# Directory scan
air-blackbox scan --recursive my_project/

# With options
air-blackbox scan --framework pytorch --confidence-threshold 0.75 ml_system.py
```

**Automated Scans**

Integrate into CI/CD pipeline for continuous compliance monitoring:

```yaml
# GitHub Actions example
- name: Scan for compliance violations
  run: air-blackbox scan --recursive . --fail-on critical,high
```

**Continuous Monitoring**

Monitor deployed systems for compliance drift:

```bash
# Scan every 6 hours; alert on new violations
air-blackbox monitor --watch /app/code --interval 21600 --alert-channel slack
```

### 2.3 Result Interpretation

AIR Blackbox outputs violations with these key fields:

```json
{
  "article": "12",
  "severity": "critical",
  "confidence": 0.94,
  "line": 42,
  "pattern": "missing_documentation",
  "remediation": "Add docstring documenting training data source"
}
```

**Interpreting Confidence Scores:**

| Confidence | Interpretation | Recommended Action |
|------------|-----------------|-------------------|
| 0.9-1.0 | Very likely a violation | Accept and remediate |
| 0.8-0.89 | Likely a violation | Accept; prioritize in backlog |
| 0.7-0.79 | Probable violation | Human review required |
| 0.6-0.69 | Uncertain | Likely false positive; verify manually |
| <0.6 | Not reported | Filtered out; high false positive rate |

**Decision Framework:**

1. **Critical violations at 0.9+:** Immediate remediation required; block production deployment
2. **High violations at 0.8+:** Schedule remediation in current sprint; document mitigation
3. **Medium violations at 0.7+:** Add to backlog; remediate before next audit
4. **Low violations:** Informational; consider in future work planning
5. **Below 0.7 confidence:** Flag for human review; document decision rationale

### 2.4 Human Review Workflows

When to involve human compliance experts:

**Mandatory Human Review:**
- Any critical violations (regardless of confidence)
- Low-confidence detections (0.5-0.69 range)
- Violations in unfamiliar frameworks or architectures
- Conflicts between multiple violation detections
- Edge cases or novel code patterns

**Optional Human Review:**
- Violations flagged for business context assessment
- False positive confirmations to retrain model
- Complex remediation guidance requiring domain expertise
- Integration of scan results with broader compliance program

**Override Process:**

When operators determine a violation is a false positive:

```bash
# Mark as false positive in audit trail
air-blackbox override --scan-id scan_20260328_143022 \
  --violation-id v12_42_missing_doc \
  --reason "Documentation present in separate RISK_ASSESSMENT.md" \
  --override-type false_positive
```

This logs the override to the immutable audit chain. Always document reasoning for audit purposes.

## 3. Escalation Procedures

### 3.1 When to Escalate

**Escalate to Compliance Officer:**
- Critical violations cannot be resolved through code changes alone
- Business decisions required to determine if compliance is necessary
- Architectural changes needed to meet compliance requirements
- Questions about scope of compliance requirements

**Escalate to Legal/Regulatory:**
- Ambiguity in EU AI Act interpretation
- Questions about applicability to your specific system
- Requests for guidance on regulatory timelines or deadlines
- Potential regulatory violations or enforcement actions

**Escalate to Security/Infrastructure Team:**
- Vulnerabilities discovered during code analysis
- Potential supply chain risks (dependencies, third-party components)
- Data privacy concerns related to model training or deployment
- Production incidents related to model behavior

**Escalate to Product/Engineering Leadership:**
- Resource requirements for remediation exceed available capacity
- Remediation requires product roadmap changes
- Trade-offs between compliance and performance or functionality
- Timeline conflicts between compliance deadlines and other commitments

### 3.2 Escalation Template

When escalating issues, provide:

```
Escalation Summary:
- System/Component: [name]
- Violation Type: [Article X; confidence Y]
- Issue Description: [specific problem]
- Business Impact: [why this matters]
- Recommended Action: [what needs to happen]
- Timeline: [when decision is needed]
- Owner: [who should decide]
```

### 3.3 Escalation SLAs

| Severity | Triage Time | Decision Time | Resolution Time |
|----------|------------|--------------|-----------------|
| Critical | 2 hours | 24 hours | 7 days |
| High | 1 day | 3 days | 30 days |
| Medium | 3 days | 7 days | 90 days |
| Low | 1 week | 30 days | Next quarter |

## 4. Result Analysis and Reporting

### 4.1 Analyzing Scan Results

**Step 1: Severity Triage**
Sort violations by severity; address critical and high first.

**Step 2: Confidence Assessment**
For medium-confidence detections (0.7-0.79), perform manual code review to confirm or reject.

**Step 3: Root Cause Analysis**
Determine why each violation exists:
- Missing from initial design (gap)
- Implemented but not documented (visibility)
- Intentionally omitted due to business decision (exemption)
- Framework limitation (not addressable)

**Step 4: Remediation Planning**
For each violation, identify:
- Owner: who will fix it
- Timeline: when it will be fixed
- Approach: code changes, documentation, architecture change, or exemption request
- Test plan: how to verify compliance after fix

**Step 5: Compliance Status**
Document compliance status:
- Compliant: no violations or all violations remediated
- Non-compliant with plan: violations with approved remediation schedule
- Non-compliant: violations without remediation plan

### 4.2 Generating Reports

**Executive Report (for leadership)**

```bash
air-blackbox report --format executive \
  --scan-id scan_20260328_143022 \
  --output compliance_report_q1.pdf
```

Includes: summary statistics, risk heat map, remediation timeline, resource requirements.

**Detailed Report (for compliance officer)**

```bash
air-blackbox report --format detailed \
  --scan-id scan_20260328_143022 \
  --include-recommendations \
  --include-audit-trail \
  --output detailed_compliance_assessment.json
```

Includes: all violations with line numbers, remediation guidance, confidence scores, audit trail.

**Audit Trail Report (for regulators)**

```bash
air-blackbox report --format audit \
  --time-range 2026-01-01 to 2026-03-28 \
  --include-cryptographic-signatures \
  --export-for-external-audit \
  --output audit_trail_export.zip
```

Includes: all scans, results, human decisions, cryptographic proofs of integrity.

### 4.3 Benchmarking and Metrics

Track compliance trends over time:

```bash
# Monthly compliance dashboard
air-blackbox metrics --period monthly --output dashboard.json

# Metrics include:
# - Total violations detected
# - Violations by article
# - False positive rate
# - Mean time to remediation
# - Percentage of critical violations resolved
```

## 5. Kill Switch and Emergency Procedures

### 5.1 When to Use Kill Switch

The kill switch is a gateway control that can disable scanning immediately in emergency situations:

**Use kill switch when:**
- Scanning is causing production system degradation
- Security incident suspected in scanner itself
- False positive epidemic from model update
- Regulatory investigation requires halting all scans

**Do NOT use kill switch for:**
- Hiding violations from audit
- Disagreement with scan results
- Delaying remediation (use override process instead)

### 5.2 Activating Kill Switch

```bash
# Disable scanner immediately
air-blackbox gateway --kill-switch activate

# Verify kill switch is active
air-blackbox gateway --status
# Output: Scanner status: DISABLED (kill switch active)

# Re-enable scanner after investigation
air-blackbox gateway --kill-switch deactivate
```

Kill switch activation is logged to immutable audit trail with timestamp and operator ID. All scans are paused immediately; in-flight scans are gracefully shut down.

### 5.3 Post-Kill Switch Procedures

After activating kill switch:

1. Immediately notify compliance leadership and relevant stakeholders
2. Document reason for kill switch activation
3. Investigate root cause (security incident, model failure, etc.)
4. Implement fix or mitigation
5. Test fix in staging environment
6. Deactivate kill switch with approval from two authorized officers
7. Perform verification scan to confirm normal operation
8. Document lesson learned

## 6. Guardrails and Controls

### 6.1 Built-in Guardrails

AIR Blackbox includes safety mechanisms:

**Input Validation:**
- Rejects files >100MB (timeout prevention)
- Validates Python syntax before analysis
- Detects and blocks prompt injection attempts
- Rate limiting to prevent abuse

**Model Safeguards:**
- Confidence thresholds filter low-confidence predictions
- RAG grounding prevents hallucination about EU AI Act articles
- Fallback to rule-based checking for high-risk patterns
- Automatic detection of model degradation

**Audit Safeguards:**
- Immutable audit chain prevents tampering
- Cryptographic signatures on all records
- Access controls on sensitive results
- Automatic redaction of detected PII

### 6.2 Operator Overrides

Operators can override model predictions when they conflict with human judgment:

```bash
# Override specific violation as false positive
air-blackbox override --violation-id v12_42 \
  --status false_positive \
  --notes "Reviewed by John Smith; documentation present in README.md"

# Override specific violation as addressed
air-blackbox override --violation-id v9_18 \
  --status remediated \
  --remediation-link https://github.com/company/repo/commit/abc123
```

All overrides are logged with:
- Operator ID and timestamp
- Original scan result and override decision
- Justification and supporting evidence
- Approval chain (if required)

### 6.3 Approval Workflows

For organizations with compliance governance:

```bash
# Create remediation plan requiring approval
air-blackbox plan create --scan-id scan_20260328 \
  --owner engineering-lead \
  --approver compliance-officer \
  --deadline 2026-05-28 \
  --status pending-approval

# Review and approve plan
air-blackbox plan approve --plan-id plan_001 \
  --approver-id john.smith@company.com \
  --approved-date 2026-03-28
```

## 7. Troubleshooting

### Common Issues and Solutions

**Problem: High false positive rate on new codebase**

Solutions:
- Reduce confidence threshold from 0.7 to 0.6 temporarily
- Review patterns with domain expert to understand false positives
- Create custom rules for framework-specific patterns
- Retrain model with your codebase examples

**Problem: Scanning takes excessive time**

Solutions:
- Use `--exclude-dirs` to skip non-essential directories
- Enable caching for repeated scans
- Use gateway mode for batch processing
- Reduce file size limits if scanning test directories

**Problem: Model seems to hallucinate about articles**

Solutions:
- Verify model version is current (air-compliance-v2)
- Check that RAG grounding is enabled
- Review confidence scores; filter results <0.7
- Report issue to support for investigation

**Problem: Audit trail showing unexpected entries**

Solutions:
- Verify no one is accessing audit chain
- Check for kill switch activity or system errors
- Review access logs for unauthorized actions
- Contact support if integrity concern

### Support Resources

- **Documentation:** https://air-blackbox.dev/docs/operator
- **Troubleshooting:** https://air-blackbox.dev/docs/troubleshooting
- **Email:** operators@airblackbox.dev
- **Slack:** #air-blackbox-operators (enterprise only)

## 8. Best Practices

### 8.1 Scanning Cadence

**Recommended Schedule:**
- Development: on every commit (automated in CI/CD)
- Code review: before merging to main branch
- Pre-release: full system scan before production deployment
- Production: monthly for deployed systems
- Incident response: scan immediately after security incident

### 8.2 Documentation

Always document:
- Why compliance is required for your system (business rationale)
- Which articles apply to your system (scoping analysis)
- Known limitations and trade-offs
- Approval records for all overrides and exemptions
- Remediation plans with timelines

### 8.3 Team Training

Ensure operators understand:
- EU AI Act Articles 9-15 basics
- How to interpret confidence scores
- When human review is required
- Escalation procedures
- Kill switch usage and limitations

Schedule quarterly training updates as EU AI Act guidance evolves.

### 8.4 Integration with Other Systems

AIR Blackbox integrates with:
- Git/GitHub/GitLab for CI/CD integration
- Jira/Linear for remediation tracking
- Slack for alerts and notifications
- PagerDuty for escalation
- ServiceNow for compliance tracking

Set up integrations early to enable automated workflows.

## 9. Compliance and Auditing

### 9.1 Audit Preparation

When preparing for regulatory audit:

1. Export full audit trail (last 7 years)
2. Generate executive summary showing compliance status
3. Document all critical and high violations and their remediation
4. Prepare override justifications with supporting evidence
5. Show control testing results
6. Document any instances kill switch was used

```bash
air-blackbox audit-export \
  --format zip \
  --include-signatures \
  --time-range 2019-01-01 to 2026-03-28 \
  --output audit_evidence.zip
```

### 9.2 Regulatory Reporting

AIR Blackbox generates compliance evidence suitable for regulatory submissions:

- Detailed compliance assessment per article
- Evidence of monitoring and testing
- Records of remediation actions
- Governance documentation

## 10. Reference

### Command Quick Reference

```bash
# Scan operations
air-blackbox scan <path>                    # Single scan
air-blackbox scan --recursive <path>        # Directory scan
air-blackbox monitor --watch <path>         # Continuous monitoring
air-blackbox report --scan-id <id>          # Generate report

# Result management
air-blackbox override <violation-id>        # Override decision
air-blackbox plan create                    # Create remediation plan
air-blackbox plan approve                   # Approve remediation plan

# Audit operations
air-blackbox audit-export                   # Export audit trail
air-blackbox metrics                        # View compliance metrics
air-blackbox gateway --kill-switch activate # Emergency stop

# Configuration
air-blackbox config set <key> <value>       # Set configuration
air-blackbox config show                    # View configuration
```

**Last Updated:** January 2026
**Operator Guide Version:** 2.0
