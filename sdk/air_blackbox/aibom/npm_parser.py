"""npm manifest and package-lock parsing for static dependency discovery."""

import json
from pathlib import Path
from typing import Any, Optional

from air_blackbox.aibom.classifier import AIClassifier, normalize_npm_package_name
from air_blackbox.aibom.dependency_utils import (
    check_manifest_size,
    exact_npm_version,
    make_component,
)
from air_blackbox.aibom.models import DependencyComponent, DependencyScope


def parse_package_json(
    path: Path,
    rel: str,
    classifier: AIClassifier,
    warnings: list[str],
    failed_manifests: list[str],
) -> list[DependencyComponent]:
    """Parse direct npm dependencies from package.json."""
    data = _read_json_manifest(path, rel, warnings, failed_manifests)
    if data is None:
        return []

    components: list[DependencyComponent] = []
    # devDependencies are intentionally excluded in this phase: they are not part
    # of the requested supported package.json fields.
    for section in ("dependencies", "optionalDependencies", "peerDependencies"):
        dependencies = data.get(section, {})
        if not isinstance(dependencies, dict):
            if dependencies:
                warnings.append(f"Ignoring non-object {section} in {rel}")
            continue
        for package_name, declaration in dependencies.items():
            version = exact_npm_version(str(declaration))
            components.append(
                make_component(
                    package_name=str(package_name),
                    version=version,
                    ecosystem="npm",
                    scope=DependencyScope.DIRECT,
                    source_manifest=rel,
                    parent_dependencies=[],
                    classifier=classifier,
                )
            )
    return components


def parse_package_lock(
    path: Path,
    rel: str,
    classifier: AIClassifier,
    warnings: list[str],
    failed_manifests: list[str],
) -> list[DependencyComponent]:
    """Parse npm package-lock dependencies and graph relationships."""
    data = _read_json_manifest(path, rel, warnings, failed_manifests)
    if data is None:
        return []

    packages = data.get("packages")
    if isinstance(packages, dict):
        sibling_package_json = _read_sibling_package_json(path, warnings)
        direct_names = _direct_names_from_sibling_package_json(sibling_package_json)
        direct_names.update(_direct_names_from_root_package(packages.get("", {})))
        direct_names.update(_direct_names_from_top_level_metadata(data))
        return _parse_package_lock_packages(
            packages,
            rel,
            classifier,
            warnings,
            direct_names,
        )

    dependencies = data.get("dependencies")
    if isinstance(dependencies, dict):
        return _parse_legacy_package_lock_dependencies(dependencies, rel, classifier)

    warnings.append(f"No supported dependency graph found in {rel}")
    return []


def _parse_package_lock_packages(
    packages: dict[str, Any],
    rel: str,
    classifier: AIClassifier,
    warnings: list[str],
    direct_names: set[str],
) -> list[DependencyComponent]:
    path_to_name: dict[str, str] = {}
    path_to_version: dict[str, Optional[str]] = {}
    direct_paths: set[str] = set()

    for package_path, entry in packages.items():
        if package_path == "" or not isinstance(entry, dict):
            continue
        name = _npm_name_from_lock_path(package_path, entry)
        if not name:
            continue
        normalized = normalize_npm_package_name(name)
        path_to_name[package_path] = normalized
        version = entry.get("version")
        path_to_version[package_path] = str(version) if version else None
        root_path = _join_lock_path("node_modules", normalized)
        if normalized in direct_names and package_path == root_path:
            direct_paths.add(package_path)

    components_by_path: dict[str, DependencyComponent] = {}
    for package_path, normalized in path_to_name.items():
        version = path_to_version[package_path]
        scope = (
            DependencyScope.DIRECT
            if package_path in direct_paths
            else DependencyScope.TRANSITIVE
        )
        components_by_path[package_path] = make_component(
            package_name=normalized,
            version=version,
            ecosystem="npm",
            scope=scope,
            source_manifest=rel,
            parent_dependencies=[],
            classifier=classifier,
        )

    for package_path, entry in packages.items():
        if package_path not in components_by_path or not isinstance(entry, dict):
            continue
        dependencies = entry.get("dependencies", {})
        if not isinstance(dependencies, dict):
            continue
        parent_id = components_by_path[package_path].package_id
        for dependency_name in dependencies:
            child_path = _resolve_lock_dependency_path(
                package_path,
                normalize_npm_package_name(str(dependency_name)),
                path_to_name,
                warnings,
                rel,
            )
            if child_path and parent_id:
                child = components_by_path[child_path]
                if parent_id not in child.parent_dependencies:
                    child.parent_dependencies.append(parent_id)

    return list(components_by_path.values())


def _parse_legacy_package_lock_dependencies(
    dependencies: dict[str, Any],
    rel: str,
    classifier: AIClassifier,
) -> list[DependencyComponent]:
    components: dict[tuple[str, str, Optional[str]], DependencyComponent] = {}

    def visit(
        package_name: str,
        entry: Any,
        scope: DependencyScope,
        parent_id: Optional[str],
        trail: set[str],
    ) -> None:
        normalized = normalize_npm_package_name(package_name)
        if normalized in trail:
            return
        version = (
            str(entry.get("version"))
            if isinstance(entry, dict) and entry.get("version")
            else None
        )
        component = make_component(
            package_name=package_name,
            version=version,
            ecosystem="npm",
            scope=scope,
            source_manifest=rel,
            parent_dependencies=[parent_id] if parent_id else [],
            classifier=classifier,
        )
        _merge_legacy_component(components, component)
        child_parent_id = component.package_id
        child_dependencies = (
            entry.get("dependencies", {}) if isinstance(entry, dict) else {}
        )
        if not isinstance(child_dependencies, dict):
            return
        for child_name, child_entry in child_dependencies.items():
            visit(
                str(child_name),
                child_entry,
                DependencyScope.TRANSITIVE,
                child_parent_id,
                trail | {normalized},
            )

    for package_name, entry in dependencies.items():
        visit(str(package_name), entry, DependencyScope.DIRECT, None, set())
    return list(components.values())


def _read_json_manifest(
    path: Path,
    rel: str,
    warnings: list[str],
    failed_manifests: list[str],
) -> Optional[dict[str, Any]]:
    if not check_manifest_size(path, path.parent, warnings):
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        failed_manifests.append(rel)
        warnings.append(f"Malformed JSON in {rel}: {exc}")
        return None
    if not isinstance(data, dict):
        failed_manifests.append(rel)
        warnings.append(f"JSON manifest must be an object: {rel}")
        return None
    return data


def _read_sibling_package_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    sibling = path.with_name("package.json")
    if not sibling.exists() or sibling.is_symlink():
        return {}
    if not check_manifest_size(sibling, path.parent, warnings):
        return {}
    try:
        with sibling.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        warnings.append(f"Could not read sibling package.json: {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def _direct_names_from_sibling_package_json(data: dict[str, Any]) -> set[str]:
    return _direct_names_from_dependency_sections(data, require_string_values=False)


def _direct_names_from_root_package(root: Any) -> set[str]:
    if not isinstance(root, dict):
        return set()
    return _direct_names_from_dependency_sections(root, require_string_values=False)


def _direct_names_from_top_level_metadata(data: dict[str, Any]) -> set[str]:
    # Top-level package-lock "dependencies" is usually the full lock graph. Only
    # treat string-valued metadata as root declarations.
    return _direct_names_from_dependency_sections(data, require_string_values=True)


def _direct_names_from_dependency_sections(
    data: dict[str, Any],
    require_string_values: bool,
) -> set[str]:
    names: set[str] = set()
    for section in ("dependencies", "optionalDependencies", "peerDependencies"):
        values = data.get(section, {})
        if not isinstance(values, dict):
            continue
        for name, declaration in values.items():
            if require_string_values and not isinstance(declaration, str):
                continue
            names.add(normalize_npm_package_name(str(name)))
    return names


def _npm_name_from_lock_path(package_path: str, entry: dict[str, Any]) -> Optional[str]:
    entry_name = entry.get("name")
    if isinstance(entry_name, str) and entry_name:
        return entry_name
    parts = package_path.replace("\\", "/").split("/")
    try:
        index = len(parts) - 1 - parts[::-1].index("node_modules")
    except ValueError:
        return None
    if index + 1 >= len(parts):
        return None
    first = parts[index + 1]
    if first.startswith("@") and index + 2 < len(parts):
        return f"{first}/{parts[index + 2]}"
    return first


def _resolve_lock_dependency_path(
    package_path: str,
    dependency_name: str,
    path_to_name: dict[str, str],
    warnings: list[str],
    rel: str,
) -> Optional[str]:
    normalized_path = package_path.replace("\\", "/")
    candidates: list[str] = []
    current = normalized_path
    while current:
        candidates.append(_join_lock_path(current, "node_modules", dependency_name))
        if "/node_modules/" not in current:
            break
        current = current.rsplit("/node_modules/", 1)[0]
    candidates.append(_join_lock_path("node_modules", dependency_name))
    for candidate in candidates:
        if path_to_name.get(candidate) == dependency_name:
            return candidate

    same_name_paths = [
        candidate_path
        for candidate_path, candidate_name in sorted(path_to_name.items())
        if candidate_name == dependency_name
    ]
    if len(same_name_paths) == 1:
        return same_name_paths[0]
    if len(same_name_paths) > 1:
        warnings.append(
            f"Ambiguous package-lock dependency edge in {rel}: "
            f"{package_path} -> {dependency_name}"
        )
    return None


def _join_lock_path(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part)


def _merge_legacy_component(
    components: dict[tuple[str, str, Optional[str]], DependencyComponent],
    incoming: DependencyComponent,
) -> None:
    key = (incoming.ecosystem, incoming.normalized_name, incoming.version)
    existing = components.get(key)
    if not existing:
        components[key] = incoming
        return
    existing.parent_dependencies = sorted(
        set(existing.parent_dependencies) | set(incoming.parent_dependencies)
    )
