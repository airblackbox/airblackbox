"""
GDPR-specific compliance scanner for AI agent codebases.

Checks Python code for GDPR-relevant patterns:
  - Data Processing Records (Art. 30)
  - Consent Management (Art. 6/7)
  - Right to Erasure (Art. 17)
  - Data Minimization (Art. 5(1)(c))
  - Data Retention Policies (Art. 5(1)(e))
  - Cross-Border Transfer Safeguards (Art. 44-49)
  - Data Protection Impact Assessment (Art. 35)

These checks complement the EU AI Act scanner. Together
they cover both AI governance and data protection.
"""

import os
import re
from typing import List

from air_blackbox.compliance.code_scanner import (
    CodeFinding,
    _find_python_files,
    _rel,
)


def scan_gdpr(scan_path: str) -> List[CodeFinding]:
    """Run all GDPR checks against a codebase."""
    py_files = _find_python_files(scan_path)
    if not py_files:
        return []

    file_contents = {}
    for fp in py_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                file_contents[fp] = f.read()
        except Exception:
            continue

    findings: List[CodeFinding] = []
    findings.extend(_check_consent_management(file_contents, scan_path))
    findings.extend(_check_data_minimization(file_contents, scan_path))
    findings.extend(_check_right_to_erasure(file_contents, scan_path))
    findings.extend(_check_data_retention(file_contents, scan_path))
    findings.extend(_check_cross_border_transfer(file_contents, scan_path))
    findings.extend(_check_dpia_patterns(file_contents, scan_path))
    findings.extend(_check_processing_records(file_contents, scan_path))
    findings.extend(_check_breach_notification(file_contents, scan_path))
    return findings


def _check_consent_management(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 6/7: Lawful basis and consent management."""
    strong_patterns = [
        r"consent_manage", r"lawful_basis", r"legal_basis",
        r"data_subject_consent", r"opt_in", r"opt_out",
        r"consent_record", r"withdraw_consent", r"revoke_consent",
        r"consent_gate", r"ConsentGate", r"require_consent",
        r"gdpr.*consent", r"consent.*gdpr",
    ]
    moderate_patterns = [
        r"\bconsent\b", r"user_agreement", r"terms_accepted",
        r"privacy_accepted", r"data_agreement",
    ]
    strong = "|".join(strong_patterns)
    moderate = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=6, name="GDPR consent management",
            status="pass",
            evidence=f"Consent management found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=6, name="GDPR consent management",
            status="warn",
            evidence=f"Consent references in {len(moderate_hits)} file(s) but no structured management",
            fix_hint="Add explicit consent gates with lawful_basis tracking per GDPR Art. 6",
        )]
    return [CodeFinding(
        article=6, name="GDPR consent management",
        status="warn",
        evidence="No consent management patterns detected for data processing",
        fix_hint="Implement consent tracking before processing personal data (GDPR Art. 6/7)",
    )]


def _check_data_minimization(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 5(1)(c): Only collect data that is necessary."""
    patterns = [
        r"data_minimiz", r"minimal_data", r"necessary_data",
        r"strip_unnecessary", r"select_fields", r"field_filter",
        r"allowed_fields", r"required_fields_only",
        r"redact_unnecessary", r"purpose_limitation",
        r"collect_only", r"data_scope",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=5, name="GDPR data minimization",
            status="pass",
            evidence=f"Data minimization patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=5, name="GDPR data minimization",
        status="warn",
        evidence="No data minimization patterns detected",
        fix_hint="Filter data to only what is necessary before sending to LLM (GDPR Art. 5(1)(c))",
    )]


def _check_right_to_erasure(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 17: Right to erasure (right to be forgotten)."""
    patterns = [
        r"right_to_erasure", r"right_to_be_forgotten",
        r"delete_user_data", r"erase_personal", r"purge_user",
        r"data_deletion", r"gdpr_delete", r"forget_user",
        r"erasure_request", r"deletion_request",
        r"remove_personal_data", r"anonymize_user",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=17, name="GDPR right to erasure",
            status="pass",
            evidence=f"Erasure/deletion patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=17, name="GDPR right to erasure",
        status="warn",
        evidence="No right-to-erasure implementation detected",
        fix_hint="Add ability to delete all personal data for a user (GDPR Art. 17)",
    )]


def _check_data_retention(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 5(1)(e): Storage limitation."""
    patterns = [
        r"retention_polic", r"data_retention", r"ttl",
        r"expire_after", r"auto_delete", r"cleanup_old",
        r"purge_expired", r"max_age", r"storage_limit",
        r"retention_period", r"keep_for", r"delete_after_days",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=5, name="GDPR data retention policy",
            status="pass",
            evidence=f"Retention/TTL patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=5, name="GDPR data retention policy",
        status="warn",
        evidence="No data retention or TTL policies detected",
        fix_hint="Set retention periods for personal data storage (GDPR Art. 5(1)(e))",
    )]


def _check_cross_border_transfer(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 44-49: International data transfers."""
    patterns = [
        r"data_transfer", r"cross_border", r"data_residency",
        r"eu_only", r"region_lock", r"geographic_restrict",
        r"transfer_impact", r"adequacy_decision",
        r"standard_contractual", r"scc", r"binding_corporate",
        r"data_localiz", r"sovereign",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    # Also check for cloud provider region configs
    region_patterns = [
        r"region\s*=\s*['\"]eu", r"location\s*=\s*['\"]europe",
        r"AWS_REGION.*eu-", r"AZURE.*europe",
    ]
    region_combined = "|".join(region_patterns)
    region_hits = [
        fp for fp, c in file_contents.items()
        if re.search(region_combined, c, re.IGNORECASE) and fp not in hits
    ]
    if hits:
        return [CodeFinding(
            article=44, name="GDPR cross-border transfer safeguards",
            status="pass",
            evidence=f"Transfer safeguard patterns in {len(hits)} file(s)",
        )]
    if region_hits:
        return [CodeFinding(
            article=44, name="GDPR cross-border transfer safeguards",
            status="warn",
            evidence=f"EU region config in {len(region_hits)} file(s) but no explicit transfer safeguards",
            fix_hint="Add explicit data residency controls for LLM API calls (GDPR Art. 44-49)",
        )]
    return [CodeFinding(
        article=44, name="GDPR cross-border transfer safeguards",
        status="warn",
        evidence="No cross-border data transfer controls detected",
        fix_hint="Ensure LLM API calls respect data residency requirements (GDPR Art. 44-49)",
    )]


def _check_dpia_patterns(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 35: Data Protection Impact Assessment."""
    patterns = [
        r"dpia", r"impact_assessment", r"privacy_impact",
        r"risk_assessment.*data", r"data.*risk_assessment",
        r"protection_impact", r"pia_report",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=35, name="GDPR data protection impact assessment",
            status="pass",
            evidence=f"DPIA patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=35, name="GDPR data protection impact assessment",
        status="warn",
        evidence="No DPIA references detected",
        fix_hint="Document a Data Protection Impact Assessment for AI processing (GDPR Art. 35)",
    )]


def _check_processing_records(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 30: Records of processing activities."""
    patterns = [
        r"processing_record", r"processing_activit",
        r"data_register", r"processing_log",
        r"record_of_processing", r"ropa",
        r"data_inventory", r"processing_purpose",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=30, name="GDPR records of processing",
            status="pass",
            evidence=f"Processing record patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=30, name="GDPR records of processing",
        status="warn",
        evidence="No records of processing activities detected",
        fix_hint="Maintain a register of data processing activities (GDPR Art. 30)",
    )]


def _check_breach_notification(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """GDPR Art. 33/34: Breach notification."""
    patterns = [
        r"breach_notif", r"data_breach", r"incident_report",
        r"breach_detect", r"security_incident",
        r"notify_authority", r"notify_dpa",
        r"breach_log", r"incident_response",
    ]
    combined = "|".join(patterns)
    hits = [
        fp for fp, c in file_contents.items()
        if re.search(combined, c, re.IGNORECASE)
    ]
    if hits:
        return [CodeFinding(
            article=33, name="GDPR breach notification",
            status="pass",
            evidence=f"Breach notification patterns in {len(hits)} file(s)",
        )]
    return [CodeFinding(
        article=33, name="GDPR breach notification",
        status="warn",
        evidence="No breach notification or incident response patterns detected",
        fix_hint="Implement breach detection and 72-hour notification process (GDPR Art. 33)",
    )]
