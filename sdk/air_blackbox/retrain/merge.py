"""Training data merger: combines feedback corrections with canonical corpus.

Takes the accumulated corrections from ~/.air-blackbox/training_feedback.jsonl,
validates them, deduplicates against the canonical training_data_v{N}.jsonl,
and writes a new versioned file ready for fine-tuning.

Usage:
    from air_blackbox.retrain.merge import merge_training_data
    report = merge_training_data(
        canonical_path="training/training_data_v11.jsonl",
        feedback_path="~/.air-blackbox/training_feedback.jsonl",
        output_dir="training/",
    )
    print(report)  # MergeReport with stats
"""

import glob
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_ARTICLES = {9, 10, 11, 12, 14, 15}
MIN_CODE_LENGTH = 20
MIN_OUTPUT_LENGTH = 10


@dataclass
class MergeReport:
    """Summary of a training data merge operation."""
    version: str = ""
    canonical_examples: int = 0
    new_from_feedback: int = 0
    duplicates_skipped: int = 0
    invalid_skipped: int = 0
    total_examples: int = 0
    article_distribution: Dict[int, int] = field(default_factory=dict)
    false_positive_corrections: int = 0
    output_path: str = ""
    warnings: List[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


def _extract_article(instruction: str) -> Optional[int]:
    """Pull the article number from an instruction string."""
    m = re.search(r"Article\s+(\d+)", instruction)
    if m:
        num = int(m.group(1))
        if num in VALID_ARTICLES:
            return num
    return None


def _example_hash(example: Dict) -> str:
    """Dedup key: SHA-256 of instruction + input."""
    raw = (example.get("instruction", "") + example.get("input", "")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_example(example: Dict, index: int) -> Optional[str]:
    """Validate a single training example. Returns error string or None."""
    instruction = example.get("instruction", "").strip()
    code_input = example.get("input", "").strip()
    output = example.get("output", "").strip()

    if not instruction:
        return f"example {index}: empty instruction"
    if not code_input or len(code_input) < MIN_CODE_LENGTH:
        return f"example {index}: input too short ({len(code_input)} chars, need {MIN_CODE_LENGTH})"
    if not output or len(output) < MIN_OUTPUT_LENGTH:
        return f"example {index}: output too short ({len(output)} chars, need {MIN_OUTPUT_LENGTH})"

    article = _extract_article(instruction)
    if article is None:
        return f"example {index}: no valid article number in instruction"

    return None


def _detect_latest_version(directory: str) -> int:
    """Find the highest version number in training_data_v{N}.jsonl files."""
    pattern = os.path.join(directory, "training_data_v*.jsonl")
    files = glob.glob(pattern)
    if not files:
        return 0
    versions = []
    for f in files:
        m = re.search(r"training_data_v(\d+)\.jsonl$", f)
        if m:
            versions.append(int(m.group(1)))
    return max(versions) if versions else 0


def merge_training_data(
    canonical_path: str,
    feedback_path: str,
    output_dir: str,
    min_feedback_count: int = 5,
    balance_threshold: float = 0.05,
) -> MergeReport:
    """Merge feedback corrections into the canonical training corpus.

    Reads the canonical training file and the feedback JSONL, deduplicates,
    validates, checks article balance, and writes a new versioned file.

    Args:
        canonical_path: Path to the current training_data_v{N}.jsonl
        feedback_path: Path to training_feedback.jsonl (from accept_and_write)
        output_dir: Directory to write the merged training_data_v{N+1}.jsonl
        min_feedback_count: Minimum feedback items before merging (safety check)
        balance_threshold: Minimum fraction per article (blocks if under this)

    Returns:
        MergeReport with full statistics.
    """
    report = MergeReport()

    # Resolve paths.
    canonical_path = os.path.expanduser(canonical_path)
    feedback_path = os.path.expanduser(feedback_path)
    output_dir = os.path.expanduser(output_dir)

    # Detect version.
    current_version = _detect_latest_version(os.path.dirname(canonical_path) or output_dir)
    if current_version == 0:
        # Try from the filename itself.
        m = re.search(r"v(\d+)", os.path.basename(canonical_path))
        current_version = int(m.group(1)) if m else 0
    next_version = current_version + 1
    report.version = f"v{next_version}"

    # Load canonical training data.
    canonical_examples = []
    canonical_hashes = set()
    if os.path.exists(canonical_path):
        with open(canonical_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    canonical_examples.append(ex)
                    canonical_hashes.add(_example_hash(ex))
                except json.JSONDecodeError:
                    continue
    report.canonical_examples = len(canonical_examples)

    # Load feedback.
    feedback_examples = []
    if os.path.exists(feedback_path):
        with open(feedback_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    feedback_examples.append(ex)
                except json.JSONDecodeError:
                    continue

    if len(feedback_examples) < min_feedback_count:
        report.blocked = True
        report.block_reason = (
            f"Only {len(feedback_examples)} feedback items (need at least "
            f"{min_feedback_count}). Collect more corrections before merging."
        )
        return report

    # Validate and deduplicate feedback.
    new_examples = []
    for i, ex in enumerate(feedback_examples):
        error = _validate_example(ex, i)
        if error:
            report.invalid_skipped += 1
            logger.debug(f"Skipping invalid feedback: {error}")
            continue

        h = _example_hash(ex)
        if h in canonical_hashes:
            report.duplicates_skipped += 1
            continue

        canonical_hashes.add(h)
        new_examples.append(ex)

        # Count false positive corrections.
        if ex.get("source") == "human_feedback":
            output = ex.get("output", "")
            if "NO ISSUE" in output or "false positive" in output.lower():
                report.false_positive_corrections += 1

    report.new_from_feedback = len(new_examples)

    # Merge.
    merged = canonical_examples + new_examples
    report.total_examples = len(merged)

    # Article distribution check.
    article_counts: Dict[int, int] = {a: 0 for a in VALID_ARTICLES}
    for ex in merged:
        article = _extract_article(ex.get("instruction", ""))
        if article is not None:
            article_counts[article] = article_counts.get(article, 0) + 1
    report.article_distribution = article_counts

    total = sum(article_counts.values())
    if total > 0:
        for article, count in article_counts.items():
            frac = count / total
            if frac < balance_threshold:
                report.blocked = True
                report.block_reason = (
                    f"Article {article} has only {count} examples "
                    f"({frac:.1%} of total). Need at least {balance_threshold:.0%}. "
                    f"Generate more examples for Article {article} before merging."
                )
                return report
            elif frac < 0.10:
                report.warnings.append(
                    f"Article {article} is underrepresented: {count} examples ({frac:.1%})"
                )

    # Write merged file.
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"training_data_v{next_version}.jsonl")
    with open(output_path, "w") as f:
        for ex in merged:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    report.output_path = os.path.abspath(output_path)

    logger.info(
        "training_data_merged",
        extra={
            "version": report.version,
            "canonical": report.canonical_examples,
            "new": report.new_from_feedback,
            "total": report.total_examples,
            "output": report.output_path,
        },
    )

    return report
