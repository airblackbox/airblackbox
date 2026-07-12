"""Static dependency discovery orchestration for AI-BOM generation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from air_blackbox.aibom.classifier import AIClassifier
from air_blackbox.aibom.dependency_utils import (
    build_package_id,
    iter_manifest_candidates,
    merge_source_manifest,
    path_for_display,
)
from air_blackbox.aibom.models import DependencyComponent, DependencyScope
from air_blackbox.aibom.npm_parser import parse_package_json, parse_package_lock
from air_blackbox.aibom.pyproject_parser import parse_pyproject
from air_blackbox.aibom.requirements_parser import parse_requirements_file


@dataclass
class DependencyDiscoveryResult:
    """Result of scanning dependency manifests under a project path."""

    dependencies: list[DependencyComponent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    inspected_manifests: list[str] = field(default_factory=list)
    failed_manifests: list[str] = field(default_factory=list)


def discover_dependencies(
    scan_path: str | Path,
    classifier: AIClassifier,
) -> DependencyDiscoveryResult:
    """Discover package dependencies from supported manifests under scan_path."""
    base = Path(scan_path).resolve()
    result = DependencyDiscoveryResult()
    if not base.exists():
        result.warnings.append(f"Scan path does not exist: {scan_path}")
        return result

    components: dict[tuple[str, str, Optional[str]], DependencyComponent] = {}
    manifests, traversal_warnings = iter_manifest_candidates(base)
    result.warnings.extend(traversal_warnings)

    for manifest in manifests:
        rel = path_for_display(manifest, base)
        result.inspected_manifests.append(rel)
        before_failures = len(result.failed_manifests)
        try:
            discovered = _parse_manifest(manifest, rel, base, classifier, result)
        except Exception as exc:  # Defensive: malformed project files should not abort.
            result.failed_manifests.append(rel)
            result.warnings.append(f"Failed to parse {rel}: {exc}")
            continue
        if len(result.failed_manifests) > before_failures:
            continue
        for component in discovered:
            _merge_component(components, component)

    result.inspected_manifests = sorted(set(result.inspected_manifests))
    result.failed_manifests = sorted(set(result.failed_manifests))
    result.dependencies = sorted(
        components.values(),
        key=lambda c: (c.ecosystem, c.normalized_name, c.version or ""),
    )
    return result


def _parse_manifest(
    manifest: Path,
    rel: str,
    base: Path,
    classifier: AIClassifier,
    result: DependencyDiscoveryResult,
) -> list[DependencyComponent]:
    name = manifest.name
    if name == "requirements.txt":
        return parse_requirements_file(
            manifest,
            base,
            classifier,
            result.warnings,
            result.inspected_manifests,
            result.failed_manifests,
        )
    if name == "pyproject.toml":
        return parse_pyproject(
            manifest,
            rel,
            classifier,
            result.warnings,
            result.failed_manifests,
        )
    if name == "package.json":
        return parse_package_json(
            manifest,
            rel,
            classifier,
            result.warnings,
            result.failed_manifests,
        )
    if name == "package-lock.json":
        return parse_package_lock(
            manifest,
            rel,
            classifier,
            result.warnings,
            result.failed_manifests,
        )
    return []


def _merge_component(
    components: dict[tuple[str, str, Optional[str]], DependencyComponent],
    incoming: DependencyComponent,
) -> None:
    target_key = _find_merge_key(components, incoming)
    if target_key is None:
        components[_component_key(incoming)] = incoming
        return

    existing = components[target_key]
    if _should_replace_identity(existing, incoming):
        del components[target_key]
        existing.version = incoming.version
        existing.package_id = incoming.package_id
        target_key = _component_key(existing)
        components[target_key] = existing
    existing.scope = _merge_scope(existing.scope, incoming.scope)
    existing.source_manifest = merge_source_manifest(
        existing.source_manifest,
        incoming.source_manifest,
    )
    existing.parent_dependencies = sorted(
        set(existing.parent_dependencies) | set(incoming.parent_dependencies)
    )
    if incoming.ai_classification.is_ai:
        existing.ai_classification = incoming.ai_classification


def _find_merge_key(
    components: dict[tuple[str, str, Optional[str]], DependencyComponent],
    incoming: DependencyComponent,
) -> Optional[tuple[str, str, Optional[str]]]:
    exact_key = _component_key(incoming)
    if exact_key in components:
        return exact_key

    same_name_keys = [
        key
        for key, component in components.items()
        if component.ecosystem == incoming.ecosystem
        and component.normalized_name == incoming.normalized_name
    ]
    if _is_direct_lock_component(incoming):
        direct_manifest_keys = [
            key
            for key in same_name_keys
            if _is_package_json_component(components[key])
            and components[key].scope == DependencyScope.DIRECT
        ]
        if len(direct_manifest_keys) == 1:
            return direct_manifest_keys[0]

    if _is_package_json_component(incoming):
        direct_lock_keys = [
            key for key in same_name_keys if _is_direct_lock_component(components[key])
        ]
        if len(direct_lock_keys) == 1:
            return direct_lock_keys[0]

    return None


def _should_replace_identity(
    existing: DependencyComponent,
    incoming: DependencyComponent,
) -> bool:
    if _is_direct_lock_component(incoming) and _is_package_json_component(existing):
        return existing.version != incoming.version
    return False


def _component_key(component: DependencyComponent) -> tuple[str, str, Optional[str]]:
    return (component.ecosystem, component.normalized_name, component.version)


def _is_direct_lock_component(component: DependencyComponent) -> bool:
    return (
        _has_source_manifest(component, "package-lock.json")
        and component.scope == DependencyScope.DIRECT
    )


def _is_package_json_component(component: DependencyComponent) -> bool:
    return _has_source_manifest(component, "package.json") and not _has_source_manifest(
        component,
        "package-lock.json",
    )


def _has_source_manifest(component: DependencyComponent, manifest_name: str) -> bool:
    if not component.source_manifest:
        return False
    return any(
        part.endswith(manifest_name) for part in component.source_manifest.split(",")
    )


def _merge_scope(left: DependencyScope, right: DependencyScope) -> DependencyScope:
    precedence = {
        DependencyScope.DIRECT: 3,
        DependencyScope.TRANSITIVE: 2,
        DependencyScope.UNKNOWN: 1,
    }
    return left if precedence[left] >= precedence[right] else right


__all__ = [
    "DependencyDiscoveryResult",
    "build_package_id",
    "discover_dependencies",
]
