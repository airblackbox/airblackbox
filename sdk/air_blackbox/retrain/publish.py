"""Publish pipeline: register retrained model with Ollama and bump version.

After a successful retrain, this module:
  1. Creates an Ollama Modelfile for the new GGUF
  2. Registers it as air-compliance:v{N} and air-compliance:latest
  3. Writes a model card with training stats and fixed false positives
  4. Appends a CHANGELOG entry
  5. Bumps the version in pyproject.toml (optional)

Usage:
    from air_blackbox.retrain.publish import publish_model
    from air_blackbox.retrain.merge import MergeReport
    from air_blackbox.retrain.run import RetrainResult

    result = publish_model(
        gguf_path="~/.air-blackbox/models/v12/gguf/model.gguf",
        version="v12",
        merge_report=merge_report,
        retrain_result=retrain_result,
    )
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Outcome of publishing a retrained model."""
    success: bool = False
    ollama_model: str = ""          # e.g. "air-compliance:v12"
    model_card_path: str = ""
    changelog_entry: str = ""
    error: str = ""


def _write_modelfile(gguf_path: str, output_path: str) -> str:
    """Write an Ollama Modelfile for the compliance model."""
    content = f"""FROM {os.path.abspath(gguf_path)}

SYSTEM \"\"\"You are an EU AI Act compliance analyzer. You analyze Python AI agent code
for compliance gaps against Articles 9 (Risk Management), 10 (Data Governance),
11 (Technical Documentation), 12 (Record-Keeping), 14 (Human Oversight), and
15 (Accuracy, Robustness & Cybersecurity). Report which technical requirements
are met or missing, with specific line references and recommendations.

Important: You are a technical linter, not a legal advisor. Your output helps
developers identify potential compliance gaps. It is not a certified compliance
test.\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
"""
    with open(output_path, "w") as f:
        f.write(content)
    return output_path


def _write_model_card(
    output_path: str,
    version: str,
    merge_report,
    retrain_result,
) -> str:
    """Write a model card documenting the training run."""
    now = datetime.utcnow().isoformat() + "Z"

    article_dist = ""
    if merge_report and merge_report.article_distribution:
        for art, count in sorted(merge_report.article_distribution.items()):
            article_dist += f"  - Article {art}: {count} examples\n"

    card = f"""# AIR Blackbox Compliance Model - {version}

**Date:** {now}
**Base model:** Llama 3.2 1B (QLoRA fine-tuned)
**Quantization:** q4_k_m (GGUF Dynamic 2.0)

## Training Data

- **Version:** {version}
- **Total examples:** {merge_report.total_examples if merge_report else 'N/A'}
- **New from feedback:** {merge_report.new_from_feedback if merge_report else 'N/A'}
- **False positive corrections:** {merge_report.false_positive_corrections if merge_report else 'N/A'}

### Article Distribution
{article_dist if article_dist else 'N/A'}

## Evaluation

- **Accuracy:** {retrain_result.eval_accuracy:.1%}
- **False positive rate:** {retrain_result.eval_false_positive_rate:.1%}
- **False negative rate:** {retrain_result.eval_false_negative_rate:.1%}
- **Training loss:** {retrain_result.training_loss:.4f}
- **Eval examples:** {retrain_result.examples_eval}

## Training Config

- **Epochs:** 3
- **Batch size:** 4
- **Learning rate:** 2e-4
- **LoRA rank:** 16
- **Max sequence length:** 2048

## Limitations

This model is a technical compliance linter, not a legal advisor. It identifies
potential gaps in EU AI Act technical requirements. It does not guarantee
regulatory compliance. Always consult qualified legal counsel for compliance
decisions.

## Privacy

This model runs entirely on-device. No code, prompts, or results are sent
to any external service. The model weights never leave your machine.
"""
    with open(output_path, "w") as f:
        f.write(card)
    return output_path


def publish_model(
    gguf_path: str,
    version: str,
    merge_report=None,
    retrain_result=None,
    changelog_path: Optional[str] = None,
    pyproject_path: Optional[str] = None,
) -> PublishResult:
    """Register the retrained model with Ollama and write metadata.

    Args:
        gguf_path: Path to the .gguf model file
        version: Version string (e.g., "v12")
        merge_report: MergeReport from the merge step
        retrain_result: RetrainResult from the retrain step
        changelog_path: Path to CHANGELOG.md (appends entry)
        pyproject_path: Path to pyproject.toml (bumps patch version)

    Returns:
        PublishResult with success status and paths
    """
    result = PublishResult()
    gguf_path = os.path.expanduser(gguf_path)

    if not os.path.exists(gguf_path):
        result.error = f"GGUF file not found: {gguf_path}"
        return result

    if not shutil.which("ollama"):
        result.error = "Ollama not installed. Install from https://ollama.com"
        return result

    model_dir = os.path.dirname(gguf_path)

    # 1. Write Modelfile.
    modelfile_path = os.path.join(model_dir, "Modelfile")
    _write_modelfile(gguf_path, modelfile_path)

    # 2. Register with Ollama.
    tag = f"air-compliance:{version}"
    try:
        proc = subprocess.run(
            ["ollama", "create", tag, "-f", modelfile_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            result.error = f"ollama create failed: {proc.stderr[:300]}"
            return result

        result.ollama_model = tag

        # Tag as latest.
        subprocess.run(
            ["ollama", "cp", tag, "air-compliance:latest"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        logger.info(f"Registered model: {tag} (also tagged as latest)")

    except subprocess.TimeoutExpired:
        result.error = "ollama create timed out"
        return result

    # 3. Write model card.
    card_path = os.path.join(model_dir, "MODEL_CARD.md")
    _write_model_card(card_path, version, merge_report, retrain_result)
    result.model_card_path = card_path

    # 4. CHANGELOG entry.
    now = datetime.utcnow().strftime("%Y-%m-%d")
    fp_count = merge_report.false_positive_corrections if merge_report else 0
    new_count = merge_report.new_from_feedback if merge_report else 0
    accuracy = retrain_result.eval_accuracy if retrain_result else 0

    entry = (
        f"\n## {version} ({now})\n\n"
        f"- Retrained compliance model on {new_count} new feedback corrections\n"
        f"- Fixed {fp_count} false positive patterns\n"
        f"- Eval accuracy: {accuracy:.1%}\n"
        f"- Model: air-compliance:{version}\n"
    )
    result.changelog_entry = entry

    if changelog_path and os.path.exists(changelog_path):
        with open(changelog_path, "r") as f:
            existing = f.read()
        with open(changelog_path, "w") as f:
            # Insert after the first heading.
            if "\n## " in existing:
                parts = existing.split("\n## ", 1)
                f.write(parts[0] + entry + "\n## " + parts[1])
            else:
                f.write(existing + entry)

    # 5. Bump pyproject.toml version (patch bump).
    if pyproject_path and os.path.exists(pyproject_path):
        with open(pyproject_path, "r") as f:
            content = f.read()
        import re
        m = re.search(r'version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
        if m:
            major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
            new_version = f"{major}.{minor}.{patch + 1}"
            content = content.replace(
                f'version = "{m.group(1)}.{m.group(2)}.{m.group(3)}"',
                f'version = "{new_version}"',
            )
            with open(pyproject_path, "w") as f:
                f.write(content)
            logger.info(f"Bumped version to {new_version}")

    result.success = True
    logger.info(
        "model_published",
        extra={
            "model": result.ollama_model,
            "card": result.model_card_path,
        },
    )

    return result
