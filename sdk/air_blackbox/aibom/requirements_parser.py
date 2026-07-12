"""requirements.txt parsing for static dependency discovery."""

import re
from pathlib import Path
from typing import Optional

from air_blackbox.aibom.classifier import AIClassifier
from air_blackbox.aibom.dependency_utils import (
    check_manifest_size,
    is_inside,
    make_component,
    path_for_display,
)
from air_blackbox.aibom.models import DependencyComponent, DependencyScope

_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*(.*)$")
_DIRECT_REFERENCE_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*@\s*(.+)$")
_EGG_RE = re.compile(r"[#&]egg=([A-Za-z0-9][A-Za-z0-9._-]*)")


def parse_requirements_file(
    path: Path,
    base: Path,
    classifier: AIClassifier,
    warnings: list[str],
    inspected_manifests: list[str],
    failed_manifests: list[str],
    seen: Optional[set[Path]] = None,
) -> list[DependencyComponent]:
    """Parse a requirements file and local includes."""
    seen = seen or set()
    resolved = path.resolve()
    rel = path_for_display(path, base)
    if resolved in seen:
        warnings.append(f"Skipping circular requirements include: {rel}")
        return []
    if path.is_symlink():
        warnings.append(f"Skipping symlinked requirements file: {rel}")
        return []
    if not is_inside(resolved, base):
        warnings.append(f"Skipping requirements file outside scan path: {rel}")
        return []
    if not check_manifest_size(path, base, warnings):
        return []
    seen.add(resolved)

    try:
        lines = _read_requirement_lines(path)
    except OSError as exc:
        failed_manifests.append(rel)
        warnings.append(f"Failed to read {rel}: {exc}")
        seen.remove(resolved)
        return []

    components: list[DependencyComponent] = []
    for line_number, line in lines:
        stripped = _strip_requirement_comment(line).strip()
        if not stripped:
            continue
        include = _parse_requirement_include(stripped)
        if include:
            components.extend(
                _parse_include(
                    include,
                    path,
                    base,
                    classifier,
                    warnings,
                    inspected_manifests,
                    failed_manifests,
                    seen,
                    rel,
                    line_number,
                )
            )
            continue
        parsed = parse_requirement_declaration(stripped)
        if parsed:
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
            continue
        if stripped.startswith("-"):
            if not _is_common_pip_option(stripped):
                warnings.append(
                    f"Ignoring unsupported pip option in {rel}:{line_number}"
                )
            continue
        warnings.append(f"Malformed requirement in {rel}:{line_number}")

    seen.remove(resolved)
    return components


def parse_requirement_declaration(line: str) -> Optional[tuple[str, Optional[str]]]:
    """Parse a package name and exact version from one requirement declaration."""
    line = _remove_hash_options(line)
    if line.startswith("-e "):
        line = line[3:].strip()
    elif line.startswith("--editable "):
        line = line[len("--editable ") :].strip()
    direct = _DIRECT_REFERENCE_RE.match(line)
    if direct:
        package_name, reference = direct.group(1), direct.group(2).strip()
        if _is_remote_reference(reference) or _looks_like_local_reference(reference):
            return package_name, None
        return None
    egg = _EGG_RE.search(line)
    if egg and (line.startswith("git+") or "://" in line):
        return egg.group(1), None
    if _is_remote_reference(line) or _looks_like_local_reference(line):
        return None

    line = line.split(";", 1)[0].strip()
    match = _REQ_NAME_RE.match(line)
    if not match:
        return None
    package_name = match.group(1)
    suffix = match.group(2).strip()
    version = None
    if suffix.startswith("=="):
        candidate = suffix[2:].strip().split()[0]
        if candidate and "*" not in candidate:
            version = candidate
    elif suffix and not suffix.startswith((">=", "<=", ">", "<", "~=", "!=", "===")):
        return None
    return package_name, version


def _parse_include(
    include: str,
    current_path: Path,
    base: Path,
    classifier: AIClassifier,
    warnings: list[str],
    inspected_manifests: list[str],
    failed_manifests: list[str],
    seen: set[Path],
    current_rel: str,
    line_number: int,
) -> list[DependencyComponent]:
    if _is_remote_reference(include):
        warnings.append(
            f"Ignoring remote requirements include in {current_rel}:{line_number}"
        )
        return []
    include_path = (current_path.parent / include).resolve()
    if not is_inside(include_path, base):
        warnings.append(
            f"Ignoring requirements include outside scan path in "
            f"{current_rel}:{line_number}"
        )
        return []
    if include_path.is_symlink():
        warnings.append(
            f"Ignoring symlinked requirements include in {current_rel}:{line_number}"
        )
        return []
    if not include_path.exists():
        warnings.append(
            f"Included requirements file not found in {current_rel}:{line_number}: "
            f"{include}"
        )
        return []
    include_rel = path_for_display(include_path, base)
    if include_rel not in inspected_manifests:
        inspected_manifests.append(include_rel)
    return parse_requirements_file(
        include_path,
        base,
        classifier,
        warnings,
        inspected_manifests,
        failed_manifests,
        seen,
    )


def _read_requirement_lines(path: Path) -> list[tuple[int, str]]:
    logical_lines: list[tuple[int, str]] = []
    pending = ""
    pending_line = 0
    with path.open("r", encoding="utf-8") as fh:
        for line_number, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")
            if pending:
                pending += line.lstrip()
            else:
                pending = line
                pending_line = line_number
            if pending.rstrip().endswith("\\"):
                pending = pending.rstrip()[:-1] + " "
                continue
            logical_lines.append((pending_line, pending))
            pending = ""
    if pending:
        logical_lines.append((pending_line, pending))
    return logical_lines


def _parse_requirement_include(line: str) -> Optional[str]:
    if line.startswith("-r "):
        return line[3:].strip()
    if line.startswith("--requirement "):
        return line[len("--requirement ") :].strip()
    return None


def _strip_requirement_comment(line: str) -> str:
    for marker in (" #", "\t#"):
        if marker in line:
            return line.split(marker, 1)[0]
    if line.lstrip().startswith("#"):
        return ""
    return line


def _remove_hash_options(line: str) -> str:
    parts = line.split()
    filtered: list[str] = []
    skip_next = False
    for part in parts:
        if skip_next:
            skip_next = False
            continue
        if part == "--hash":
            skip_next = True
            continue
        if part.startswith("--hash="):
            continue
        filtered.append(part)
    return " ".join(filtered)


def _is_common_pip_option(line: str) -> bool:
    return line.split()[0] in {
        "-c",
        "--constraint",
        "-e",
        "--editable",
        "--index-url",
        "-i",
        "--extra-index-url",
        "--find-links",
        "-f",
        "--trusted-host",
        "--require-hashes",
    }


def _is_remote_reference(value: str) -> bool:
    return value.startswith(("http://", "https://", "git+", "ssh://"))


def _looks_like_local_reference(value: str) -> bool:
    return value.startswith((".", "/", "file:")) or "\\" in value
