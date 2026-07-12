"""
AI-BOM Generator - produces CycloneDX AI Bill of Materials from gateway traffic.

Reads .air.json-derived GatewayStatus data and generates a machine-readable
inventory of every model, API provider, and tool observed in your AI system.
"""

from typing import Optional

from air_blackbox.aibom.models import AIBOMInventory, RuntimeModelComponent
from air_blackbox.aibom.serializers import to_cyclonedx
from air_blackbox.gateway_client import GatewayStatus


def generate_aibom(
    status: GatewayStatus,
    metadata: Optional[dict] = None,
    dependencies: Optional[list] = None,
    inventory: Optional[AIBOMInventory] = None,
) -> dict:
    """Generate a CycloneDX 1.6 AI-BOM from gateway traffic data.

    Args:
        status: GatewayStatus with observed traffic data.
        metadata: Optional dict with project/system metadata.
        dependencies: Optional static DependencyComponent list.
        inventory: Optional complete inventory. When supplied, status is ignored.

    Returns:
        CycloneDX 1.6 JSON dict.
    """
    bom_inventory = inventory or inventory_from_status(status, dependencies or [])
    meta = dict(metadata or {})
    meta.setdefault("project_name", meta.get("system_name", "AI System"))
    meta.setdefault("description", "AI system inventoried by AIR Blackbox")
    meta.setdefault("tool_name", "air-blackbox")
    meta.setdefault("tool_version", "1.0.0")
    return to_cyclonedx(bom_inventory, meta)


def inventory_from_status(
    status: GatewayStatus,
    dependencies: Optional[list] = None,
    warnings: Optional[list[str]] = None,
) -> AIBOMInventory:
    """Build the normalized AI-BOM inventory from runtime gateway status."""
    runtime_models = []
    for model in status.models_observed:
        provider = _guess_provider(model)
        model_runs = sum(1 for run in status.recent_runs if run.get("model") == model)
        model_tokens = sum(
            run.get("tokens", 0)
            for run in status.recent_runs
            if run.get("model") == model
        )
        runtime_models.append(
            RuntimeModelComponent(
                model_name=model,
                model_provider=provider if provider != "Unknown" else None,
                model_version=None,
                observed_runs=model_runs,
                observed_tokens=model_tokens,
            )
        )

    runtime_tools = sorted(
        {
            tool
            for run in status.recent_runs
            for tool in run.get("tool_calls", [])
            if tool
        }
    )
    return AIBOMInventory(
        runtime_models=runtime_models,
        runtime_providers=sorted(status.providers_observed),
        runtime_tools=runtime_tools,
        dependencies=list(dependencies or []),
        warnings=list(warnings or []),
    )


def _guess_provider(model: str) -> str:
    """Guess the provider from model name."""
    model_lower = model.lower()
    if any(x in model_lower for x in ["gpt", "o1", "o3", "dall-e"]):
        return "OpenAI"
    if any(x in model_lower for x in ["claude", "sonnet", "haiku", "opus"]):
        return "Anthropic"
    if any(x in model_lower for x in ["gemini", "palm", "gemma"]):
        return "Google"
    if any(x in model_lower for x in ["llama", "codellama"]):
        return "Meta"
    if any(x in model_lower for x in ["mistral", "mixtral"]):
        return "Mistral AI"
    if any(x in model_lower for x in ["command", "embed"]):
        return "Cohere"
    return "Unknown"
