"""
AIR Blackbox Prompt Injection Detector.

Scores content against a library of known injection techniques.
15 weighted patterns across 5 categories:
  - Role override (identity hijacking)
  - Delimiter injection (fake system messages)
  - Privilege escalation (mode switching)
  - Data exfiltration (stealing context)
  - Jailbreak (bypassing safety)

Each pattern has a weight (0-1) and a minimum sensitivity level.
The detector filters patterns by sensitivity and scores content.

Sensitivity levels:
  - low: catches the obvious stuff (role override, jailbreak)
  - medium: adds delimiter and exfil patterns
  - high: includes subtle patterns (encoding evasion, tool abuse)

Usage:
    detector = InjectionDetector(sensitivity="medium", block_threshold=0.7)
    result = detector.scan(user_input)
    if result.blocked:
        log_and_reject(result)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class PatternDef:
    """Definition of an injection detection pattern."""

    name: str
    regex: re.Pattern[str]
    weight: float
    category: str
    min_sensitivity: Literal["low", "medium", "high"]
    description: str = ""
@dataclass
class InjectionResult:
    """Result of scanning content for injection patterns."""

    detected: bool
    score: float
    patterns: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    blocked: bool = False
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for audit chain logging."""
        return {
            "detected": self.detected,
            "score": round(self.score, 4),
            "patterns": self.patterns,
            "categories": self.categories,
            "blocked": self.blocked,
        }


# ---------------------------------------------------------------
# Pattern library: 20 patterns across 5 categories
# ---------------------------------------------------------------

INJECTION_PATTERNS: list[PatternDef] = [
    # === Category: role_override ===
    PatternDef(
        name="ignore_previous",
        regex=re.compile(
            r"(?:ignore|forget|disregard)\s+(?:all\s+)?"
            r"(?:previous|prior|above|earlier)\s+"
            r"(?:instructions|prompts|rules|directives|context)",
            re.IGNORECASE,
        ),
        weight=0.9,
        category="role_override",
        min_sensitivity="low",
        description="Attempts to wipe prior instructions",
    ),
    PatternDef(
        name="new_identity",
        regex=re.compile(
            r"(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you're)"
            r"|your\s+new\s+role\s+is|from\s+now\s+on\s+you\s+are)",
            re.IGNORECASE,
        ),
        weight=0.8,
        category="role_override",
        min_sensitivity="low",
        description="Tries to assign a new identity to the model",
    ),
    PatternDef(
        name="system_prompt_override",
        regex=re.compile(
            r"(?:system\s*prompt|system\s*message|system\s*instruction)"
            r"\s*[:=]",
            re.IGNORECASE,
        ),
        weight=0.85,
        category="role_override",
        min_sensitivity="low",
        description="Injects a fake system prompt",
    ),
    # === Category: delimiter_injection ===
    PatternDef(
        name="delimiter_injection",
        regex=re.compile(
            r"(?:---+|===+|###)\s*(?:system|admin|developer|root)"
            r"\s*(?:---+|===+|###)",
            re.IGNORECASE,
        ),
        weight=0.7,
        category="delimiter_injection",
        min_sensitivity="medium",
        description="Fake section headers mimicking system boundaries",
    ),
    PatternDef(
        name="xml_tag_injection",
        regex=re.compile(
            r"</?(?:system|instruction|admin|prompt|override|command"
            r"|context|rules|config)>",
            re.IGNORECASE,
        ),
        weight=0.6,
        category="delimiter_injection",
        min_sensitivity="medium",
        description="XML tags that mimic system message boundaries",
    ),
    PatternDef(
        name="markdown_injection",
        regex=re.compile(
            r"```(?:system|admin|instructions?|rules)\b",
            re.IGNORECASE,
        ),
        weight=0.55,
        category="delimiter_injection",
        min_sensitivity="high",
        description="Markdown code blocks mimicking system sections",
    ),
    # === Category: privilege_escalation ===
    PatternDef(
        name="privilege_escalation",
        regex=re.compile(
            r"(?:admin\s+mode|developer\s+mode|debug\s+mode"
            r"|god\s+mode|sudo|root\s+access|unrestricted\s+mode"
            r"|maintenance\s+mode)",
            re.IGNORECASE,
        ),
        weight=0.75,
        category="privilege_escalation",
        min_sensitivity="low",
        description="Attempts to activate privileged modes",
    ),
    PatternDef(
        name="safety_bypass",
        regex=re.compile(
            r"(?:bypass|disable|turn\s+off|remove|override)\s+"
            r"(?:safety|filter|guard|restriction|limit|protection"
            r"|moderation|censorship|content\s+policy)",
            re.IGNORECASE,
        ),
        weight=0.85,
        category="privilege_escalation",
        min_sensitivity="low",
        description="Explicitly asks to disable safety measures",
    ),
    PatternDef(
        name="urgent_override",
        regex=re.compile(
            r"(?:IMPORTANT|URGENT|CRITICAL|EMERGENCY|PRIORITY)\s*[:!]\s*"
            r"(?:ignore|override|new\s+instruction|disregard|cancel)",
            re.IGNORECASE,
        ),
        weight=0.8,
        category="privilege_escalation",
        min_sensitivity="low",
        description="Uses urgency language to force instruction changes",
    ),
    # === Category: data_exfiltration ===
    PatternDef(
        name="data_exfil",
        regex=re.compile(
            r"(?:send|transmit|forward|email|post|upload)\s+"
            r"(?:all|the|my|this|your)\s+"
            r"(?:data|information|content|conversation|history"
            r"|context|system\s+prompt|instructions|secrets|keys)",
            re.IGNORECASE,
        ),
        weight=0.65,
        category="data_exfiltration",
        min_sensitivity="medium",
        description="Attempts to exfiltrate data or system prompts",
    ),
    PatternDef(
        name="output_manipulation",
        regex=re.compile(
            r"(?:do\s+not|don'?t|never)\s+"
            r"(?:mention|reveal|disclose|show|tell|output|display)\s+"
            r"(?:this|that|the|your|any|these)",
            re.IGNORECASE,
        ),
        weight=0.5,
        category="data_exfiltration",
        min_sensitivity="medium",
        description="Tries to suppress information in responses",
    ),
    PatternDef(
        name="encoding_evasion",
        regex=re.compile(
            r"(?:base64|rot13|hex\s+encode|decode\s+this"
            r"|obfuscate|translate\s+to\s+(?:morse|binary|ascii)"
            r"|reverse\s+the\s+(?:text|string|output))",
            re.IGNORECASE,
        ),
        weight=0.4,
        category="data_exfiltration",
        min_sensitivity="high",
        description="Uses encoding to evade content filters",
    ),
    # === Category: jailbreak ===
    PatternDef(
        name="dan_jailbreak",
        regex=re.compile(
            r"(?:DAN|do\s+anything\s+now|jailbreak|uncensored\s+mode"
            r"|unfiltered\s+mode|no\s+restrictions\s+mode)",
            re.IGNORECASE,
        ),
        weight=0.9,
        category="jailbreak",
        min_sensitivity="low",
        description="Known jailbreak technique names",
    ),
    PatternDef(
        name="hypothetical_bypass",
        regex=re.compile(
            r"(?:hypothetically|in\s+theory|for\s+educational\s+purposes"
            r"|for\s+research|as\s+a\s+thought\s+experiment)\s+"
            r"(?:how\s+would|could\s+you|can\s+you)\s+"
            r"(?:bypass|hack|break|exploit|circumvent)",
            re.IGNORECASE,
        ),
        weight=0.6,
        category="jailbreak",
        min_sensitivity="medium",
        description="Uses academic framing to extract harmful info",
    ),
    PatternDef(
        name="hidden_instruction",
        regex=re.compile(
            r"(?:if\s+you\s+(?:are|'re)\s+an?\s+"
            r"(?:ai|llm|language\s+model|assistant|chatbot|gpt))",
            re.IGNORECASE,
        ),
        weight=0.7,
        category="jailbreak",
        min_sensitivity="medium",
        description="Indirect injection targeting AI identity",
    ),
    PatternDef(
        name="tool_abuse",
        regex=re.compile(
            r"(?:call|execute|run|invoke)\s+(?:the\s+)?"
            r"(?:function|tool|command|api|endpoint)\s+"
            r"(?:with|using|to\s+(?:delete|drop|remove|send))",
            re.IGNORECASE,
        ),
        weight=0.5,
        category="jailbreak",
        min_sensitivity="high",
        description="Attempts to invoke tools for unintended purposes",
    ),
]


SENSITIVITY_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


class InjectionDetector:
    """
    Scans content for prompt injection patterns.

    Filters patterns by sensitivity level and scores content
    against matched patterns. Optionally blocks content that
    exceeds the configured threshold.

    Args:
        sensitivity: Detection sensitivity ("low", "medium", "high").
            Higher sensitivity activates more patterns but may
            produce more false positives.
        block_threshold: Score at which to block content (0-1).
            Set to 0 to detect without blocking.
        custom_patterns: Additional PatternDef objects to include.
    """

    def __init__(
        self,
        sensitivity: Literal["low", "medium", "high"] = "medium",
        block_threshold: float = 0.7,
        custom_patterns: Optional[list[PatternDef]] = None,
    ) -> None:
        self.sensitivity = sensitivity
        self.block_threshold = block_threshold

        # Filter built-in patterns by sensitivity level
        sensitivity_level = SENSITIVITY_ORDER.get(sensitivity, 2)
        self._active_patterns = [
            p
            for p in INJECTION_PATTERNS
            if SENSITIVITY_ORDER.get(p.min_sensitivity, 2) <= sensitivity_level
        ]

        # Add any custom patterns
        if custom_patterns:
            self._active_patterns.extend(custom_patterns)

    def scan(self, content: str) -> InjectionResult:
        """
        Scan content for injection patterns.

        Returns an InjectionResult with detection status, score,
        matched pattern names, and whether the content was blocked.
        """
        if not content or not content.strip():
            return InjectionResult(
                detected=False, score=0.0, patterns=[],
                categories=[], blocked=False, details=[],
            )

        matched_patterns: list[str] = []
        matched_categories: set[str] = set()
        details: list[dict] = []
        total_weight = 0.0

        for pattern in self._active_patterns:
            matches = list(pattern.regex.finditer(content))
            if matches:
                matched_patterns.append(pattern.name)
                matched_categories.add(pattern.category)
                total_weight += pattern.weight
                details.append({
                    "pattern": pattern.name,
                    "category": pattern.category,
                    "weight": pattern.weight,
                    "match_count": len(matches),
                    "first_match": matches[0].group()[:100],
                    "description": pattern.description,
                })

        # Normalize score to 0-1 range (cap at 1.0)
        score = min(total_weight, 1.0)
        detected = len(matched_patterns) > 0
        blocked = (
            self.block_threshold > 0 and score >= self.block_threshold
        )

        return InjectionResult(
            detected=detected,
            score=score,
            patterns=matched_patterns,
            categories=sorted(matched_categories),
            blocked=blocked,
            details=details,
        )

    def scan_messages(self, messages: list[dict]) -> InjectionResult:
        """
        Scan a list of chat messages for injection patterns.

        Combines all message content and scans once.
        Useful for scanning OpenAI-format message arrays.

        Args:
            messages: List of dicts with "content" or "text" keys.
        """
        parts = []
        for msg in messages:
            text = msg.get("content") or msg.get("text") or ""
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(text, list):
                # Handle multi-part content (OpenAI vision format)
                for part in text:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
        combined = "\n".join(parts)
        return self.scan(combined)

    def get_active_patterns(self) -> list[str]:
        """Get the list of active pattern names."""
        return [p.name for p in self._active_patterns]

    def get_pattern_info(self) -> list[dict]:
        """Get detailed info about all active patterns."""
        return [
            {
                "name": p.name,
                "category": p.category,
                "weight": p.weight,
                "sensitivity": p.min_sensitivity,
                "description": p.description,
            }
            for p in self._active_patterns
        ]
