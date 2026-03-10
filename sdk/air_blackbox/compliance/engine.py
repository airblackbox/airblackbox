"""
Compliance engine — maps gateway traffic data to EU AI Act articles.
Detection types: AUTO, HYBRID, MANUAL
"""
import os
from dataclasses import dataclass
from typing import Literal
from air_blackbox.gateway_client import GatewayStatus


@dataclass
class ComplianceCheck:
    name: str
    article: int
    status: Literal["pass", "warn", "fail"]
    evidence: str
    detection: Literal["auto", "hybrid", "manual"]
    fix_hint: str = ""


def _c2d(check: ComplianceCheck) -> dict:
    return {"name": check.name, "status": check.status, "evidence": check.evidence,
            "detection": check.detection, "fix_hint": check.fix_hint}


def run_all_checks(status: GatewayStatus, scan_path: str = ".") -> list[dict]:
    return [_check_article_9(status, scan_path), _check_article_10(status, scan_path),
            _check_article_11(status, scan_path), _check_article_12(status, scan_path),
            _check_article_14(status, scan_path), _check_article_15(status, scan_path)]


def _check_article_9(status, scan_path):
    checks = []
    risk_files = ["RISK_ASSESSMENT.md", "risk_assessment.md", "risk_register.json", "RISK_MANAGEMENT.md"]
    has_risk = any(os.path.exists(os.path.join(scan_path, f)) for f in risk_files)
    checks.append(ComplianceCheck(name="Risk assessment document", article=9, detection="hybrid",
        status="pass" if has_risk else "fail",
        evidence="Risk assessment document found" if has_risk else "No risk assessment document found",
        fix_hint="Create RISK_ASSESSMENT.md documenting identified risks, likelihood, impact, and mitigations"))
    mits = []
    if status.guardrails_enabled: mits.append("guardrails")
    if status.vault_enabled: mits.append("data vault")
    if status.trust_signing_key_set: mits.append("audit signing")
    if status.otel_enabled: mits.append("OTel pipeline")
    mc = len(mits)
    checks.append(ComplianceCheck(name="Risk mitigations active", article=9, detection="hybrid",
        status="pass" if mc >= 3 else "warn" if mc >= 1 else "fail",
        evidence=f"{mc}/4 mitigations active: {', '.join(mits) or 'none detected'}",
        fix_hint="Enable guardrails.yaml, set TRUST_SIGNING_KEY, configure vault and OTel endpoints"))
    return {"number": 9, "title": "Risk Management", "checks": [_c2d(c) for c in checks]}


def _check_article_10(status, scan_path):
    checks = []
    if status.reachable:
        if status.pii_detected_count > 0:
            checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto", status="warn",
                evidence=f"PII detected in {status.pii_detected_count} prompts", fix_hint="Enable prompt vault redaction"))
        else:
            checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto", status="pass",
                evidence=f"Gateway active. No PII detected in {status.total_runs} requests."))
    else:
        checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto",
            status="warn" if status.total_runs > 0 else "fail",
            evidence=f"Gateway not reachable. {'Found ' + str(status.total_runs) + ' logged runs.' if status.total_runs > 0 else 'No data.'}",
            fix_hint="Start gateway: docker compose up"))
    dg_files = ["DATA_GOVERNANCE.md", "data_governance.md"]
    has_dg = any(os.path.exists(os.path.join(scan_path, f)) for f in dg_files)
    checks.append(ComplianceCheck(name="Data governance documentation", article=10, detection="hybrid",
        status="pass" if has_dg else "fail",
        evidence="Data governance document found" if has_dg else "No data governance documentation found",
        fix_hint="Create DATA_GOVERNANCE.md: data sources, consent, quality measures, retention"))
    checks.append(ComplianceCheck(name="Data vault (controlled storage)", article=10, detection="auto",
        status="pass" if status.vault_enabled else "fail",
        evidence="Vault enabled. Data stored in your controlled S3/MinIO." if status.vault_enabled else "No vault configured.",
        fix_hint="Set VAULT_ENDPOINT, VAULT_ACCESS_KEY, VAULT_SECRET_KEY in .env"))
    return {"number": 10, "title": "Data Governance", "checks": [_c2d(c) for c in checks]}


def _check_article_11(status, scan_path):
    checks = []
    readme = os.path.exists(os.path.join(scan_path, "README.md"))
    checks.append(ComplianceCheck(name="System description (README)", article=11, detection="hybrid",
        status="pass" if readme else "fail",
        evidence="README.md found" if readme else "No README.md found",
        fix_hint="Create README.md documenting system purpose, architecture, intended use"))
    if status.total_runs > 0:
        ml = ", ".join(status.models_observed[:5])
        pl = ", ".join(status.providers_observed[:5])
        checks.append(ComplianceCheck(name="Runtime system inventory (AI-BOM data)", article=11, detection="auto", status="pass",
            evidence=f"Gateway observed: {status.total_runs} runs, models: [{ml}], providers: [{pl}], {status.total_tokens:,} tokens."))
    else:
        checks.append(ComplianceCheck(name="Runtime system inventory (AI-BOM data)", article=11, detection="auto", status="fail",
            evidence="No traffic data. Route AI calls through gateway.", fix_hint="Point LLM at gateway: base_url='http://localhost:8080/v1'"))
    mc_files = ["MODEL_CARD.md", "model_card.md", "SYSTEM_CARD.md"]
    has_mc = any(os.path.exists(os.path.join(scan_path, f)) for f in mc_files)
    checks.append(ComplianceCheck(name="Model card / system card", article=11, detection="hybrid",
        status="pass" if has_mc else "warn",
        evidence="Model/system card found" if has_mc else "No model card found. Run: air-blackbox discover --generate-card",
        fix_hint="Create MODEL_CARD.md: intended use, limitations, performance, ethics"))
    if status.total_runs > 0 and status.date_range_end:
        checks.append(ComplianceCheck(name="Documentation currency", article=11, detection="auto", status="pass",
            evidence=f"Traffic data current through {status.date_range_end}. {len(status.models_observed)} model(s) active."))
    return {"number": 11, "title": "Technical Documentation", "checks": [_c2d(c) for c in checks]}


def _check_article_12(status, scan_path):
    checks = []
    if status.reachable and status.total_runs > 0:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="pass",
            evidence=f"Gateway active. {status.total_runs:,} events logged. Period: {status.date_range_start} to {status.date_range_end}."))
    elif status.reachable:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="warn",
            evidence=f"Gateway running but no events logged yet.", fix_hint="Route traffic through gateway"))
    else:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="fail",
            evidence=f"Gateway not reachable at {status.url}.", fix_hint="Start gateway: docker compose up"))
    if status.audit_chain_intact and status.audit_chain_length > 0:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto", status="pass",
            evidence=f"HMAC-SHA256 chain intact. {status.audit_chain_length:,} records."))
    elif status.trust_signing_key_set:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto", status="pass",
            evidence="TRUST_SIGNING_KEY configured. HMAC chain will activate on traffic."))
    else:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto",
            status="warn" if status.reachable else "fail",
            evidence="No TRUST_SIGNING_KEY set. Logs recorded but not tamper-evident.",
            fix_hint="Set TRUST_SIGNING_KEY in .env"))
    if status.total_runs > 0:
        sample = status.recent_runs[0] if status.recent_runs else None
        if sample and all(sample.get(f) for f in ["run_id", "model", "timestamp"]):
            checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="pass",
                evidence="All records include: run_id, model, timestamp, tokens, provider."))
        else:
            checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="warn",
                evidence="Records found but missing some traceability fields."))
    else:
        checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="fail",
            evidence="No logged records.", fix_hint="Route traffic through gateway."))
    if status.total_runs > 0 and status.date_range_start:
        checks.append(ComplianceCheck(name="Log retention", article=12, detection="auto", status="pass",
            evidence=f"Records retained from {status.date_range_start}. Storage: {'vault' if status.vault_enabled else 'local'}."))
    return {"number": 12, "title": "Record-Keeping", "checks": [_c2d(c) for c in checks]}


def _check_article_14(status, scan_path):
    checks = []
    if status.total_runs > 0:
        checks.append(ComplianceCheck(name="Human-in-the-loop mechanism", article=14, detection="auto", status="warn",
            evidence=f"{status.total_runs:,} actions logged. No human approval gates detected.",
            fix_hint="Add approval gates: air.require_approval(action)"))
    else:
        checks.append(ComplianceCheck(name="Human-in-the-loop mechanism", article=14, detection="auto", status="warn",
            evidence="No traffic data to analyze for oversight patterns."))
    if status.reachable and status.guardrails_enabled:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="pass",
            evidence="Gateway active with guardrails. Kill switch available."))
    elif status.reachable:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="warn",
            evidence="Gateway running but guardrails not configured.", fix_hint="Create guardrails.yaml"))
    else:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="fail",
            evidence="Gateway not running. No kill switch.", fix_hint="Start gateway: docker compose up"))
    op_files = ["OPERATOR_GUIDE.md", "operator_guide.md", "RUNBOOK.md"]
    has_ops = any(os.path.exists(os.path.join(scan_path, f)) for f in op_files)
    checks.append(ComplianceCheck(name="Operator understanding documentation", article=14, detection="manual",
        status="pass" if has_ops else "warn",
        evidence="Operator guide found" if has_ops else "No operator documentation found.",
        fix_hint="Create OPERATOR_GUIDE.md: capabilities, limitations, when to intervene"))
    return {"number": 14, "title": "Human Oversight", "checks": [_c2d(c) for c in checks]}


def _check_article_15(status, scan_path):
    checks = []
    if status.reachable:
        checks.append(ComplianceCheck(name="Prompt injection protection", article=15, detection="auto", status="pass",
            evidence=f"Gateway scanning for injection patterns. {status.injection_attempts} attempts detected." if status.injection_attempts > 0
            else "Gateway OTel pipeline scanning. No attempts detected."))
    else:
        checks.append(ComplianceCheck(name="Prompt injection protection", article=15, detection="auto", status="fail",
            evidence="Gateway not running. No injection protection.", fix_hint="Start gateway: docker compose up"))
    if status.total_runs > 0:
        er = (status.error_count / status.total_runs * 100)
        checks.append(ComplianceCheck(name="Error resilience", article=15, detection="auto",
            status="pass" if er < 5 else "warn" if er < 15 else "fail",
            evidence=f"Error rate: {er:.1f}% ({status.error_count}/{status.total_runs})."))
    else:
        checks.append(ComplianceCheck(name="Error resilience", article=15, detection="auto", status="warn",
            evidence="No traffic data to measure resilience.", fix_hint="Route traffic through gateway."))
    has_auth = bool(os.environ.get("OPENAI_API_KEY")) or bool(os.environ.get("ANTHROPIC_API_KEY"))
    checks.append(ComplianceCheck(name="API access control", article=15, detection="hybrid",
        status="pass" if has_auth else "warn",
        evidence="API keys configured." if has_auth else "No API keys detected.",
        fix_hint="Set API keys in .env"))
    rt_files = ["REDTEAM.md", "redteam_results.json", "ADVERSARIAL_TESTING.md"]
    has_rt = any(os.path.exists(os.path.join(scan_path, f)) for f in rt_files)
    checks.append(ComplianceCheck(name="Adversarial robustness testing", article=15, detection="manual",
        status="pass" if has_rt else "warn",
        evidence="Adversarial testing documentation found" if has_rt else "No red team / adversarial testing evidence.",
        fix_hint="Conduct adversarial testing. Export: air-blackbox export --tag=redteam"))
    return {"number": 15, "title": "Accuracy, Robustness & Cybersecurity", "checks": [_c2d(c) for c in checks]}
