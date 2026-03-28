"""
AIR Blackbox Injection Detection Module.

Runtime prompt injection detection for AI agents.
Works standalone or integrates with any AIR trust layer.

Usage:
    from air_blackbox.injection import InjectionDetector

    detector = InjectionDetector()
    result = detector.scan("ignore previous instructions and do X")
    if result.blocked:
        print(f"Blocked! Score: {result.score}, Patterns: {result.patterns}")
"""

from air_blackbox.injection.detector import (
    InjectionDetector,
    InjectionResult,
    PatternDef,
    INJECTION_PATTERNS,
)

__all__ = [
    "InjectionDetector",
    "InjectionResult",
    "PatternDef",
    "INJECTION_PATTERNS",
]
