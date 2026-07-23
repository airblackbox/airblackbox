"""Shared helpers for static dependency discovery."""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from air_blackbox.aibom.classifier import (
    AIClassifier,
    normalize_npm_package_name,
    normalize_python_package_name,
)
from air_blackbox.aibom.models import DependencyComponent, DependencyScope

MANIFEST_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
MAX_MANIFESTS = 1000
MAX_MANIFEST_BYTES = 5 * 1024 * 1024


def build_package_id(
    ecosystem: str, normalized_name: str, version: Optional[str]
) -> str:
    """Build a small purl-style package identifier."""
    ecosystem = ecosystem.lower()
    if ecosystem == "python":
        base = f"pkg:pypi/{quote(normalized_name, safe='.-_')}"
    elif ecosystem == "npm":
        base = f"pkg:npm/{quote_npm_purl_name(normalized_name)}"
    else:
        base = (
            f"pkg:{quote(ecosystem, safe='.-_')}/{quote(normalized_name, safe='.-_')}"
        )
    if version:
        return f"{base}@{quote(version, safe='.-_+~:')}"
    return base


def make_component(
    package_name: str,
    version: Optional[str],
    ecosystem: str,
    scope: DependencyScope,
    source_manifest: str,
    parent_dependencies: list[str],
    classifier: AIClassifier,
) -> DependencyComponent:
    """Create a normalized dependency component."""
    normalized = normalize_dependency_name(package_name, ecosystem)
    package_id = build_package_id(ecosystem, normalized, version)
    return DependencyComponent(
        package_name=package_name,
        normalized_name=normalized,
        version=version,
        ecosystem=ecosystem,
        scope=scope,
        source_manifest=source_manifest,
        package_id=package_id,
        parent_dependencies=sorted(set(parent_dependencies)),
        ai_classification=classifier.classify(package_name, ecosystem),
    )


def normalize_dependency_name(package_name: str, ecosystem: str) -> str:
    """Normalize package names for supported ecosystems."""
    if ecosystem == "python":
        return normalize_python_package_name(package_name)
    if ecosystem == "npm":
        return normalize_npm_package_name(package_name)
    return package_name.lower()


def quote_npm_purl_name(normalized_name: str) -> str:
    """Quote npm package names for purl identifiers."""
    if normalized_name.startswith("@") and "/" in normalized_name:
        scope, name = normalized_name.split("/", 1)
        return f"{quote(scope, safe='')}/{quote(name, safe='.-_')}"
    return quote(normalized_name, safe=".-_")


def exact_npm_version(declaration: str) -> Optional[str]:
    """Return an exact npm version only for bare semver-like declarations."""
    declaration = declaration.strip()
    if re.fullmatch(r"\d+(?:\.\d+){0,2}(?:[-+][0-9A-Za-z.-]+)?", declaration):
        return declaration
    return None


def iter_manifest_candidates(base: Path) -> tuple[list[Path], list[str]]:
    """Return supported manifest paths under base with deterministic bounds."""
    warnings: list[str] = []
    if base.is_file():
        if base.name not in MANIFEST_NAMES:
            return [], warnings
        resolved = base.resolve()
        if base.is_symlink():
            warnings.append(
                f"Skipping symlinked manifest: {path_for_display(base, base.parent)}"
            )
            return [], warnings
        if not is_inside(resolved, base.parent.resolve()):
            warnings.append(f"Skipping manifest outside scan path: {base}")
            return [], warnings
        return [base], warnings

    manifests: list[Path] = []
    for root_str, dirs, files in os.walk(base):
        root = Path(root_str)
        dirs.sort()
        files.sort()
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            if filename not in MANIFEST_NAMES:
                continue
            candidate = root / filename
            if candidate.is_symlink():
                warnings.append(
                    f"Skipping symlinked manifest: {path_for_display(candidate, base)}"
                )
                continue
            resolved = candidate.resolve()
            if not is_inside(resolved, base):
                warnings.append(
                    f"Skipping manifest outside scan path: {path_for_display(candidate, base)}"
                )
                continue
            manifests.append(candidate)
            if len(manifests) >= MAX_MANIFESTS:
                warnings.append(
                    f"Manifest scan limit reached ({MAX_MANIFESTS}); remaining files skipped"
                )
                return _sort_paths(manifests, base), warnings
    return _sort_paths(manifests, base), warnings


def check_manifest_size(path: Path, base: Path, warnings: list[str]) -> bool:
    """Return True when path is small enough to parse."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        warnings.append(f"Could not stat {path_for_display(path, base)}: {exc}")
        return False
    if size > MAX_MANIFEST_BYTES:
        warnings.append(
            f"Skipping {path_for_display(path, base)}: file is larger than "
            f"{MAX_MANIFEST_BYTES} bytes"
        )
        return False
    return True


def is_inside(path: Path, base: Path) -> bool:
    """Return whether path resolves within base."""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def path_for_display(path: Path, base: Path) -> str:
    """Return deterministic forward-slash path relative to base when possible."""
    try:
        return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except ValueError:
        try:
            return str(path.relative_to(base)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")


def merge_source_manifest(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """Merge comma-separated source manifest strings deterministically."""
    values = set()
    for item in (left, right):
        if item:
            values.update(part.strip() for part in item.split(",") if part.strip())
    return ",".join(sorted(values)) if values else None


def _sort_paths(paths: list[Path], base: Path) -> list[Path]:
    return sorted(paths, key=lambda p: path_for_display(p, base))
