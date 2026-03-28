"""
Bias and fairness evaluation module for AI agent codebases.

Checks Python code for fairness and bias patterns:
  - Fairness Metrics (Art. 10)
  - Bias Detection Libraries (Art. 10)
  - Protected/Sensitive Attributes (Art. 10)
  - Dataset Balancing Patterns (Art. 10)
  - Model Card Bias Documentation (Art. 11)
  - Runtime Bias Monitoring (Art. 15)

These checks ensure models are evaluated for disparate impact,
demographic parity, and other fairness constraints required by
the EU AI Act.
"""

import os
import re
from typing import List

from air_blackbox.compliance.code_scanner import (
    CodeFinding,
    _find_python_files,
    _rel,
)


def scan_bias(scan_path: str) -> List[CodeFinding]:
    """Run all bias and fairness checks against a codebase."""
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
    findings.extend(_check_fairness_metrics(file_contents, scan_path))
    findings.extend(_check_bias_detection(file_contents, scan_path))
    findings.extend(_check_protected_attributes(file_contents, scan_path))
    findings.extend(_check_dataset_balance(file_contents, scan_path))
    findings.extend(_check_model_card_bias(file_contents, scan_path))
    findings.extend(_check_output_bias_monitoring(file_contents, scan_path))
    return findings


def _check_fairness_metrics(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 10: Fairness metric implementations.
    
    Detects demographic parity, equalized odds, disparate impact,
    statistical parity, equal opportunity, and calibration measures.
    """
    strong_patterns = [
        r"demographic_parity", r"equalized_odds", r"disparate_impact",
        r"statistical_parity", r"equal_opportunity", r"calibration_score",
        r"fairness_score", r"bias_score", r"group_fairness",
        r"DemographicParity", r"EqualizedOdds", r"DisparateImpact",
        r"fairness_metric", r"bias_metric", r"parity_metric",
    ]
    moderate_patterns = [
        r"metric.*fairness", r"fairness.*metric",
        r"score.*bias", r"bias.*score",
        r"fairness_check", r"bias_check",
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong_combined, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate_combined, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=10, name="Fairness metrics",
            status="pass",
            evidence=f"Fairness metrics found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=10, name="Fairness metrics",
            status="warn",
            evidence=f"Fairness references in {len(moderate_hits)} file(s) but no structured metrics",
            fix_hint="Implement fairness metrics (demographic_parity, equalized_odds) per EU AI Act Art. 10",
        )]
    return [CodeFinding(
        article=10, name="Fairness metrics",
        status="warn",
        evidence="No fairness metric implementations detected",
        fix_hint="Add fairness metric checks for disparate impact, parity, and equal opportunity (Art. 10)",
    )]


def _check_bias_detection(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 10: Bias detection library integration.
    
    Looks for aif360, fairlearn, what_if_tool, responsibleai,
    and other bias detection frameworks.
    """
    strong_patterns = [
        r"aif360", r"fairlearn", r"what_if_tool", r"responsibleai",
        r"bias_detect", r"bias_audit", r"bias_test",
        r"check_bias", r"measure_bias", r"BiasDetector",
        r"FairnessChecker", r"BiasChecker", r"BiasScanner",
        r"from aif360", r"from fairlearn", r"import fairlearn",
        r"responsibleai_dashboard", r"analyze_bias",
    ]
    moderate_patterns = [
        r"bias.*librar", r"fairness.*librar",
        r"bias_framework", r"fairness_framework",
        r"audit_bias", r"test_fairness",
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong_combined, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate_combined, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=10, name="Bias detection libraries",
            status="pass",
            evidence=f"Bias detection library found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=10, name="Bias detection libraries",
            status="warn",
            evidence=f"Bias audit references in {len(moderate_hits)} file(s) but no library integration",
            fix_hint="Integrate aif360, fairlearn, or ResponsibleAI for automated bias testing (Art. 10)",
        )]
    return [CodeFinding(
        article=10, name="Bias detection libraries",
        status="warn",
        evidence="No bias detection library integration detected",
        fix_hint="Add aif360, fairlearn, or ResponsibleAI to detect disparate impact (Art. 10)",
    )]


def _check_protected_attributes(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 10: Handling of protected and sensitive attributes.
    
    Moderate signal: just declaring sensitive attributes.
    Strong signal: using them with fairness checks.
    """
    # Protected attribute declarations
    attribute_patterns = [
        r"protected_attribute", r"sensitive_attribute", r"demographic",
        r"\brace\b", r"\brace\s*[:=]", r"\bgender\b", r"\bgender\s*[:=]",
        r"ethnicity", r"age_group", r"disability", r"religion",
        r"sexual_orientation", r"marital_status", r"nationality",
        r"PROTECTED_ATTRS", r"SENSITIVE_ATTRS", r"demographic_vars",
    ]
    # Using attributes with fairness checks (strong signal)
    fairness_usage_patterns = [
        r"(?:protected|demographic|sensitive).*(?:fairness|bias|parity)",
        r"(?:fairness|bias|parity).*(?:protected|demographic|sensitive)",
        r"stratify.*(?:race|gender|age_group|ethnicity)",
        r"(?:race|gender|age_group|ethnicity).*stratif",
    ]
    attr_combined = "|".join(attribute_patterns)
    usage_combined = "|".join(fairness_usage_patterns)
    attr_hits = [
        fp for fp, c in file_contents.items()
        if re.search(attr_combined, c, re.IGNORECASE)
    ]
    usage_hits = [
        fp for fp, c in file_contents.items()
        if re.search(usage_combined, c, re.IGNORECASE) and fp in attr_hits
    ]
    if usage_hits:
        return [CodeFinding(
            article=10, name="Protected attribute handling",
            status="pass",
            evidence=f"Protected attributes with fairness checks in {len(usage_hits)} file(s)",
        )]
    if attr_hits:
        return [CodeFinding(
            article=10, name="Protected attribute handling",
            status="warn",
            evidence=f"Protected attributes declared in {len(attr_hits)} file(s) but not used with fairness checks",
            fix_hint="Use protected attributes in fairness evaluations (demographic_parity, stratification)",
        )]
    return [CodeFinding(
        article=10, name="Protected attribute handling",
        status="warn",
        evidence="No protected/sensitive attribute handling detected",
        fix_hint="Identify and track protected attributes (race, gender, age) for fairness analysis (Art. 10)",
    )]


def _check_dataset_balance(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 10: Dataset balancing and class imbalance handling.
    
    Looks for SMOTE, stratified sampling, class weighting, and
    other techniques to prevent biased training data.
    """
    strong_patterns = [
        r"class_weight", r"sample_weight", r"oversampling",
        r"undersampling", r"SMOTE", r"stratified_split",
        r"StratifiedKFold", r"stratified_shuffle_split",
        r"balanced_dataset", r"class_imbalance", r"rebalance",
        r"data_augment", r"balance_classes", r"weight_samples",
        r"imbalanced_learn", r"RandomOverSampler",
        r"RandomUnderSampler", r"SMOTETomek",
    ]
    moderate_patterns = [
        r"balance.*data", r"data.*balance",
        r"stratif", r"imbalance",
        r"weight.*class", r"class.*weight",
        r"oversample|undersample",
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong_combined, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate_combined, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=10, name="Dataset balancing",
            status="pass",
            evidence=f"Dataset balancing patterns found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=10, name="Dataset balancing",
            status="warn",
            evidence=f"Balancing references in {len(moderate_hits)} file(s) but no structured approach",
            fix_hint="Use SMOTE, class_weight, or stratified sampling to handle class imbalance (Art. 10)",
        )]
    return [CodeFinding(
        article=10, name="Dataset balancing",
        status="warn",
        evidence="No dataset balancing patterns detected",
        fix_hint="Address class imbalance with SMOTE, stratified splits, or class weighting (Art. 10)",
    )]


def _check_model_card_bias(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 11: Model card and bias documentation.
    
    Looks for bias reports, fairness statements, known limitations,
    and debiasing documentation.
    """
    strong_patterns = [
        r"bias_report", r"fairness_report", r"model_card",
        r"bias_statement", r"known_limitations", r"bias_mitigation",
        r"debiasing", r"fairness_constraint", r"bias_analysis",
        r"fairness_statement", r"limitation_statement",
        r"mitigation_strategy", r"fairness_analysis",
        r"model_documentation", r"evaluation_report",
    ]
    moderate_patterns = [
        r"report.*bias", r"bias.*report",
        r"card.*fairness", r"fairness.*card",
        r"document.*limitations", r"limitations.*document",
        r"bias.*documentation", r"documentation.*bias",
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong_combined, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate_combined, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=11, name="Model card bias documentation",
            status="pass",
            evidence=f"Bias documentation found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=11, name="Model card bias documentation",
            status="warn",
            evidence=f"Documentation references in {len(moderate_hits)} file(s) but no structured bias reporting",
            fix_hint="Create model cards documenting known biases and fairness limitations (Art. 11)",
        )]
    return [CodeFinding(
        article=11, name="Model card bias documentation",
        status="warn",
        evidence="No model card or bias documentation patterns detected",
        fix_hint="Document model biases, limitations, and mitigation strategies in model cards (Art. 11)",
    )]


def _check_output_bias_monitoring(
    file_contents: dict, scan_path: str
) -> List[CodeFinding]:
    """Article 15: Runtime bias monitoring and alerting.
    
    Looks for bias drift detection, fairness dashboards,
    and real-time fairness thresholds.
    """
    strong_patterns = [
        r"monitor_bias", r"bias_alert", r"fairness_threshold",
        r"bias_drift", r"fairness_dashboard", r"bias_metric_log",
        r"demographic_parity_check", r"equal_opportunity_check",
        r"disparate_impact_check", r"bias_monitoring",
        r"fairness_monitor", r"bias_monitoring_service",
        r"detect_bias_drift", r"fairness_alert",
        r"bias_threshold", r"parity_threshold",
    ]
    moderate_patterns = [
        r"monitor.*fairness", r"fairness.*monitor",
        r"alert.*bias", r"bias.*alert",
        r"dashboard.*fairness", r"fairness.*dashboard",
        r"log.*bias_metric", r"bias.*log",
        r"track_fairness", r"fairness_track",
    ]
    strong_combined = "|".join(strong_patterns)
    moderate_combined = "|".join(moderate_patterns)
    strong_hits = [
        fp for fp, c in file_contents.items()
        if re.search(strong_combined, c, re.IGNORECASE)
    ]
    moderate_hits = [
        fp for fp, c in file_contents.items()
        if re.search(moderate_combined, c, re.IGNORECASE) and fp not in strong_hits
    ]
    if strong_hits:
        return [CodeFinding(
            article=15, name="Bias monitoring and alerting",
            status="pass",
            evidence=f"Bias monitoring patterns found in {len(strong_hits)} file(s)",
        )]
    if moderate_hits:
        return [CodeFinding(
            article=15, name="Bias monitoring and alerting",
            status="warn",
            evidence=f"Monitoring references in {len(moderate_hits)} file(s) but no production alerting",
            fix_hint="Implement runtime bias monitoring with alerts for fairness drift (Art. 15)",
        )]
    return [CodeFinding(
        article=15, name="Bias monitoring and alerting",
        status="warn",
        evidence="No runtime bias monitoring or alerting detected",
        fix_hint="Add fairness dashboards and drift detection to monitor bias in production (Art. 15)",
    )]
