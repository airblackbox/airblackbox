"""
US State AI Law Scanner - checks for Colorado, Illinois, California, and Texas requirements.

Each check maps to a specific state law and section. Checks are designed to fire
for ANY AI system (not just hiring-specific), unlike the existing hiring-context
checks in code_scanner.py which only activate for employment AI.

Laws covered:
  - Colorado SB 26-189 (AI consumer protections) - effective Jan 1, 2027;
    replaced SB 24-205, which was repealed before it ever took effect
  - Illinois HB 3773 (AI Video Interview Act extension) - effective Jan 1, 2026
  - California FEHA ADS regulations (employment automated-decision systems) - effective Oct 1, 2025
  - California SB 942 (AI Transparency Act) - effective Jan 1, 2026
  - California ADMT Regulations (Automated Decision-Making Technology) - effective Jan 1, 2027
  - Texas RAIGA (Responsible AI Governance Act) - HB 1709, effective Sep 1, 2025

Check numbering uses article=17 to separate from the existing article=16 hiring checks.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class USFinding:
    """A single US state law compliance finding."""
    law: str           # e.g., "Colorado SB 26-189"
    section: str       # statutory cite where stable, duty label otherwise
    name: str
    status: str        # "pass", "warn", "fail"
    evidence: str
    detection: str = "auto"
    fix_hint: str = ""
    files: list = field(default_factory=list)
    deadline: str = ""  # e.g., "2026-02-01"


# ─────────────────────────────────────────────
# Colorado SB 26-189 (AI consumer protections)
# Effective: Jan 1, 2027
# Replaced SB 24-205 (repealed before taking
# effect). Surviving duties: pre-use consumer
# notice, adverse-outcome explanation within 30
# days, correction rights, meaningful human
# review. The duty-of-care, impact-assessment,
# and risk-management-program duties are gone.
# ─────────────────────────────────────────────

def check_colorado_disclosure(file_contents: dict, scan_path: str) -> USFinding:
    """Colorado SB 26-189: pre-use consumer notice.

    Deployers must tell consumers, before use, that an AI system is being
    used to make or substantially support a consequential decision.
    """
    disclosure_patterns = [
        r"ai_disclosure", r"ai_notice", r"automated_decision.*notice",
        r"consumer_disclosure", r"transparency_notice",
        r"disclosure_text", r"disclosure_message",
        r"notify.*(?:ai|automated|algorithm)", r"inform.*(?:ai|automated)",
        r"(?:ai|automated).*(?:notice|disclosure|inform|notify)",
        r"decision_disclosure", r"system_disclosure",
    ]
    combined = "|".join(disclosure_patterns)

    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="Colorado SB 26-189", section="Pre-use consumer notice",
            name="CO: Consumer AI disclosure",
            status="pass",
            evidence=f"AI disclosure mechanism detected in {len(hits)} file(s)",
            deadline="2027-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="Colorado SB 26-189", section="Pre-use consumer notice",
        name="CO: Consumer AI disclosure",
        status="fail",
        evidence="No consumer AI disclosure mechanism found. Colorado SB 26-189 requires notifying consumers before an AI system makes or substantially supports a consequential decision.",
        fix_hint="Add ai_disclosure() or transparency_notice() that informs users an AI system is involved in the decision, delivered before the decision is made",
        deadline="2027-01-01",
    )


def check_colorado_adverse_explanation(file_contents: dict, scan_path: str) -> USFinding:
    """Colorado SB 26-189: adverse-outcome explanation.

    On request, deployers must explain an adverse consequential decision
    within 30 days - which in practice requires decision records with a
    rationale captured at decision time, not reconstructed later.
    """
    explain_patterns = [
        r"adverse_(?:action|outcome|decision)",
        r"decision_(?:rationale|reason|explanation|log)",
        r"explanation.*(?:decision|outcome|adverse)",
        r"(?:decision|outcome).*explanation",
        r"reason.*(?:rejection|denial|adverse)",
        r"(?:rejection|denial).*reason",
        r"audit_(?:trail|chain|log)", r"decision_record",
        r"rationale", r"why_(?:rejected|denied|decided)",
    ]
    combined = "|".join(explain_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="Colorado SB 26-189", section="Adverse-outcome explanation (30 days)",
            name="CO: Adverse-decision explanation",
            status="pass",
            evidence=f"Decision-rationale/explanation records detected in {len(hits)} file(s)",
            deadline="2027-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="Colorado SB 26-189", section="Adverse-outcome explanation (30 days)",
        name="CO: Adverse-decision explanation",
        status="fail",
        evidence="No decision-rationale records found. Colorado SB 26-189 gives consumers a right to an explanation of an adverse AI-supported decision within 30 days - impossible to honor without a rationale recorded at decision time.",
        fix_hint="Record each consequential decision with its rationale in a tamper-evident log (e.g. AuditChain) so a 30-day explanation request can be answered from contemporaneous records",
        deadline="2027-01-01",
    )


def check_colorado_correction_rights(file_contents: dict, scan_path: str) -> USFinding:
    """Colorado SB 26-189: correction rights and meaningful human review.

    Consumers can correct inaccurate personal data behind an adverse
    decision and get meaningful human review of it.
    """
    report_patterns = [
        r"correct.*(?:data|record|information)",
        r"(?:data|record).*correction",
        r"appeal.*(?:ai|algorithm|decision)",
        r"grievance.*(?:ai|algorithm)",
        r"dispute.*(?:ai|automated|algorithm)",
        r"human_review.*request", r"request.*human_review",
        r"human_in_the_loop", r"human_oversight", r"human_approval",
        r"opt.?out.*(?:ai|automated)", r"(?:ai|automated).*opt.?out",
    ]
    combined = "|".join(report_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="Colorado SB 26-189", section="Correction rights + human review",
            name="CO: Correction rights + human review",
            status="pass",
            evidence=f"Correction/appeal/human-review mechanism detected in {len(hits)} file(s)",
            deadline="2027-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="Colorado SB 26-189", section="Correction rights + human review",
        name="CO: Correction rights + human review",
        status="fail",
        evidence="No correction or human-review mechanism found. Colorado SB 26-189 requires letting consumers correct inaccurate data behind an adverse decision and obtain meaningful human review of it.",
        fix_hint="Add a correction/appeal path for AI-driven decisions that routes to a named human reviewer, and record the review in the audit trail",
        deadline="2027-01-01",
    )


# ─────────────────────────────────────────────
# Illinois HB 3773 (AI Video Interview Act ext.)
# Effective: Jan 1, 2026
# Applies to: employers using AI in hiring
# ─────────────────────────────────────────────

def check_illinois_employee_notification(file_contents: dict, scan_path: str) -> USFinding:
    """Illinois HB 3773: Employee AI notification requirement.

    Employers must notify employees and applicants when AI is used
    in employment decisions, and provide a description of the AI's
    purpose and the data it collects.
    """
    notify_patterns = [
        r"employee.*(?:notice|notify|notification|disclosure).*(?:ai|algorithm)",
        r"(?:ai|algorithm).*(?:notice|notify|notification|disclosure).*employee",
        r"applicant.*(?:notice|notify|notification).*(?:ai|algorithm)",
        r"candidate.*(?:notice|notify|notification|disclosure)",
        r"hiring.*(?:notice|notify|disclosure|transparency)",
        r"ai_hiring_notice", r"aedt_notice",  # NYC LL144 term also used
        r"interview.*(?:ai|algorithm).*(?:notice|consent|disclosure)",
        r"video.*(?:ai|algorithm).*(?:notice|consent)",
    ]
    combined = "|".join(notify_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="Illinois HB 3773", section="Sec. 5/2-2",
            name="IL: Employee AI notification",
            status="pass",
            evidence=f"Employee/applicant AI notification mechanism detected in {len(hits)} file(s)",
            deadline="2026-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="Illinois HB 3773", section="Sec. 5/2-2",
        name="IL: Employee AI notification",
        status="fail",
        evidence="No employee AI notification mechanism found. Illinois requires notifying employees/applicants when AI is used in employment decisions, including the AI's purpose and data collected.",
        fix_hint="Add employee_ai_notice() that discloses: AI is being used, what data it analyzes, the purpose of the AI analysis, and how to request human review",
        deadline="2026-01-01",
    )


# ─────────────────────────────────────────────
# California FEHA ADS regulations
# Cal. Code Regs. tit. 2 (CRD), eff. Oct 1, 2025
# Applies to: employers using automated-decision
# systems in employment decisions. Requires
# anti-bias testing evidence and 4-year retention
# of ADS records (inputs, outputs, criteria).
# ─────────────────────────────────────────────

def check_california_feha_ads(file_contents: dict, scan_path: str) -> USFinding:
    """California FEHA ADS: bias testing + 4-year record retention.

    Using an ADS in employment decisions can itself be evidence of
    discrimination unless the employer can show anti-bias testing; ADS
    records must be retained for four years.
    """
    feha_patterns = [
        r"bias_(?:test|audit|check|analysis)",
        r"(?:test|audit|check).*bias",
        r"adverse_impact", r"disparate_impact", r"four_fifths",
        r"selection_(?:rate|criteria)",
        r"retention.*(?:polic|period|year)",
        r"(?:record|data)_retention",
        r"fairness_(?:test|metric|audit)",
    ]
    combined = "|".join(feha_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="California FEHA ADS", section="Cal. Code Regs. tit. 2 (ADS rules)",
            name="CA: FEHA ADS bias testing + retention",
            status="pass",
            evidence=f"Bias-testing and/or record-retention patterns detected in {len(hits)} file(s)",
            deadline="2025-10-01",
            files=hits[:3],
        )

    return USFinding(
        law="California FEHA ADS", section="Cal. Code Regs. tit. 2 (ADS rules)",
        name="CA: FEHA ADS bias testing + retention",
        status="fail",
        evidence="No bias-testing or ADS record-retention evidence found. California FEHA regulations treat untested automated-decision systems in employment as discrimination exposure and require 4-year retention of ADS records.",
        fix_hint="Add bias/adverse-impact testing for employment ADS outputs and retain ADS records (inputs, outputs, selection criteria) for 4 years - the evidence bundle's retention floor matches this",
        deadline="2025-10-01",
    )


# ─────────────────────────────────────────────
# California SB 942 (AI Transparency Act)
# Effective: Jan 1, 2026
# Applies to: generative AI providers with 1M+
# monthly users (or licensed by such providers)
# ─────────────────────────────────────────────

def check_california_sb942_transparency(file_contents: dict, scan_path: str) -> USFinding:
    """California SB 942: AI-generated content transparency.

    Providers must offer tools to detect AI-generated content,
    including latent disclosure (watermarking/metadata) and
    manifest disclosure (visible labeling).
    """
    transparency_patterns = [
        r"ai_generated.*(?:label|tag|mark|watermark|disclosure|metadata)",
        r"(?:watermark|c2pa|content_credentials|provenance).*(?:ai|generated)",
        r"content.*(?:authenticity|provenance|origin)",
        r"synthetic.*(?:label|tag|disclosure|detect)",
        r"generated.*(?:label|tag|disclosure|metadata)",
        r"(?:label|tag|mark).*(?:ai_generated|ai.generated|machine.generated)",
        r"c2pa", r"content_credentials", r"content_authenticity",
        r"ai_watermark", r"digital_watermark",
    ]
    combined = "|".join(transparency_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="California SB 942", section="Sec. 22757",
            name="CA: AI content transparency",
            status="pass",
            evidence=f"AI-generated content labeling/watermarking detected in {len(hits)} file(s)",
            deadline="2026-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="California SB 942", section="Sec. 22757",
        name="CA: AI content transparency",
        status="fail",
        evidence="No AI-generated content labeling found. California SB 942 requires tools to identify AI-generated content (watermarking, metadata, visible labels).",
        fix_hint="Add AI content provenance: C2PA content credentials, watermarking, or metadata tagging for AI-generated outputs",
        deadline="2026-01-01",
    )


# ─────────────────────────────────────────────
# California ADMT (Automated Decision-Making Tech)
# CCPA regulations, effective: Jan 1, 2027
# Applies to: businesses using automated decision
# technology for significant decisions
# ─────────────────────────────────────────────

def check_california_admt(file_contents: dict, scan_path: str) -> USFinding:
    """California ADMT: Pre-use notice and opt-out requirement.

    Businesses must provide a pre-use notice before using ADMT
    for significant decisions, and honor consumer opt-out requests.
    """
    admt_patterns = [
        r"pre.?use.*notice", r"admt.*notice", r"automated.*decision.*notice",
        r"opt.?out.*(?:automated|ai|algorithm|admt)",
        r"(?:automated|ai|algorithm|admt).*opt.?out",
        r"consumer.*(?:opt.?out|choice|consent).*(?:automated|ai)",
        r"right.*(?:opt.?out|refuse).*(?:automated|ai|algorithm)",
        r"human.*alternative", r"manual.*alternative",
        r"decline.*(?:automated|ai)", r"(?:automated|ai).*decline",
    ]
    combined = "|".join(admt_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    if hits:
        return USFinding(
            law="California ADMT", section="CCPA Reg. 7030-7031",
            name="CA: ADMT pre-use notice + opt-out",
            status="pass",
            evidence=f"ADMT notice and/or opt-out mechanism detected in {len(hits)} file(s)",
            deadline="2027-01-01",
            files=hits[:3],
        )

    return USFinding(
        law="California ADMT", section="CCPA Reg. 7030-7031",
        name="CA: ADMT pre-use notice + opt-out",
        status="fail",
        evidence="No ADMT pre-use notice or opt-out mechanism found. California CCPA regulations require pre-use notice before automated decision-making and consumer opt-out rights.",
        fix_hint="Add pre_use_notice() before ADMT processing, plus opt_out() that routes to a human decision-maker as alternative",
        deadline="2027-01-01",
    )


# ─────────────────────────────────────────────
# Texas RAIGA (Responsible AI Governance Act)
# HB 1709, effective: Sep 1, 2025
# Applies to: deployers of high-risk AI systems
# in Texas
# ─────────────────────────────────────────────

def check_texas_registration(file_contents: dict, scan_path: str) -> USFinding:
    """Texas RAIGA Sec. 3: AI system inventory/registration.

    Deployers must maintain an inventory of high-risk AI systems
    and make it available to the AG upon request.
    """
    inventory_patterns = [
        r"ai_inventory", r"ai_registry", r"ai_register",
        r"system_inventory", r"model_inventory", r"model_registry",
        r"ai_catalog", r"model_catalog",
        r"deployed_models", r"model_deployment.*(?:log|register|track)",
        r"(?:register|inventory|catalog).*(?:ai|model|algorithm)",
    ]
    combined = "|".join(inventory_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    # Also check for AI-BOM or model card docs
    inv_docs = [
        "AI_INVENTORY.md", "ai_inventory.md", "AI_REGISTRY.md",
        "MODEL_REGISTRY.md", "model_registry.md", "AI_BOM.md",
    ]
    has_inv_doc = any(os.path.exists(os.path.join(scan_path, f)) for f in inv_docs)

    if has_inv_doc or hits:
        evidence = "AI system inventory document found" if has_inv_doc else f"AI inventory/registry code patterns in {len(hits)} file(s)"
        return USFinding(
            law="Texas RAIGA (HB 1709)", section="Sec. 3",
            name="TX: AI system inventory",
            status="pass",
            evidence=evidence,
            deadline="2025-09-01",
        )

    return USFinding(
        law="Texas RAIGA (HB 1709)", section="Sec. 3",
        name="TX: AI system inventory",
        status="fail",
        evidence="No AI system inventory or registry found. Texas RAIGA requires deployers to maintain an inventory of high-risk AI systems.",
        fix_hint="Create AI_INVENTORY.md listing deployed AI models, their purpose, risk level, and deployment date. Use air-blackbox discover for auto-detection.",
        deadline="2025-09-01",
    )


def check_texas_risk_management(file_contents: dict, scan_path: str) -> USFinding:
    """Texas RAIGA Sec. 4: Risk management and governance.

    Deployers must implement a risk management policy that includes
    governance, testing, and monitoring of high-risk AI systems.
    """
    governance_patterns = [
        r"ai_governance", r"ai_policy", r"responsible_ai",
        r"ai_risk.*(?:management|policy|framework)",
        r"(?:management|policy|framework).*ai_risk",
        r"model_governance", r"model_risk",
        r"ai_oversight", r"ai_compliance",
        r"governance_framework", r"risk_framework",
    ]
    combined = "|".join(governance_patterns)
    hits = [fp for fp, content in file_contents.items()
            if re.search(combined, content, re.IGNORECASE)]

    gov_docs = [
        "AI_GOVERNANCE.md", "ai_governance.md",
        "RESPONSIBLE_AI.md", "responsible_ai.md",
        "AI_RISK_POLICY.md", "RISK_MANAGEMENT.md",
    ]
    has_gov_doc = any(os.path.exists(os.path.join(scan_path, f)) for f in gov_docs)

    if has_gov_doc or hits:
        evidence = "AI governance document found" if has_gov_doc else f"AI governance/risk code patterns in {len(hits)} file(s)"
        return USFinding(
            law="Texas RAIGA (HB 1709)", section="Sec. 4",
            name="TX: Risk management policy",
            status="pass",
            evidence=evidence,
            deadline="2025-09-01",
        )

    return USFinding(
        law="Texas RAIGA (HB 1709)", section="Sec. 4",
        name="TX: Risk management policy",
        status="fail",
        evidence="No AI governance or risk management policy found. Texas RAIGA requires a risk management framework for high-risk AI systems.",
        fix_hint="Create AI_GOVERNANCE.md or RISK_MANAGEMENT.md documenting: governance structure, testing procedures, monitoring plan, incident response",
        deadline="2025-09-01",
    )


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def scan_us_laws(scan_path: str) -> List[USFinding]:
    """Run all US state law checks against a codebase.

    Returns a list of USFinding objects, one per check.
    Always returns all 9 checks (3 CO, 1 IL, 3 CA, 2 TX) regardless of
    codebase content.
    """
    # Read Python files
    file_contents = {}
    if os.path.isfile(scan_path) and scan_path.endswith(".py"):
        try:
            with open(scan_path, "r", encoding="utf-8", errors="ignore") as f:
                file_contents[scan_path] = f.read()
        except Exception:
            pass
    elif os.path.isdir(scan_path):
        skip_dirs = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".eggs", "site-packages", ".tox",
            ".mypy_cache", ".pytest_cache",
        }
        for root, dirs, files in os.walk(scan_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith(".egg-info")]
            for fname in files:
                if fname.endswith(".py"):
                    fp = os.path.join(root, fname)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                            file_contents[fp] = f.read(16000)
                    except Exception:
                        pass
            if len(file_contents) >= 200:
                break

    doc_path = scan_path
    if os.path.isfile(scan_path):
        doc_path = os.path.dirname(os.path.abspath(scan_path)) or "."

    findings = [
        # Colorado SB 26-189 (3 checks)
        check_colorado_disclosure(file_contents, doc_path),
        check_colorado_adverse_explanation(file_contents, doc_path),
        check_colorado_correction_rights(file_contents, doc_path),
        # Illinois HB 3773 (1 check)
        check_illinois_employee_notification(file_contents, doc_path),
        # California FEHA ADS (1 check)
        check_california_feha_ads(file_contents, doc_path),
        # California SB 942 (1 check)
        check_california_sb942_transparency(file_contents, doc_path),
        # California ADMT (1 check)
        check_california_admt(file_contents, doc_path),
        # Texas RAIGA (2 checks)
        check_texas_registration(file_contents, doc_path),
        check_texas_risk_management(file_contents, doc_path),
    ]

    return findings


def findings_to_dicts(findings: List[USFinding]) -> list:
    """Convert USFinding list to the dict format engine.py expects."""
    return [
        {
            "name": f"{f.name}",
            "status": f.status,
            "evidence": f.evidence,
            "detection": f.detection,
            "fix_hint": f.fix_hint,
            "tier": "static",
            "law": f.law,
            "section": f.section,
            "deadline": f.deadline,
        }
        for f in findings
    ]
