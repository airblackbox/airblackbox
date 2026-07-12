"""PEP 621 pyproject.toml parsing for static dependency discovery."""

from pathlib import Path
from typing import Any

from air_blackbox.aibom.classifier import AIClassifier
from air_blackbox.aibom.dependency_utils import check_manifest_size, make_component
from air_blackbox.aibom.models import DependencyComponent, DependencyScope
from air_blackbox.aibom.requirements_parser import parse_requirement_declaration

try:
    import tomllib
except ImportError:  # pragma: no cover - exercised only on Python 3.10.
    import tomli as tomllib


def parse_pyproject(
    path: Path,
    rel: str,
    classifier: AIClassifier,
    warnings: list[str],
    failed_manifests: list[str],
) -> list[DependencyComponent]:
    """Parse PEP 621 project dependencies from pyproject.toml."""
    if not check_manifest_size(path, path.parent, warnings):
        return []
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except Exception as exc:
        failed_manifests.append(rel)
        warnings.append(f"Malformed TOML in {rel}: {exc}")
        return []

    project = data.get("project", {})
    if not isinstance(project, dict):
        warnings.append(f"Ignoring non-table project metadata in {rel}")
        return []

    components: list[DependencyComponent] = []
    dependencies = project.get("dependencies", [])
    if isinstance(dependencies, list):
        components.extend(
            _components_from_declarations(dependencies, rel, classifier, warnings)
        )
    elif dependencies:
        warnings.append(f"Ignoring non-list project.dependencies in {rel}")

    optional_dependencies = project.get("optional-dependencies", {})
    if isinstance(optional_dependencies, dict):
        for declarations in optional_dependencies.values():
            if isinstance(declarations, list):
                components.extend(
                    _components_from_declarations(
                        declarations, rel, classifier, warnings
                    )
                )
            else:
                warnings.append(
                    f"Ignoring non-list project.optional-dependencies group in {rel}"
                )
    elif optional_dependencies:
        warnings.append(f"Ignoring non-table project.optional-dependencies in {rel}")
    return components


def _components_from_declarations(
    declarations: list[Any],
    rel: str,
    classifier: AIClassifier,
    warnings: list[str],
) -> list[DependencyComponent]:
    components: list[DependencyComponent] = []
    for declaration in declarations:
        if not isinstance(declaration, str):
            warnings.append(f"Ignoring non-string Python dependency in {rel}")
            continue
        parsed = parse_requirement_declaration(declaration)
        if not parsed:
            warnings.append(f"Malformed Python dependency in {rel}: {declaration}")
            continue
        package_name, version = parsed
        components.append(
            make_component(
                package_name=package_name,
                version=version,
                ecosystem="python",
                scope=DependencyScope.DIRECT,
                source_manifest=rel,
                parent_dependencies=[],
                classifier=classifier,
            )
        )
    return components
