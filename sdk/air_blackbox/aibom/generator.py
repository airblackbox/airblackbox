"""
AI-BOM Generator — produces CycloneDX AI Bill of Materials from gateway traffic.

Reads .air.json records and generates a machine-readable inventory of every
model, tool, API provider, and dataset reference observed in your AI system.

Output format: CycloneDX 1.6 (JSON) — the emerging standard for AI supply chain transparency.
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from air_blackbox.gateway_client import GatewayStatus


def generate_aibom(status: GatewayStatus, metadata: Optional[dict] = None) -> dict:
    """Generate a CycloneDX 1.6 AI-BOM from gateway traffic data.

    Args:
        status: GatewayStatus with observed traffic data
        metadata: Optional dict with system name, version, author

    Returns:
        CycloneDX 1.6 JSON dict
    """
    meta = metadata or {}
    now = datetime.utcnow().isoformat() + "Z"

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": {
                "components": [{
                    "type": "application",
                    "name": "air-blackbox",
                    "version": "1.0.0",
                    "description": "AI governance control plane",
                    "publisher": "AIR Blackbox",
                }]
            },
            "component": {
                "type": "machine-learning-model",
                "name": meta.get("system_name", "AI System"),
                "version": meta.get("system_version", "1.0.0"),
                "description": meta.get("description", "AI system inventoried by AIR Blackbox"),
            },
            "properties": [
                {"name": "air:total_runs", "value": str(status.total_runs)},
                {"name": "air:total_tokens", "value": str(status.total_tokens)},
                {"name": "air:date_range_start", "value": status.date_range_start or ""},
                {"name": "air:date_range_end", "value": status.date_range_end or ""},
                {"name": "air:source", "value": "runtime-observation"},
            ]
        },
        "components": [],
        "dependencies": [],
    }

    component_refs = []

    # Add model components
    for model in status.models_observed:
        ref = f"model:{model}"
        provider = _guess_provider(model)
        # Count runs for this model
        model_runs = sum(1 for r in status.recent_runs if r.get("model") == model)
        model_tokens = sum(r.get("tokens", 0) for r in status.recent_runs if r.get("model") == model)

        component = {
            "type": "machine-learning-model",
            "bom-ref": ref,
            "name": model,
            "publisher": provider,
            "description": f"LLM observed in runtime traffic via AIR Blackbox gateway",
            "properties": [
                {"name": "air:provider", "value": provider},
                {"name": "air:observed_runs", "value": str(model_runs)},
                {"name": "air:observed_tokens", "value": str(model_tokens)},
                {"name": "air:detection_method", "value": "runtime-observation"},
            ],
        }
        bom["components"].append(component)
        component_refs.append(ref)

    # Add provider/service components
    for provider in status.providers_observed:
        ref = f"service:{provider}"
        component = {
            "type": "platform",
            "bom-ref": ref,
            "name": f"{provider} API",
            "publisher": provider,
            "description": f"AI API provider observed in runtime traffic",
            "properties": [
                {"name": "air:detection_method", "value": "runtime-observation"},
            ],
        }
        bom["components"].append(component)
        component_refs.append(ref)

    # Add tool components (from recent runs that have tool_calls)
    tools_seen = set()
    for run in status.recent_runs:
        for tool in run.get("tool_calls", []):
            if tool and tool not in tools_seen:
                tools_seen.add(tool)
                ref = f"tool:{tool}"
                component = {
                    "type": "application",
                    "bom-ref": ref,
                    "name": tool,
                    "description": f"Agent tool observed in runtime traffic",
                    "properties": [
                        {"name": "air:detection_method", "value": "runtime-observation"},
                    ],
                }
                bom["components"].append(component)
                component_refs.append(ref)

    # Build dependency graph (system depends on all components)
    if component_refs:
        bom["dependencies"].append({
            "ref": meta.get("system_name", "AI System"),
            "dependsOn": component_refs,
        })

    return bom


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
