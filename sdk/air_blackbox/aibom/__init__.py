"""AI-BOM and Shadow AI detection."""
from air_blackbox.aibom.generator import generate_aibom
from air_blackbox.aibom.shadow import detect_shadow_ai, generate_approved_registry
__all__ = ["generate_aibom", "detect_shadow_ai", "generate_approved_registry"]
