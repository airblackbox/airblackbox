"""Compliance feedback collection, processing, and training data generation.

This module handles gathering, validating, and recording user feedback
on compliance scanning results. Critically, it writes accepted corrections
back to a training JSONL file so the fine-tuned compliance model improves
over time. This closes the feedback loop: scan -> review -> correct -> retrain.

The training data format matches what Unsloth/LoRA fine-tuning expects:
  {"instruction": "...", "input": "<code>", "output": "<finding>"}
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Default path for training data output.
_DEFAULT_TRAINING_DIR = os.path.expanduser("~/.air-blackbox")
_DEFAULT_TRAINING_FILE = "training_feedback.jsonl"

# Article names for human-readable instructions.
ARTICLE_NAMES = {
    9: "Risk Management",
    10: "Data Governance",
    11: "Technical Documentation",
    12: "Record-Keeping",
    14: "Human Oversight",
    15: "Robustness",
}


@dataclass
class ComplianceFeedback:
    """Represents feedback on a compliance scan result.

    Attributes:
        scan_id: Unique identifier for the scanned item
        article: EU AI Act article number (9, 10, 11, 12, 14, 15)
        severity: Issue severity level (critical, high, medium, low)
        feedback_text: User feedback text explaining the correction
        original_finding: The scanner's original finding text
        corrected_finding: The user's corrected finding (what it should have said)
        code_snippet: The code that was scanned (for training data)
        is_false_positive: Whether the original finding was a false positive
        accepted: Whether this feedback has been accepted for training
        timestamp: When feedback was collected
        feedback_id: SHA-256 hash of scan_id + article + timestamp (dedup key)
    """
    scan_id: str
    article: int
    severity: str
    feedback_text: str
    original_finding: str = ""
    corrected_finding: str = ""
    code_snippet: str = ""
    is_false_positive: bool = False
    accepted: bool = False
    timestamp: str = ""
    feedback_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if not self.feedback_id:
            raw = f"{self.scan_id}|{self.article}|{self.timestamp}"
            self.feedback_id = hashlib.sha256(raw.encode()).hexdigest()[:16]


def validate_feedback_input(feedback_text: str, article: int, severity: str) -> bool:
    """Validate user feedback before processing.

    Args:
        feedback_text: The feedback text to validate
        article: EU AI Act article number
        severity: Issue severity level

    Returns:
        True if feedback passes validation

    Raises:
        ValueError: If feedback fails validation
    """
    if not feedback_text or len(feedback_text.strip()) < 10:
        raise ValueError("Feedback text must be at least 10 characters")

    if article not in (9, 10, 11, 12, 14, 15):
        raise ValueError(f"Invalid article: {article}")

    if severity not in ("critical", "high", "medium", "low"):
        raise ValueError(f"Invalid severity: {severity}")

    return True


def record_feedback(
    scan_id: str,
    article: int,
    severity: str,
    feedback_text: str,
    original_finding: str = "",
    corrected_finding: str = "",
    code_snippet: str = "",
    is_false_positive: bool = False,
) -> ComplianceFeedback:
    """Record user feedback on a compliance scan result.

    Args:
        scan_id: Unique identifier for the scanned item
        article: EU AI Act article number
        severity: Issue severity level
        feedback_text: User feedback text
        original_finding: What the scanner originally said
        corrected_finding: What the scanner should have said
        code_snippet: The code that was scanned
        is_false_positive: True if the original finding was wrong

    Returns:
        ComplianceFeedback object with audit logging
    """
    validate_feedback_input(feedback_text, article, severity)

    feedback = ComplianceFeedback(
        scan_id=scan_id,
        article=article,
        severity=severity,
        feedback_text=feedback_text.strip(),
        original_finding=original_finding,
        corrected_finding=corrected_finding,
        code_snippet=code_snippet,
        is_false_positive=is_false_positive,
    )

    logger.info(
        "feedback_recorded",
        extra={
            "feedback_id": feedback.feedback_id,
            "scan_id": scan_id,
            "article": article,
            "severity": severity,
            "is_false_positive": is_false_positive,
            "timestamp": feedback.timestamp,
        },
    )

    return feedback


def collect_feedback_batch(
    feedback_items: List[Dict[str, Any]],
) -> List[ComplianceFeedback]:
    """Collect multiple feedback items with error recovery.

    Args:
        feedback_items: List of feedback dictionaries

    Returns:
        List of successfully recorded feedback items
    """
    results = []
    failed_count = 0

    for item in feedback_items:
        try:
            feedback = record_feedback(
                scan_id=item.get("scan_id", ""),
                article=item.get("article", 0),
                severity=item.get("severity", ""),
                feedback_text=item.get("feedback_text", ""),
                original_finding=item.get("original_finding", ""),
                corrected_finding=item.get("corrected_finding", ""),
                code_snippet=item.get("code_snippet", ""),
                is_false_positive=item.get("is_false_positive", False),
            )
            results.append(feedback)
        except (ValueError, KeyError) as e:
            failed_count += 1
            logger.warning(f"Failed to record feedback item: {e}")

    logger.info(
        "batch_feedback_processed",
        extra={"total": len(feedback_items), "failed": failed_count},
    )

    return results


# ---------------------------------------------------------------------------
# Training data generation - the feedback loop that improves the model.
# ---------------------------------------------------------------------------


def feedback_to_training_example(feedback: ComplianceFeedback) -> Optional[Dict[str, str]]:
    """Convert a feedback item into a training example for fine-tuning.

    The output format matches the Unsloth/LoRA training pipeline:
      {"instruction": "...", "input": "<code>", "output": "<corrected finding>"}

    Args:
        feedback: A ComplianceFeedback with code_snippet and correction.

    Returns:
        Training example dict, or None if insufficient data.
    """
    if not feedback.code_snippet:
        logger.debug("Skipping training example: no code_snippet")
        return None

    article_name = ARTICLE_NAMES.get(feedback.article, f"Article {feedback.article}")

    instruction = (
        f"Analyze this Python AI agent code for EU AI Act "
        f"Article {feedback.article} ({article_name}) compliance."
    )

    # For false positives, the corrected output should say "no issue found."
    if feedback.is_false_positive:
        output = (
            f"NO ISSUE: This code does not violate Article {feedback.article} "
            f"({article_name}).\n"
            f"REASON: {feedback.feedback_text}\n"
            f"ORIGINAL (incorrect): {feedback.original_finding}"
        )
    elif feedback.corrected_finding:
        output = feedback.corrected_finding
    else:
        # Use the feedback text as a correction narrative.
        output = (
            f"FINDING: {feedback.feedback_text}\n"
            f"ARTICLE: {feedback.article}\n"
            f"SEVERITY: {feedback.severity.upper()}"
        )

    return {
        "instruction": instruction,
        "input": feedback.code_snippet,
        "output": output,
        "source": "human_feedback",
        "feedback_id": feedback.feedback_id,
    }


def write_training_data(
    feedbacks: List[ComplianceFeedback],
    output_dir: Optional[str] = None,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Write accepted feedback to a JSONL training file.

    Appends new training examples to the file (does not overwrite).
    Deduplicates by feedback_id so the same correction is never
    written twice even if this function is called multiple times.

    Args:
        feedbacks: List of ComplianceFeedback items to convert.
        output_dir: Directory for the training file.
                    Defaults to ~/.air-blackbox/
        output_file: Filename. Defaults to training_feedback.jsonl

    Returns:
        Summary dict with counts and output path.
    """
    out_dir = output_dir or _DEFAULT_TRAINING_DIR
    out_file = output_file or _DEFAULT_TRAINING_FILE
    out_path = os.path.join(out_dir, out_file)

    os.makedirs(out_dir, exist_ok=True)

    # Load existing feedback IDs for dedup.
    existing_ids: set = set()
    if os.path.exists(out_path):
        with open(out_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    fid = entry.get("feedback_id", "")
                    if fid:
                        existing_ids.add(fid)
                except json.JSONDecodeError:
                    continue

    written = 0
    skipped_no_code = 0
    skipped_duplicate = 0

    with open(out_path, "a") as f:
        for fb in feedbacks:
            example = feedback_to_training_example(fb)
            if example is None:
                skipped_no_code += 1
                continue
            if example["feedback_id"] in existing_ids:
                skipped_duplicate += 1
                continue

            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            existing_ids.add(example["feedback_id"])
            written += 1

    summary = {
        "output_path": os.path.abspath(out_path),
        "written": written,
        "skipped_no_code": skipped_no_code,
        "skipped_duplicate": skipped_duplicate,
        "total_in_file": len(existing_ids),
    }

    logger.info("training_data_written", extra=summary)
    return summary


def accept_and_write(
    scan_id: str,
    article: int,
    severity: str,
    feedback_text: str,
    original_finding: str,
    corrected_finding: str,
    code_snippet: str,
    is_false_positive: bool = False,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """One-call convenience: record feedback AND write training data.

    This is the main entry point for the feedback loop. Call this when
    a user reviews a scan result and provides a correction.

    Args:
        scan_id: Unique identifier for the scanned item
        article: EU AI Act article number
        severity: Issue severity level
        feedback_text: User feedback text
        original_finding: What the scanner originally said
        corrected_finding: What the scanner should have said
        code_snippet: The code that was scanned
        is_false_positive: True if the original finding was wrong
        output_dir: Where to write training data

    Returns:
        Summary dict with feedback_id, training data path, and counts.

    Example:
        >>> result = accept_and_write(
        ...     scan_id="scan-abc123",
        ...     article=12,
        ...     severity="high",
        ...     feedback_text="This app uses structlog, which counts as audit logging",
        ...     original_finding="No audit logging detected for tool calls",
        ...     corrected_finding="FINDING: structlog detected but missing HMAC chain...",
        ...     code_snippet="import structlog\\nlogger = structlog.get_logger()\\n...",
        ...     is_false_positive=False,
        ... )
        >>> print(result["written"])  # 1
    """
    feedback = record_feedback(
        scan_id=scan_id,
        article=article,
        severity=severity,
        feedback_text=feedback_text,
        original_finding=original_finding,
        corrected_finding=corrected_finding,
        code_snippet=code_snippet,
        is_false_positive=is_false_positive,
    )
    feedback.accepted = True

    summary = write_training_data([feedback], output_dir=output_dir)
    summary["feedback_id"] = feedback.feedback_id
    return summary
