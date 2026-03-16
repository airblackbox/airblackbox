"""
Deep scan — uses local fine-tuned LLM (Ollama) to analyze code beyond regex.

The air-compliance model (fine-tuned Llama 3.1 8B) catches compliance issues that patterns miss:
- Understanding *intent* behind code, not just keywords
- Context-aware analysis (e.g., is this logging for compliance or debugging?)
- Cross-file relationship detection
- Natural language documentation quality assessment

Usage:
    air-blackbox comply --scan .               # hybrid: regex + LLM (auto-detects Ollama)
    air-blackbox comply --scan . --no-llm      # regex-only (skip LLM)
    air-blackbox comply --scan . --model air-compliance  # specify model

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


DEEP_PROMPT_JSON = """You are an EU AI Act compliance expert analyzing Python AI agent code.

Analyze ONLY for these 6 articles — output ONLY valid JSON, no explanation:

- Article 9: Risk Management (error handling, fallbacks, risk assessment)
- Article 10: Data Governance (input validation, PII handling, data quality)
- Article 11: Technical Documentation (docstrings, type hints, README, model card)
- Article 12: Record-Keeping (logging, tracing, audit trails, observability)
- Article 14: Human Oversight (HITL gates, rate limits, kill switch, identity binding)
- Article 15: Accuracy & Security (injection defense, output validation, retry logic)

For each issue you find, output one JSON object. Only report issues the code actually has — do NOT fabricate findings.
Use status "pass" if the code satisfies an article, "warn" for partial compliance, "fail" for missing.

Output format (JSON array):
[
  {{"article": 9, "name": "Missing error handling on LLM calls", "status": "fail", "evidence": "Lines 42-48: raw openai.chat.completions.create() with no try/except", "fix_hint": "Wrap in try/except with fallback response"}},
  {{"article": 12, "name": "Structured logging present", "status": "pass", "evidence": "Uses logging.getLogger() with structured output", "fix_hint": ""}}
]

Report ALL 6 articles — use pass/warn/fail for each.

Code to analyze:
```python
{code}
```

JSON findings (array only, no extra text):"""


# Alpaca-format prompt for the fine-tuned air-compliance model
DEEP_PROMPT_ALPACA = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Analyze this Python code for EU AI Act compliance. This is a {sample_context} from a project with {total_files} Python files. Assess ONLY what is visible in the code below — do not assume patterns are missing if they could exist in files not shown.

For each of Articles 9, 10, 11, 12, 14, and 15: report status (pass if evidence found, warn if partial, fail only if clearly absent), cite specific evidence from the code (function names, patterns, line references), and give fix recommendations. Output as a JSON array.

### Input:
{code}

### Response:
"""


def deep_scan(code: str, model: str = "air-compliance",
              sample_context: str = "code sample",
              total_files: int = 0) -> dict:
    """Run deep LLM analysis on code.

    Args:
        code: The code to analyze
        model: Ollama model name
        sample_context: Description of what the sample contains (e.g., "core pipeline files")
        total_files: Total number of Python files in the project (for context)

    Returns:
        dict with 'available' (bool), 'findings' (list), 'model' (str), 'error' (str or None)
    """
    # Check if Ollama is available
    if not _ollama_available():
        return {
            "available": False,
            "findings": [],
            "model": model,
            "error": "Ollama not installed. Install: brew install ollama && ollama create air-compliance -f Modelfile",
        }

    # Check if model exists
    if not _model_available(model):
        return {
            "available": False,
            "findings": [],
            "model": model,
            "error": f"Model '{model}' not found. Create it: cd ~/models/air-compliance && ollama create air-compliance -f Modelfile",
        }

    # Truncate very long code to avoid context overflow
    max_chars = 12000
    if len(code) > max_chars:
        code = code[:max_chars] + "\n\n# ... (truncated for analysis)"

    # Use Alpaca prompt for fine-tuned model, JSON prompt for others
    if model.startswith("air-compliance"):
        prompt = DEEP_PROMPT_ALPACA.format(
            code=code,
            sample_context=sample_context,
            total_files=total_files or "unknown number of",
        )
    else:
        prompt = DEEP_PROMPT_JSON.format(code=code)

    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            return {
                "available": True,
                "findings": [],
                "model": model,
                "error": f"Ollama returned error: {result.stderr[:200]}",
            }

        raw_output = result.stdout

        # Always print raw output in verbose mode for debugging
        import os
        if os.environ.get("AIR_VERBOSE"):
            print(f"\n  [DEBUG] Model raw output ({len(raw_output)} chars):")
            print(f"  {raw_output[:1000]}")
            if len(raw_output) > 1000:
                print(f"  ... ({len(raw_output) - 1000} more chars)")

        findings = _parse_llm_output(raw_output)

        # Debug: log raw output length and first 500 chars for troubleshooting
        import logging
        logger = logging.getLogger("air_blackbox.deep_scan")
        logger.debug(f"Model raw output ({len(raw_output)} chars): {raw_output[:500]}")
        logger.debug(f"Parsed {len(findings)} findings from model output")

        return {
            "available": True,
            "findings": findings,
            "model": model,
            "error": None,
            "raw_length": len(raw_output),
            "sample_chars": len(code),
        }

    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "findings": [],
            "model": model,
            "error": "LLM analysis timed out after 180s. Try a smaller codebase.",
        }
    except Exception as e:
        return {
            "available": True,
            "findings": [],
            "model": model,
            "error": str(e),
        }


def hybrid_merge(rule_findings: list, llm_findings: list) -> list:
    """Merge rule-based and LLM findings intelligently.

    Rules:
    - Rule-based findings are ground truth for pattern checks (type hints, logging, retries)
    - LLM findings add context and catch things regex can't (intent, cross-file logic)
    - When both cover the same article, rule-based status wins for measurable checks
    - LLM insights are added as supplementary evidence
    """
    # Index rule findings by article
    rule_by_article = {}
    for f in rule_findings:
        art = f.get("article", 0)
        if art not in rule_by_article:
            rule_by_article[art] = []
        rule_by_article[art].append(f)

    # Index LLM findings by article
    llm_by_article = {}
    for f in llm_findings:
        art = f.get("article", 0)
        if art not in llm_by_article:
            llm_by_article[art] = []
        llm_by_article[art].append(f)

    merged = list(rule_findings)  # Start with all rule findings

    # Add LLM findings for articles not covered by rules, or as supplements
    for art, llm_list in llm_by_article.items():
        if art not in rule_by_article:
            # LLM found something rules didn't check — add it
            for f in llm_list:
                f["source"] = "llm"
                merged.append(f)
        else:
            # Both have findings — add LLM insights as supplementary
            for f in llm_list:
                f["source"] = "llm-supplement"
                f["name"] = f"[AI] {f.get('name', '')}"
                merged.append(f)

    return merged


def deep_scan_project(file_contents: dict, model: str = "air-compliance") -> dict:
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

    The model may return JSON, markdown, or mixed format.
    We try multiple strategies to extract valid findings.
    """
    import re
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
    if findings:
        return findings

    # Strategy 4: parse markdown-style output from fine-tuned model
    # Handles two formats:
    #   Format A: **Article 9 — Risk Management**: FAIL (status on same line)
    #   Format B: ### Article 9 — Risk Management \n **Status**: FAIL (status on next line)
    article_with_status = re.compile(
        r'\*{0,2}Article\s+(\d+)[^*:]*\*{0,2}\s*:\s*(PASS|FAIL|WARN)',
        re.IGNORECASE
    )
    article_header_only = re.compile(
        r'(?:#{1,4}\s+)?\*{0,2}Article\s+(\d+)\s*[—–-]\s*([^*:\n]+)',
        re.IGNORECASE
    )
    status_line = re.compile(
        r'\*{0,2}Status\*{0,2}\s*:\s*(PASS|FAIL|WARN)',
        re.IGNORECASE
    )
    # Also match "Analysis:" or "Evidence:" lines
    evidence_pattern = re.compile(r'\*{0,2}(?:Analysis|Evidence)\*{0,2}\s*:\s*(.*)', re.IGNORECASE)
    recommend_pattern = re.compile(r'\*{0,2}(?:Recommendation|Fix|Remediation)\*{0,2}\s*:\s*(.*)', re.IGNORECASE)

    current_article = None
    current_status = None
    current_name = ""
    current_evidence = []
    current_fix = []

    for line in raw.split("\n"):
        # Check for article header with status on same line (Format A)
        art_status_match = article_with_status.search(line)
        # Check for article header without status (Format B)
        art_header_match = article_header_only.search(line)
        # Check for standalone status line
        status_match = status_line.search(line.strip())

        if art_status_match:
            # Save previous finding
            if current_article is not None:
                findings.append(_validate_finding({
                    "article": current_article,
                    "name": current_name or f"Article {current_article} analysis",
                    "status": current_status,
                    "evidence": " ".join(current_evidence).strip(),
                    "fix_hint": " ".join(current_fix).strip(),
                }))
            current_article = int(art_status_match.group(1))
            current_status = art_status_match.group(2).lower()
            name_match = re.search(r'Article\s+\d+\s*[—–-]\s*([^*:]+)', line)
            current_name = name_match.group(1).strip() if name_match else f"Article {current_article} analysis"
            current_evidence = []
            current_fix = []
        elif art_header_match and not art_status_match:
            # Save previous finding
            if current_article is not None:
                findings.append(_validate_finding({
                    "article": current_article,
                    "name": current_name or f"Article {current_article} analysis",
                    "status": current_status,
                    "evidence": " ".join(current_evidence).strip(),
                    "fix_hint": " ".join(current_fix).strip(),
                }))
            current_article = int(art_header_match.group(1))
            current_name = art_header_match.group(2).strip()
            current_status = "warn"  # Default until we find a Status line
            current_evidence = []
            current_fix = []
        elif status_match and current_article is not None:
            # Standalone **Status**: PASS/FAIL/WARN line (Format B)
            current_status = status_match.group(1).lower()
        elif current_article is not None:
            ev_match = evidence_pattern.match(line.strip())
            rec_match = recommend_pattern.match(line.strip())
            if ev_match:
                current_evidence.append(ev_match.group(1).strip())
            elif rec_match:
                current_fix.append(rec_match.group(1).strip())
            else:
                cleaned = line.strip().lstrip("*-# ")
                if cleaned and not cleaned.startswith("Status") and not cleaned.startswith("###") and not cleaned.startswith("Summary"):
                    # Check if this looks like a recommendation
                    if any(kw in cleaned.lower() for kw in ["recommend", "address", "add ", "implement", "install"]):
                        current_fix.append(cleaned)
                    elif cleaned:
                        current_evidence.append(cleaned)

    # Don't forget the last finding
    if current_article is not None:
        findings.append(_validate_finding({
            "article": current_article,
            "name": current_name or f"Article {current_article} analysis",
            "status": current_status,
            "evidence": " ".join(current_evidence).strip(),
            "fix_hint": " ".join(current_fix).strip(),
        }))

    return [f for f in findings if f is not None]


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
