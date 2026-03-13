"""
Deep scan — uses local fine-tuned LLM (Ollama) to analyze code beyond regex.

The air-compliance-v2 model catches compliance issues that patterns miss:
- Understanding *intent* behind code, not just keywords
- Context-aware analysis (e.g., is this logging for compliance or debugging?)
- Cross-file relationship detection
- Natural language documentation quality assessment

Usage:
    air-blackbox comply --scan . --deep       # regex + LLM
    air-blackbox comply --scan . --deep --model air-compliance-v2

Falls back gracefully to regex-only if Ollama is not available.
"""
import json
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeepFinding:
    """A finding from the LLM deep analysis."""
    article: int
    name: str
    status: str  # pass, warn, fail
    evidence: str
    fix_hint: str = ""
    source: str = "llm"


DEEP_PROMPT = """You are an EU AI Act compliance expert analyzing Python AI agent code.

Analyze ONLY for these 6 articles — output ONLY valid JSON, no explanation:

- Article 9: Risk Management (error handling, fallbacks, risk assessment)
- Article 10: Data Governance (input validation, PII handling, data quality)
- Article 11: Technical Documentation (docstrings, type hints, README, model card)
- Article 12: Record-Keeping (logging, tracing, audit trails, observability)
- Article 14: Human Oversight (HITL gates, rate limits, kill switch, identity binding)
- Article 15: Accuracy & Security (injection defense, output validation, retry logic)

For each issue you find, output one JSON object. Only report issues the code actually has — do NOT fabricate findings.

Output format (JSON array):
[
  {{"article": 9, "name": "Missing error handling on LLM calls", "status": "fail", "evidence": "Lines 42-48: raw openai.chat.completions.create() with no try/except", "fix_hint": "Wrap in try/except with fallback response"}},
  {{"article": 12, "name": "No structured logging", "status": "warn", "evidence": "Uses print() for debugging but no logging framework", "fix_hint": "Add import logging and use logger.info/error"}}
]

If code is fully compliant for an article, omit it. Only report actual findings.

Code to analyze:
```python
{code}
```

JSON findings (array only, no extra text):"""


def deep_scan(code: str, model: str = "air-compliance-v2") -> dict:
    """Run deep LLM analysis on code.

    Returns:
        dict with 'available' (bool), 'findings' (list), 'model' (str), 'error' (str or None)
    """
    # Check if Ollama is available
    if not _ollama_available():
        return {
            "available": False,
            "findings": [],
            "model": model,
            "error": "Ollama not installed. Install: brew install ollama && ollama pull air-compliance-v2",
        }

    # Check if model exists
    if not _model_available(model):
        return {
            "available": False,
            "findings": [],
            "model": model,
            "error": f"Model '{model}' not found. Pull it: ollama pull {model}",
        }

    # Truncate very long code to avoid context overflow
    max_chars = 12000
    if len(code) > max_chars:
        code = code[:max_chars] + "\n\n# ... (truncated for analysis)"

    prompt = DEEP_PROMPT.format(code=code)

    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return {
                "available": True,
                "findings": [],
                "model": model,
                "error": f"Ollama returned error: {result.stderr[:200]}",
            }

        findings = _parse_llm_output(result.stdout)
        return {
            "available": True,
            "findings": findings,
            "model": model,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "findings": [],
            "model": model,
            "error": "LLM analysis timed out after 120s. Try a smaller file.",
        }
    except Exception as e:
        return {
            "available": True,
            "findings": [],
            "model": model,
            "error": str(e),
        }


def deep_scan_project(file_contents: dict, model: str = "air-compliance-v2") -> dict:
    """Run deep scan across multiple files, merging findings.

    Args:
        file_contents: dict of {filepath: code_string}
        model: Ollama model name

    Returns:
        dict with merged findings and per-file analysis
    """
    if not _ollama_available() or not _model_available(model):
        return deep_scan("", model)

    all_findings = []
    file_results = []

    for filepath, code in file_contents.items():
        if len(code.strip()) < 50:  # Skip tiny files
            continue
        result = deep_scan(code, model)
        for f in result.get("findings", []):
            f["file"] = filepath
        all_findings.extend(result.get("findings", []))
        file_results.append({
            "file": filepath,
            "findings_count": len(result.get("findings", [])),
            "error": result.get("error"),
        })

    return {
        "available": True,
        "findings": all_findings,
        "model": model,
        "files_analyzed": len(file_results),
        "file_results": file_results,
        "error": None,
    }


def _ollama_available() -> bool:
    """Check if ollama CLI is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _model_available(model: str) -> bool:
    """Check if a specific Ollama model is pulled."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        return model in result.stdout
    except Exception:
        return False


def _parse_llm_output(raw: str) -> list:
    """Parse LLM output into structured findings.

    The model should return a JSON array, but LLMs can be messy.
    We try multiple strategies to extract valid JSON.
    """
    raw = raw.strip()

    # Strategy 1: direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [_validate_finding(f) for f in data if _validate_finding(f)]
    except json.JSONDecodeError:
        pass

    # Strategy 2: find JSON array in the output
    start = raw.find("[")
    end = raw.rfind("]")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, list):
                return [_validate_finding(f) for f in data if _validate_finding(f)]
        except json.JSONDecodeError:
            pass

    # Strategy 3: line-by-line JSON objects
    findings = []
    for line in raw.split("\n"):
        line = line.strip().rstrip(",")
        if line.startswith("{"):
            try:
                f = _validate_finding(json.loads(line))
                if f:
                    findings.append(f)
            except json.JSONDecodeError:
                continue
    return findings


def _validate_finding(f) -> Optional[dict]:
    """Validate a finding dict has required fields."""
    if not isinstance(f, dict):
        return None
    if "article" not in f or "name" not in f or "status" not in f:
        return None
    if f["status"] not in ("pass", "warn", "fail"):
        f["status"] = "warn"
    return {
        "article": int(f.get("article", 0)),
        "name": str(f.get("name", "")),
        "status": f["status"],
        "evidence": str(f.get("evidence", "")),
        "fix_hint": str(f.get("fix_hint", "")),
        "source": "llm",
    }
