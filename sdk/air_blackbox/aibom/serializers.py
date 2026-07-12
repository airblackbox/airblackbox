"""CycloneDX and SPDX serializers for normalized AI-BOM inventories."""

import hashlib
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from air_blackbox.aibom.models import (
    AIBOMInventory,
    DependencyComponent,
    DependencyScope,
    RuntimeModelComponent,
)

PROP_PREFIX = "air-blackbox"
NOASSERTION = "NOASSERTION"


def to_cyclonedx(
    inventory: AIBOMInventory,
    metadata: Optional[dict] = None,
) -> dict:
    """Serialize an inventory as CycloneDX 1.6 JSON."""
    meta = metadata or {}
    root_ref = _root_ref(meta)
    components: list[dict] = []

    dependency_ref_by_package_id: dict[str, str] = {}
    for dependency in _sorted_dependencies(inventory.dependencies):
        component = _dependency_to_cyclonedx_component(dependency)
        components.append(component)
        if dependency.package_id:
            dependency_ref_by_package_id[dependency.package_id] = component["bom-ref"]

    runtime_refs: list[str] = []
    for model in _sorted_models(inventory.runtime_models):
        component = _model_to_cyclonedx_component(model)
        components.append(component)
        runtime_refs.append(component["bom-ref"])
    for provider in sorted(set(inventory.runtime_providers)):
        component = _provider_to_cyclonedx_component(provider)
        components.append(component)
        runtime_refs.append(component["bom-ref"])
    for tool in sorted(set(inventory.runtime_tools)):
        component = _tool_to_cyclonedx_component(tool)
        components.append(component)
        runtime_refs.append(component["bom-ref"])

    direct_package_refs = [
        dependency_ref_by_package_id[dependency.package_id]
        for dependency in _sorted_dependencies(inventory.dependencies)
        if dependency.package_id
        and dependency.scope == DependencyScope.DIRECT
        and dependency.package_id in dependency_ref_by_package_id
    ]
    graph: dict[str, set[str]] = {
        root_ref: set(direct_package_refs) | set(runtime_refs),
    }
    for dependency in _sorted_dependencies(inventory.dependencies):
        if not dependency.package_id:
            continue
        child_ref = dependency_ref_by_package_id.get(dependency.package_id)
        if not child_ref:
            continue
        for parent_id in sorted(set(dependency.parent_dependencies)):
            parent_ref = dependency_ref_by_package_id.get(parent_id)
            if parent_ref:
                graph.setdefault(parent_ref, set()).add(child_ref)

    component_refs = {component["bom-ref"] for component in components}
    dependencies = [
        {"ref": ref, "dependsOn": sorted(depends_on)}
        for ref, depends_on in sorted(graph.items())
        if ref == root_ref or ref in component_refs
    ]
    for ref in sorted(component_refs - set(graph)):
        dependencies.append({"ref": ref, "dependsOn": []})

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": meta.get("serial_number")
        or meta.get("serialNumber")
        or f"urn:uuid:{uuid.uuid4()}",
        "version": int(meta.get("version", 1)),
        "metadata": _cyclonedx_metadata(meta, root_ref),
        "components": sorted(components, key=lambda component: component["bom-ref"]),
        "dependencies": sorted(dependencies, key=lambda item: item["ref"]),
    }


def to_spdx(
    inventory: AIBOMInventory,
    metadata: Optional[dict] = None,
) -> dict:
    """Serialize an inventory as SPDX 2.3 JSON."""
    meta = metadata or {}
    root_spdx_id = _root_spdx_id(meta)
    packages: list[dict] = [_root_spdx_package(meta, root_spdx_id)]
    annotations: list[dict] = []

    dependency_spdx_by_package_id: dict[str, str] = {}
    for dependency in _sorted_dependencies(inventory.dependencies):
        package = _dependency_to_spdx_package(dependency)
        packages.append(package)
        if dependency.package_id:
            dependency_spdx_by_package_id[dependency.package_id] = package["SPDXID"]
        annotations.append(
            _spdx_annotation(
                package["SPDXID"],
                _dependency_annotation_comment(dependency),
                meta,
            )
        )

    runtime_spdx_ids: list[str] = []
    for model in _sorted_models(inventory.runtime_models):
        package = _model_to_spdx_package(model)
        packages.append(package)
        runtime_spdx_ids.append(package["SPDXID"])
        annotations.append(
            _spdx_annotation(package["SPDXID"], _model_annotation_comment(model), meta)
        )
    for provider in sorted(set(inventory.runtime_providers)):
        package = _provider_to_spdx_package(provider)
        packages.append(package)
        runtime_spdx_ids.append(package["SPDXID"])
    for tool in sorted(set(inventory.runtime_tools)):
        package = _tool_to_spdx_package(tool)
        packages.append(package)
        runtime_spdx_ids.append(package["SPDXID"])

    relationships: set[tuple[str, str, str]] = {
        ("SPDXRef-DOCUMENT", "DESCRIBES", root_spdx_id),
    }
    for dependency in _sorted_dependencies(inventory.dependencies):
        if not dependency.package_id:
            continue
        child_id = dependency_spdx_by_package_id.get(dependency.package_id)
        if not child_id:
            continue
        if dependency.scope == DependencyScope.DIRECT:
            relationships.add((root_spdx_id, "DEPENDS_ON", child_id))
        for parent_id in sorted(set(dependency.parent_dependencies)):
            parent_spdx_id = dependency_spdx_by_package_id.get(parent_id)
            if parent_spdx_id:
                relationships.add((parent_spdx_id, "DEPENDS_ON", child_id))
    for runtime_id in sorted(runtime_spdx_ids):
        relationships.add((root_spdx_id, "DEPENDS_ON", runtime_id))

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": meta.get("document_name")
        or meta.get("name")
        or meta.get("project_name")
        or "AIR Blackbox AI-BOM",
        "documentNamespace": meta.get("document_namespace")
        or meta.get("documentNamespace")
        or f"https://airblackbox.ai/spdx/{uuid.uuid4()}",
        "creationInfo": {
            "created": _timestamp(meta),
            "creators": [
                f"Tool: {meta.get('tool_name', 'air-blackbox')}-"
                f"{meta.get('tool_version', meta.get('toolVersion', 'unknown'))}"
            ],
        },
        "packages": sorted(packages, key=lambda package: package["SPDXID"]),
        "relationships": [
            {
                "spdxElementId": source,
                "relationshipType": relationship_type,
                "relatedSpdxElement": target,
            }
            for source, relationship_type, target in sorted(relationships)
        ],
        "annotations": sorted(
            annotations,
            key=lambda annotation: (
                annotation["SPDXID"],
                annotation["annotationDate"],
                annotation["comment"],
            ),
        ),
    }


def _cyclonedx_metadata(meta: dict, root_ref: str) -> dict:
    component: dict[str, Any] = {
        "type": "application",
        "bom-ref": root_ref,
        "name": meta.get("project_name") or meta.get("system_name") or "AI System",
        "description": meta.get(
            "description",
            "AI system inventoried by AIR Blackbox",
        ),
    }
    project_version = meta.get("project_version") or meta.get("system_version")
    if project_version:
        component["version"] = project_version
    return {
        "timestamp": _timestamp(meta),
        "tools": {
            "components": [
                {
                    "type": "application",
                    "name": meta.get("tool_name", "air-blackbox"),
                    "version": meta.get("tool_version")
                    or meta.get("toolVersion")
                    or "unknown",
                    "description": "AI governance control plane",
                    "publisher": "AIR Blackbox",
                }
            ]
        },
        "component": component,
    }


def _dependency_to_cyclonedx_component(dependency: DependencyComponent) -> dict:
    component: dict[str, Any] = {
        "type": "library",
        "bom-ref": _dependency_ref(dependency),
        "name": dependency.package_name,
    }
    if dependency.version:
        component["version"] = dependency.version
    if dependency.package_id:
        component["purl"] = dependency.package_id
    properties = [
        _property("ecosystem", dependency.ecosystem),
        _property("dependency-scope", dependency.scope.value),
        _property("ai-dependency", str(dependency.ai_classification.is_ai).lower()),
    ]
    if dependency.source_manifest:
        properties.append(_property("source-manifest", dependency.source_manifest))
    classification = dependency.ai_classification
    if classification.category:
        properties.append(_property("ai-category", classification.category))
    if classification.reason:
        properties.append(_property("classification-reason", classification.reason))
    if classification.matched_rule:
        properties.append(_property("matched-rule", classification.matched_rule))
    if classification.provider:
        properties.append(_property("provider", classification.provider))
    component["properties"] = sorted(properties, key=lambda item: item["name"])
    return component


def _model_to_cyclonedx_component(model: RuntimeModelComponent) -> dict:
    component: dict[str, Any] = {
        "type": "machine-learning-model",
        "bom-ref": _model_ref(model),
        "name": model.model_name,
        "description": "LLM observed in runtime traffic via AIR Blackbox",
    }
    if model.model_version:
        component["version"] = model.model_version
    if model.model_provider:
        component["publisher"] = model.model_provider
    properties = [
        _property("detection-method", "runtime-observation"),
        _property("observed-runs", str(model.observed_runs)),
        _property("observed-tokens", str(model.observed_tokens)),
    ]
    if model.model_provider:
        properties.append(_property("provider", model.model_provider))
    component["properties"] = sorted(properties, key=lambda item: item["name"])
    return component


def _provider_to_cyclonedx_component(provider: str) -> dict:
    return {
        "type": "platform",
        "bom-ref": _provider_ref(provider),
        "name": f"{provider} API",
        "publisher": provider,
        "description": "AI API provider observed in runtime traffic",
        "properties": [_property("detection-method", "runtime-observation")],
    }


def _tool_to_cyclonedx_component(tool: str) -> dict:
    return {
        "type": "application",
        "bom-ref": _tool_ref(tool),
        "name": tool,
        "description": "Agent tool observed in runtime traffic",
        "properties": [_property("detection-method", "runtime-observation")],
    }


def _root_spdx_package(meta: dict, spdx_id: str) -> dict:
    package = {
        "name": meta.get("project_name") or meta.get("system_name") or "AI System",
        "SPDXID": spdx_id,
        "downloadLocation": NOASSERTION,
        "filesAnalyzed": False,
        "versionInfo": meta.get("project_version")
        or meta.get("system_version")
        or NOASSERTION,
    }
    return package


def _dependency_to_spdx_package(dependency: DependencyComponent) -> dict:
    package = {
        "name": dependency.package_name,
        "SPDXID": _dependency_spdx_id(dependency),
        "downloadLocation": NOASSERTION,
        "filesAnalyzed": False,
        "versionInfo": dependency.version or NOASSERTION,
    }
    if dependency.ai_classification.provider:
        package["supplier"] = f"Organization: {dependency.ai_classification.provider}"
    if dependency.package_id and dependency.package_id.startswith("pkg:"):
        package["externalRefs"] = [
            {
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": dependency.package_id,
            }
        ]
    return package


def _model_to_spdx_package(model: RuntimeModelComponent) -> dict:
    package = {
        "name": model.model_name,
        "SPDXID": _model_spdx_id(model),
        "downloadLocation": NOASSERTION,
        "filesAnalyzed": False,
        "versionInfo": model.model_version or NOASSERTION,
        "supplier": (
            f"Organization: {model.model_provider}"
            if model.model_provider
            else NOASSERTION
        ),
    }
    return package


def _provider_to_spdx_package(provider: str) -> dict:
    return {
        "name": f"{provider} API",
        "SPDXID": _provider_spdx_id(provider),
        "downloadLocation": NOASSERTION,
        "filesAnalyzed": False,
        "versionInfo": NOASSERTION,
        "supplier": f"Organization: {provider}",
    }


def _tool_to_spdx_package(tool: str) -> dict:
    return {
        "name": tool,
        "SPDXID": _tool_spdx_id(tool),
        "downloadLocation": NOASSERTION,
        "filesAnalyzed": False,
        "versionInfo": NOASSERTION,
    }


def _dependency_annotation_comment(dependency: DependencyComponent) -> str:
    classification = dependency.ai_classification
    fields = {
        "air-blackbox:ai-dependency": str(classification.is_ai).lower(),
        "air-blackbox:dependency-scope": dependency.scope.value,
    }
    if dependency.source_manifest:
        fields["air-blackbox:source-manifest"] = dependency.source_manifest
    if classification.category:
        fields["air-blackbox:ai-category"] = classification.category
    if classification.reason:
        fields["air-blackbox:classification-reason"] = classification.reason
    if classification.matched_rule:
        fields["air-blackbox:matched-rule"] = classification.matched_rule
    if classification.provider:
        fields["air-blackbox:provider"] = classification.provider
    return _annotation_comment(fields)


def _model_annotation_comment(model: RuntimeModelComponent) -> str:
    fields = {
        "air-blackbox:model": "true",
        "air-blackbox:detection-method": "runtime-observation",
        "air-blackbox:observed-runs": str(model.observed_runs),
        "air-blackbox:observed-tokens": str(model.observed_tokens),
    }
    if model.model_provider:
        fields["air-blackbox:provider"] = model.model_provider
    if model.model_version:
        fields["air-blackbox:model-version"] = model.model_version
    return _annotation_comment(fields)


def _spdx_annotation(spdx_id: str, comment: str, meta: dict) -> dict:
    return {
        "SPDXID": spdx_id,
        "annotationDate": _timestamp(meta),
        "annotationType": "OTHER",
        "annotator": f"Tool: {meta.get('tool_name', 'air-blackbox')}",
        "comment": comment,
    }


def _annotation_comment(fields: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in sorted(fields.items()))


def _property(name: str, value: str) -> dict:
    return {"name": f"{PROP_PREFIX}:{name}", "value": value}


def _sorted_dependencies(
    dependencies: list[DependencyComponent],
) -> list[DependencyComponent]:
    return sorted(
        dependencies,
        key=lambda item: (
            item.ecosystem,
            item.normalized_name,
            item.version or "",
            item.package_id or "",
        ),
    )


def _sorted_models(models: list[RuntimeModelComponent]) -> list[RuntimeModelComponent]:
    return sorted(
        models,
        key=lambda item: (
            item.model_name,
            item.model_provider or "",
            item.model_version or "",
        ),
    )


def _dependency_ref(dependency: DependencyComponent) -> str:
    return dependency.package_id or _stable_ref(
        "pkg",
        dependency.ecosystem,
        dependency.normalized_name,
        dependency.version or "unknown",
    )


def _model_ref(model: RuntimeModelComponent) -> str:
    return _stable_ref(
        "model",
        model.model_provider or "unknown",
        model.model_name,
        model.model_version or "unknown",
    )


def _provider_ref(provider: str) -> str:
    return _stable_ref("service", provider)


def _tool_ref(tool: str) -> str:
    return _stable_ref("tool", tool)


def _root_ref(meta: dict) -> str:
    return meta.get("root_bom_ref") or _stable_ref(
        "root",
        meta.get("project_name") or meta.get("system_name") or "AI System",
    )


def _dependency_spdx_id(dependency: DependencyComponent) -> str:
    return _spdx_id(
        "Package",
        dependency.ecosystem,
        dependency.normalized_name,
        dependency.version or "unknown",
        dependency.package_id or "",
    )


def _model_spdx_id(model: RuntimeModelComponent) -> str:
    return _spdx_id(
        "Model",
        model.model_provider or "unknown",
        model.model_name,
        model.model_version or "unknown",
    )


def _provider_spdx_id(provider: str) -> str:
    return _spdx_id("Provider", provider)


def _tool_spdx_id(tool: str) -> str:
    return _spdx_id("Tool", tool)


def _root_spdx_id(meta: dict) -> str:
    return meta.get("root_spdx_id") or _spdx_id(
        "Root",
        meta.get("project_name") or meta.get("system_name") or "AI System",
    )


def _stable_ref(prefix: str, *parts: str) -> str:
    raw = ":".join(str(part) for part in parts)
    return f"{prefix}:{_sanitize_ref(raw)}:{_short_hash(raw)}"


def _spdx_id(prefix: str, *parts: str) -> str:
    raw = ":".join(str(part) for part in parts)
    safe = re.sub(r"[^A-Za-z0-9.-]+", "-", raw).strip("-") or "unknown"
    return f"SPDXRef-{prefix}-{safe}-{_short_hash(raw)}"


def _sanitize_ref(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@/+~-]+", "-", value).strip("-") or "unknown"


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _timestamp(meta: dict) -> str:
    return (
        meta.get("timestamp")
        or datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    )
