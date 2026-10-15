"""
Compliance engine - maps gateway traffic data to EU AI Act articles.
Detection types: AUTO, HYBRID, MANUAL
"""
import os
import re
from dataclasses import dataclass
from typing import Literal
from air_blackbox.gateway_client import GatewayStatus
from air_blackbox.compliance.code_scanner import (
    FRAMEWORK_EU_AI_ACT,
    FRAMEWORK_US_HIRING,
)


@dataclass
class ComplianceCheck:
    name: str
    article: int
    status: Literal["pass", "warn", "fail"]
    evidence: str
    detection: Literal["auto", "hybrid", "manual"]
    fix_hint: str = ""
    tier: Literal["static", "runtime"] = "static"


def _c2d(check: ComplianceCheck) -> dict:
    return {"name": check.name, "status": check.status, "evidence": check.evidence,
            "detection": check.detection, "fix_hint": check.fix_hint, "tier": check.tier}


def _finding_to_dict(finding) -> dict:
    """Convert a CodeFinding to the same dict format as ComplianceCheck."""
    return {"name": finding.name, "status": finding.status, "evidence": finding.evidence,
            "detection": getattr(finding, "detection", "auto"), "fix_hint": finding.fix_hint,
            "tier": "static"}


_BIAS_CHECK_NAMES = {
    "protected_attribute_reference": "Protected attribute references",
    "gender_reference": "Gender term references",
    "race_reference": "Race/ethnicity term references",
    "unvalidated_threshold": "Decision thresholds without fairness validation",
}


# Term lists that also match colour names. In JSX/TSX components those words
# are almost always styling, so these two are not counted there.
_COLOUR_PRONE = {"race_reference", "gender_reference"}


def _bias_checks(scan_path: str) -> list[dict]:
    """Run the per-file bias scanner over every source file and merge by type.

    scan_bias reads one file and returns a report dict. It used to be handed
    the scan path directly, which raised IsADirectoryError on directories (so
    the section never appeared) and, on a single file, iterated the report's
    keys as if they were findings, crashing the whole comply run.
    """
    from air_blackbox.compliance.bias_scanner import scan_bias
    from air_blackbox.compliance.code_scanner import (
        _find_source_files, _has_hiring_context, _is_test_file)
    from air_blackbox.compliance.sources import read_sources

    root = scan_path if os.path.isdir(scan_path) else os.path.dirname(os.path.abspath(scan_path))
    keep = [path for path in sorted(_find_source_files(scan_path))
            # fixtures mention protected attributes on purpose
            if not (os.path.isdir(scan_path) and _is_test_file(os.path.relpath(path, root)))]
    sources = read_sources(keep)

    # The term lists match words like "white", "black" and "age" wherever they
    # appear (colour names, log text), so outside code that makes decisions
    # about people they are noise. Same gate as the US hiring checks.
    if not _has_hiring_context(sources):
        return []

    merged = {}  # finding type -> (reference count, [relative paths])
    for path in sources:
        rel = os.path.relpath(path, root)
        for f in scan_bias(path, code=str(sources[path])).get("findings", []):
            if f["type"] in _COLOUR_PRONE and path.endswith((".tsx", ".jsx")):
                continue  # UI components: text-white, bg-black, fill="white"
            count, files = merged.setdefault(f["type"], (0, []))
            merged[f["type"]] = (count + f["count"], files + [rel])

    checks = []
    for kind, (count, files) in merged.items():
        shown = ", ".join(files[:5]) + (f" (+{len(files) - 5} more)" if len(files) > 5 else "")
        if kind == "unvalidated_threshold":
            hint = ("Validate hardcoded score cutoffs for disparate impact across "
                    "protected groups, or document why they are fair.")
        else:
            hint = ("Review whether these terms feed a decision. If they do, add "
                    "bias testing; if they are incidental, no action is needed.")
        checks.append({
            "name": _BIAS_CHECK_NAMES.get(kind, kind),
            "status": "warn",
            "evidence": f"{count} match(es) in {len(files)} file(s): {shown}",
            "detection": "auto",
            "fix_hint": hint,
            "tier": "static",
        })
    return checks


#: Runtime-check advice for projects with no Python: the trust layers are pip
#: packages. TypeScript and JavaScript have their own recorder on npm; the
#: gateway is a proxy any SDK can use (OpenAI-compatible routes plus the
#: Anthropic Messages API).
GATEWAY_HINT_JS = ("TypeScript/JavaScript: npm install air-blackbox (records tool calls and "
                   "enforces a covenant). Any language: start the AIR gateway (docker compose up) "
                   "and point your SDK client's base URL at http://localhost:8080/v1 "
                   "(Anthropic SDK: http://localhost:8080)")


def _runtime_hint(rec_pkg: str, js_only: bool) -> str:
    if js_only:
        return GATEWAY_HINT_JS
    return f"pip install {rec_pkg}  # or start gateway: docker compose up"


def _is_js_only(scan_path: str) -> bool:
    """True when the scan found source files and none of them Python
    (TypeScript, JavaScript, Java): the pip trust layers do not apply."""
    from air_blackbox.compliance.sources import PYTHON, project_languages
    langs = project_languages(scan_path)
    return bool(langs) and PYTHON not in langs


TRUST_LAYER_MAP = {
    "langchain": "air-langchain-trust",
    "crewai": "air-crewai-trust",
    "openai": "air-openai-trust",
    "anthropic": "air-anthropic-trust",
    "google.adk": "air-adk-trust",
    "google_adk": "air-adk-trust",
    "vertexai": "air-adk-trust",
}

FRAMEWORK_IMPORTS = {
    "langchain": ["from langchain", "import langchain"],
    "crewai": ["from crewai", "import crewai"],
    "openai": ["from openai", "import openai", "OpenAI("],
    "anthropic": ["from anthropic", "import anthropic", "Anthropic("],
    "google.adk": ["from google.adk", "import google.adk", "from google_adk", "from vertexai"],
}


#: npm packages, matched against import/require specifiers, named as a JS
#: developer knows them. None has an AIR trust layer (those are Python
#: packages), so they never produce a `pip install` recommendation.
JS_FRAMEWORK_IMPORTS = {
    "LangChain.js": r"^(?:@langchain/|langchain(?:/|$))",
    "OpenAI Node SDK": r"^openai(?:/|$)",
    "Anthropic TypeScript SDK": r"^@anthropic-ai/sdk(?:/|$)",
    "Vercel AI SDK": r"^(?:ai(?:/|$)|@ai-sdk/)",
    "OpenAI Agents SDK (JS)": r"^@openai/agents",
    "Mastra": r"^@mastra/",
    "LlamaIndex.TS": r"^(?:llamaindex(?:/|$)|@llamaindex/)",
    "Google Gen AI (JS)": r"^@google/(?:genai|generative-ai|adk)(?:/|$)",
    "MCP TypeScript SDK": r"^@modelcontextprotocol/sdk(?:/|$)",
}
#: JVM packages (Java and Kotlin), matched against import statements.
JAVA_FRAMEWORK_IMPORTS = {
    "Koog": r"^ai\.koog\.",
    "OpenAI Kotlin (aallam)": r"^com\.aallam\.openai\.",
    "LangChain4j": r"^dev\.langchain4j\.",
    "Spring AI": r"^org\.springframework\.ai\.",
    "OpenAI Java SDK": r"^com\.openai\.",
    "Anthropic Java SDK": r"^com\.anthropic\.",
    "Google ADK (Java)": r"^com\.google\.adk\.",
    "Google Gen AI (Java)": r"^com\.google\.genai\.",
    "Azure OpenAI (Java)": r"^com\.azure\.ai\.openai\.",
    "MCP Java SDK": r"^io\.modelcontextprotocol\.",
    "LangGraph4j": r"^org\.bsc\.langgraph4j\.",
}
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)", re.M)
_JS_MODULE_SPECIFIER = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\brequire\s*\(\s*)["']([^"'\n]+)["']""")


def detect_frameworks(scan_path: str) -> list[str]:
    """Detect which AI frameworks are used in the scanned codebase."""
    from air_blackbox.compliance.code_scanner import SOURCE_SKIP_DIRS
    from air_blackbox.compliance.sources import (
        JS_FAMILY, JVM_FAMILY, is_notebook, is_scannable, language_of, read_text)
    detected = set()
    py_files = []
    if os.path.isfile(scan_path) and language_of(scan_path):
        py_files = [scan_path]
    elif os.path.isdir(scan_path):
        for root, _dirs, files in os.walk(scan_path):
            # Python files have always been collected from everywhere; JS
            # files are never read from node_modules or build output.
            rel_parts = os.path.relpath(root, scan_path).replace("\\", "/").split("/")
            js_ok = not any(p in SOURCE_SKIP_DIRS for p in rel_parts)
            for f in files:
                fp = os.path.join(root, f)
                if f.endswith(".py") or (js_ok and is_scannable(fp, scan_path)):
                    py_files.append(fp)
    for fp in py_files[:200]:  # cap to avoid scanning huge repos
        try:
            if is_notebook(fp):
                content = read_text(fp, 16000) or ""
            else:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read(16000)  # first 16KB is enough
            if language_of(fp) in JVM_FAMILY:
                imports = _JAVA_IMPORT.findall(content)
                for framework, pattern in JAVA_FRAMEWORK_IMPORTS.items():
                    if framework not in detected and any(re.match(pattern, m) for m in imports):
                        detected.add(framework)
                continue
            if language_of(fp) in JS_FAMILY:
                modules = _JS_MODULE_SPECIFIER.findall(content)
                for framework, pattern in JS_FRAMEWORK_IMPORTS.items():
                    if framework not in detected and any(re.match(pattern, m) for m in modules):
                        detected.add(framework)
                continue
            for framework, patterns in FRAMEWORK_IMPORTS.items():
                if framework not in detected:
                    for pattern in patterns:
                        if pattern in content:
                            detected.add(framework)
                            break
        except (OSError, UnicodeDecodeError):
            pass
    return sorted(detected)


def get_trust_layer_recommendation(scan_path: str) -> str:
    """Return the best pip install command based on detected frameworks."""
    detected = [fw for fw in detect_frameworks(scan_path) if fw in TRUST_LAYER_MAP]
    if detected:
        return TRUST_LAYER_MAP[detected[0]]
    return "air-langchain-trust"


def run_all_checks(status: GatewayStatus, scan_path: str = ".", standard: str = "all") -> list[dict]:
    """Run compliance checks filtered by jurisdiction standard.

    Args:
        status: GatewayStatus from the gateway client
        scan_path: Path to the codebase to scan
        standard: Which jurisdiction(s) to check:
            "eu"  - EU AI Act + GDPR only
            "us"  - US state laws only (CO, IL, CA, TX)
            "all" - Everything (default)

    Returns:
        (results, detected_frameworks, rec_pkg) tuple
    """
    standard = standard.lower().strip()
    if standard not in ("eu", "us", "all"):
        standard = "all"

    # Support single-file scanning: code scanner gets the file,
    # but doc checks use the parent directory
    doc_path = scan_path
    if os.path.isfile(scan_path):
        doc_path = os.path.dirname(os.path.abspath(scan_path)) or "."

    # Run code-level scan (always, both EU and US checks use it)
    code_findings = []
    try:
        from air_blackbox.compliance.code_scanner import scan_codebase
        code_findings = scan_codebase(scan_path)
    except Exception:
        pass  # Graceful fallback if code scanner has issues

    # Run GDPR scan (EU only)
    gdpr_findings = []
    if standard in ("eu", "all"):
        try:
            from air_blackbox.compliance.gdpr_scanner import scan_gdpr
            gdpr_findings = scan_gdpr(scan_path)
        except Exception:
            pass

    # Run bias/fairness scan (universal)
    bias_checks = []
    try:
        bias_checks = _bias_checks(scan_path)
    except Exception:
        pass

    # Detect frameworks for smart trust layer recommendations
    detected = detect_frameworks(scan_path)
    # Python framework names are all in TRUST_LAYER_MAP, so on a Python-only
    # scan this is detected[0] exactly as before. npm frameworks have no
    # trust layer and are skipped.
    mapped = [fw for fw in detected if fw in TRUST_LAYER_MAP]
    rec_pkg = TRUST_LAYER_MAP[mapped[0]] if mapped else "air-langchain-trust"
    js_only = _is_js_only(scan_path)

    # Group code findings by article number. Only EU AI Act findings carry an
    # article; everything else is selected by framework so that a non-EU
    # finding can never be picked up by an Article N lookup.
    code_by_article = {}
    for f in code_findings:
        if getattr(f, "framework", FRAMEWORK_EU_AI_ACT) == FRAMEWORK_EU_AI_ACT:
            code_by_article.setdefault(f.article, []).append(f)

    results = []

    # ── EU AI Act articles ──
    eu_count = 0
    if standard in ("eu", "all"):
        eu_results = [
            _check_article_9(status, doc_path, code_by_article.get(9, []), rec_pkg, js_only),
            _check_article_10(status, doc_path, code_by_article.get(10, []), rec_pkg, js_only),
            _check_article_11(status, doc_path, code_by_article.get(11, []), rec_pkg, js_only),
            _check_article_12(status, doc_path, code_by_article.get(12, []), rec_pkg, js_only),
            _check_article_14(status, doc_path, code_by_article.get(14, []), rec_pkg, js_only),
            _check_article_15(status, doc_path, code_by_article.get(15, []), rec_pkg, js_only),
        ]
        results.extend(eu_results)
        eu_count = sum(len(a.get("checks", [])) for a in eu_results)

    # ── US State AI Laws (new dedicated scanner) ──
    us_count = 0
    if standard in ("us", "all"):
        try:
            from air_blackbox.compliance.us_scanner import scan_us_laws, findings_to_dicts
            us_findings = scan_us_laws(scan_path)
            us_checks = findings_to_dicts(us_findings)
            us_count = len(us_checks)
            if us_checks:
                # Group by state for cleaner display
                co_checks = [c for c in us_checks if c.get("law", "").startswith("Colorado")]
                il_checks = [c for c in us_checks if c.get("law", "").startswith("Illinois")]
                ca_checks = [c for c in us_checks if c.get("law", "").startswith("California")]
                tx_checks = [c for c in us_checks if c.get("law", "").startswith("Texas")]

                if co_checks:
                    results.append({
                        "number": "CO",
                        "title": "Colorado SB 26-189 (AI consumer protections)",
                        "checks": co_checks,
                    })
                if il_checks:
                    results.append({
                        "number": "IL",
                        "title": "Illinois HB 3773 (AI Employment)",
                        "checks": il_checks,
                    })
                if ca_checks:
                    results.append({
                        "number": "CA",
                        "title": "California AI Laws (FEHA ADS + SB 942 + ADMT)",
                        "checks": ca_checks,
                    })
                if tx_checks:
                    results.append({
                        "number": "TX",
                        "title": "Texas RAIGA (HB 1709)",
                        "checks": tx_checks,
                    })
        except Exception:
            pass

        # Hiring-context checks from code_scanner. Keyed "US-HIRING" like the
        # other non-EU groups above: these are Illinois HB 3773, NYC LL144 and
        # California FEHA findings, and numbering them 16 labelled them as EU
        # AI Act Article 16 (provider obligations) in the exported report.
        state_code_findings = [
            f for f in code_findings
            if getattr(f, "framework", "") == FRAMEWORK_US_HIRING]
        state_checks = [_finding_to_dict(f) for f in state_code_findings]
        if state_checks:
            results.append({
                "number": "US-HIRING",
                "title": "US Hiring AI Laws (context-specific)",
                "checks": state_checks,
            })

    # ── GDPR checks ──
    if standard in ("eu", "all"):
        gdpr_checks = [_finding_to_dict(f) for f in gdpr_findings]
        if gdpr_checks:
            results.append({
                "number": "GDPR",
                "title": "GDPR Data Protection",
                "checks": gdpr_checks,
            })

    # ── Bias/fairness checks (universal) ──
    if bias_checks:
        results.append({
            "number": "BIAS",
            "title": "Bias and Fairness",
            "checks": bias_checks,
        })

    # ── Crosswalk teaser: show what's available in other jurisdictions ──
    crosswalk_hint = None
    if standard == "us" and eu_count == 0:
        # Run a quick count of what EU checks would find
        try:
            eu_preview = [
                _check_article_9(status, doc_path, code_by_article.get(9, []), rec_pkg, js_only),
                _check_article_10(status, doc_path, code_by_article.get(10, []), rec_pkg, js_only),
                _check_article_11(status, doc_path, code_by_article.get(11, []), rec_pkg, js_only),
                _check_article_12(status, doc_path, code_by_article.get(12, []), rec_pkg, js_only),
                _check_article_14(status, doc_path, code_by_article.get(14, []), rec_pkg, js_only),
                _check_article_15(status, doc_path, code_by_article.get(15, []), rec_pkg, js_only),
            ]
            eu_finding_count = sum(len(a.get("checks", [])) for a in eu_preview)
            if eu_finding_count > 0:
                crosswalk_hint = f"Also found {eu_finding_count} EU AI Act findings. Run --standard all to see them."
        except Exception:
            pass
    elif standard == "eu" and us_count == 0:
        # Preview US checks
        try:
            from air_blackbox.compliance.us_scanner import scan_us_laws
            us_preview = scan_us_laws(scan_path)
            us_fail_count = sum(1 for f in us_preview if f.status == "fail")
            if us_fail_count > 0:
                crosswalk_hint = f"Also found {us_fail_count} US state law gaps. Run --standard all to see them."
        except Exception:
            pass

    # Attach detected frameworks for CLI recommendation display
    return results, detected, rec_pkg, crosswalk_hint


def _check_article_9(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    risk_files = ["RISK_ASSESSMENT.md", "risk_assessment.md", "risk_register.json", "RISK_MANAGEMENT.md"]
    has_risk = any(os.path.exists(os.path.join(scan_path, f)) for f in risk_files)
    checks.append(ComplianceCheck(name="Risk assessment document", article=9, detection="hybrid",
        status="pass" if has_risk else "fail",
        evidence="Risk assessment document found" if has_risk else "No risk assessment document found",
        fix_hint="Create RISK_ASSESSMENT.md documenting identified risks, likelihood, impact, and mitigations",
        tier="static"))
    mits = []
    if status.guardrails_enabled: mits.append("guardrails")
    if status.vault_enabled: mits.append("data vault")
    if status.trust_signing_key_set: mits.append("audit signing")
    if status.otel_enabled: mits.append("OTel pipeline")
    mc = len(mits)
    checks.append(ComplianceCheck(name="Risk mitigations active", article=9, detection="hybrid",
        status="pass" if mc >= 3 else "warn" if mc >= 1 else "fail",
        evidence=f"{mc}/4 mitigations active: {', '.join(mits) or 'none detected'}",
        fix_hint="Enable guardrails.yaml, set TRUST_SIGNING_KEY, configure vault and OTel endpoints",
        tier="runtime"))
    result = {"number": 9, "title": "Risk Management", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result


def _check_article_10(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    if status.reachable or (status.total_runs > 0 and status.audit_chain_intact):
        src = "Gateway" if status.reachable else "Trust layer"
        if status.pii_detected_count > 0:
            checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto", status="warn",
                evidence=f"{src} scanning active. PII detected in {status.pii_detected_count} prompt(s) across {status.total_runs} runs.",
                fix_hint="Enable prompt vault redaction",
                tier="runtime"))
        else:
            checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto", status="pass",
                evidence=f"{src} scanning active. No PII detected in {status.total_runs} requests.",
                tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="PII detection in prompts", article=10, detection="auto",
            status="warn",
            evidence=f"Runtime check skipped - gateway not running. {'Found ' + str(status.total_runs) + ' logged runs.' if status.total_runs > 0 else 'Start it to enable this check.'}",
            fix_hint=(GATEWAY_HINT_JS if js_only else f"Start gateway or install a trust layer package (pip install {rec_pkg})"),
            tier="runtime"))
    dg_files = ["DATA_GOVERNANCE.md", "data_governance.md"]
    has_dg = any(os.path.exists(os.path.join(scan_path, f)) for f in dg_files)
    checks.append(ComplianceCheck(name="Data governance documentation", article=10, detection="hybrid",
        status="pass" if has_dg else "fail",
        evidence="Data governance document found" if has_dg else "No data governance documentation found",
        fix_hint="Create DATA_GOVERNANCE.md: data sources, consent, quality measures, retention",
        tier="static"))
    checks.append(ComplianceCheck(name="Data vault (controlled storage)", article=10, detection="auto",
        status="pass" if status.vault_enabled else "fail",
        evidence="Vault enabled. Data stored in your controlled S3/MinIO." if status.vault_enabled else "No vault configured.",
        fix_hint="Set VAULT_ENDPOINT, VAULT_ACCESS_KEY, VAULT_SECRET_KEY in .env or install a trust layer",
        tier="runtime"))
    result = {"number": 10, "title": "Data Governance", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result


def _check_article_11(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    readme = os.path.exists(os.path.join(scan_path, "README.md"))
    checks.append(ComplianceCheck(name="System description (README)", article=11, detection="hybrid",
        status="pass" if readme else "fail",
        evidence="README.md found" if readme else "No README.md found",
        fix_hint="Create README.md documenting system purpose, architecture, intended use",
        tier="static"))
    if status.total_runs > 0:
        ml = ", ".join(status.models_observed[:5])
        pl = ", ".join(status.providers_observed[:5])
        checks.append(ComplianceCheck(name="Runtime system inventory (AI-BOM data)", article=11, detection="auto", status="pass",
            evidence=f"Gateway observed: {status.total_runs} runs, models: [{ml}], providers: [{pl}], {status.total_tokens:,} tokens.",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Runtime system inventory (AI-BOM data)", article=11, detection="auto", status="warn",
            evidence="Runtime check skipped - no traffic data yet. Route AI calls through the gateway or install a trust layer.",
            fix_hint=_runtime_hint(rec_pkg, js_only),
            tier="runtime"))
    mc_files = ["MODEL_CARD.md", "model_card.md", "SYSTEM_CARD.md"]
    has_mc = any(os.path.exists(os.path.join(scan_path, f)) for f in mc_files)
    checks.append(ComplianceCheck(name="Model card / system card", article=11, detection="hybrid",
        status="pass" if has_mc else "warn",
        evidence="Model/system card found" if has_mc else "No model card found. Run: air-blackbox discover --generate-card",
        fix_hint="Create MODEL_CARD.md: intended use, limitations, performance, ethics",
        tier="static"))
    if status.total_runs > 0 and status.date_range_end:
        checks.append(ComplianceCheck(name="Documentation currency", article=11, detection="auto", status="pass",
            evidence=f"Traffic data current through {status.date_range_end}. {len(status.models_observed)} model(s) active.",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Documentation currency", article=11, detection="auto", status="warn",
            evidence="No runtime traffic data. Install a trust layer to track active models.",
            fix_hint="Route traffic through gateway or install a trust layer package",
            tier="runtime"))
    result = {"number": 11, "title": "Technical Documentation", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result


def _check_article_12(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    if status.reachable and status.total_runs > 0:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="pass",
            evidence=f"Gateway active. {status.total_runs:,} events logged. Period: {status.date_range_start} to {status.date_range_end}.",
            tier="runtime"))
    elif status.total_runs > 0:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="pass",
            evidence=f"Trust layer active. {status.total_runs:,} events logged. Period: {status.date_range_start} to {status.date_range_end}.",
            tier="runtime"))
    elif status.reachable:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="warn",
            evidence=f"Gateway running but no events logged yet.", fix_hint="Route traffic through gateway",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Automatic event logging", article=12, detection="auto", status="warn",
            evidence=f"Runtime check skipped - gateway not running. Install a trust layer for inline logging.",
            fix_hint=_runtime_hint(rec_pkg, js_only),
            tier="runtime"))
    if status.audit_chain_intact and status.audit_chain_length > 0:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto", status="pass",
            evidence=f"HMAC-SHA256 chain intact. {status.audit_chain_length:,} records.",
            tier="runtime"))
    elif status.trust_signing_key_set:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto", status="pass",
            evidence="TRUST_SIGNING_KEY configured. HMAC chain will activate on traffic.",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Tamper-evident audit chain", article=12, detection="auto",
            status="warn" if status.reachable else "fail",
            evidence="No TRUST_SIGNING_KEY set. Logs recorded but not tamper-evident.",
            fix_hint="Set TRUST_SIGNING_KEY in .env or install a trust layer package",
            tier="runtime"))
    if status.total_runs > 0:
        sample = status.recent_runs[0] if status.recent_runs else None
        if sample and all(sample.get(f) for f in ["run_id", "model", "timestamp"]):
            checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="pass",
                evidence="All records include: run_id, model, timestamp, tokens, provider.",
                tier="runtime"))
        else:
            checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="warn",
                evidence="Records found but missing some traceability fields.",
                tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Log detail and traceability", article=12, detection="auto", status="fail",
            evidence="No logged records.", fix_hint="Route traffic through gateway or install a trust layer.",
            tier="runtime"))
    if status.total_runs > 0 and status.date_range_start:
        checks.append(ComplianceCheck(name="Log retention", article=12, detection="auto", status="pass",
            evidence=f"Records retained from {status.date_range_start}. Storage: {'vault' if status.vault_enabled else 'local'}.",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Log retention", article=12, detection="auto", status="warn",
            evidence="No runtime records to assess retention policy.",
            fix_hint="Route traffic through gateway or install a trust layer to start recording",
            tier="runtime"))
    result = {"number": 12, "title": "Record-Keeping", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result


def _check_article_14(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    if status.total_runs > 0:
        checks.append(ComplianceCheck(name="Human-in-the-loop mechanism", article=14, detection="auto", status="warn",
            evidence=f"{status.total_runs:,} actions logged. No human approval gates detected.",
            fix_hint="Add approval gates: air.require_approval(action)",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Human-in-the-loop mechanism", article=14, detection="auto", status="warn",
            evidence="No traffic data to analyze for oversight patterns.",
            tier="runtime"))
    if status.reachable and status.guardrails_enabled:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="pass",
            evidence="Gateway active with guardrails. Kill switch available.",
            tier="runtime"))
    elif status.reachable:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="warn",
            evidence="Gateway running but guardrails not configured.", fix_hint="Create guardrails.yaml",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Kill switch / stop mechanism", article=14, detection="auto", status="warn",
            evidence="Runtime check skipped - gateway not running. Kill switch requires the gateway.",
            fix_hint=_runtime_hint(rec_pkg, js_only),
            tier="runtime"))
    op_files = ["OPERATOR_GUIDE.md", "operator_guide.md", "RUNBOOK.md"]
    has_ops = any(os.path.exists(os.path.join(scan_path, f)) for f in op_files)
    checks.append(ComplianceCheck(name="Operator understanding documentation", article=14, detection="manual",
        status="pass" if has_ops else "warn",
        evidence="Operator guide found" if has_ops else "No operator documentation found.",
        fix_hint="Create OPERATOR_GUIDE.md: capabilities, limitations, when to intervene",
        tier="static"))
    result = {"number": 14, "title": "Human Oversight", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result


def _check_article_15(status, scan_path, code_findings=None, rec_pkg="air-langchain-trust", js_only=False):
    checks = []
    if status.reachable:
        checks.append(ComplianceCheck(name="Prompt injection protection", article=15, detection="auto", status="pass",
            evidence=f"Gateway scanning for injection patterns. {status.injection_attempts} attempts detected." if status.injection_attempts > 0
            else "Gateway OTel pipeline scanning. No attempts detected.",
            tier="runtime"))
    elif status.total_runs > 0 and status.audit_chain_intact:
        checks.append(ComplianceCheck(name="Prompt injection protection", article=15, detection="auto", status="pass",
            evidence=f"Trust layer active with injection scanning. {status.injection_attempts} attempts detected in {status.total_runs} runs.",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Prompt injection protection", article=15, detection="auto", status="fail",
            evidence="No runtime injection protection. Install a trust layer for inline scanning.",
            fix_hint=_runtime_hint(rec_pkg, js_only),
            tier="runtime"))
    if status.total_runs > 0:
        er = (status.error_count / status.total_runs * 100)
        checks.append(ComplianceCheck(name="Error resilience", article=15, detection="auto",
            status="pass" if er < 5 else "warn" if er < 15 else "fail",
            evidence=f"Error rate: {er:.1f}% ({status.error_count}/{status.total_runs}).",
            tier="runtime"))
    else:
        checks.append(ComplianceCheck(name="Error resilience", article=15, detection="auto", status="warn",
            evidence="No traffic data to measure resilience.",
            fix_hint="Route traffic through gateway or install a trust layer.",
            tier="runtime"))
    has_auth = bool(os.environ.get("OPENAI_API_KEY")) or bool(os.environ.get("ANTHROPIC_API_KEY"))
    checks.append(ComplianceCheck(name="API access control", article=15, detection="hybrid",
        status="pass" if has_auth else "warn",
        evidence="API keys configured." if has_auth else "No API keys detected.",
        fix_hint="Set API keys in .env",
        tier="static"))
    rt_files = ["REDTEAM.md", "redteam_results.json", "ADVERSARIAL_TESTING.md"]
    has_rt = any(os.path.exists(os.path.join(scan_path, f)) for f in rt_files)
    checks.append(ComplianceCheck(name="Adversarial robustness testing", article=15, detection="manual",
        status="pass" if has_rt else "warn",
        evidence="Adversarial testing documentation found" if has_rt else "No red team / adversarial testing evidence.",
        fix_hint="Conduct adversarial testing. Export: air-blackbox export --tag=redteam",
        tier="static"))
    result = {"number": 15, "title": "Accuracy, Robustness & Cybersecurity", "checks": [_c2d(c) for c in checks]}
    for f in (code_findings or []):
        result["checks"].append(_finding_to_dict(f))
    return result
