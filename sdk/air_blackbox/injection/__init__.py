"""Prompt injection detection and prevention.

Provides tools for detecting and mitigating prompt injection attacks
in AI system inputs and interactions.
"""

from air_blackbox.injection.detector import (
    InjectionDetector,
    InjectionResult,
    PatternDef,
)

__all__ = [
    "InjectionDetector",
    "InjectionResult",
    "PatternDef",
]
