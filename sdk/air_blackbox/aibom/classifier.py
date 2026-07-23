"""Configurable AI-library classifier for package dependencies."""

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import yaml

from air_blackbox.aibom.models import AIClassification


class ClassifierConfigError(ValueError):
    """Raised when an explicitly supplied classifier config is invalid."""


@dataclass(frozen=True)
class ClassificationRule:
    """Normalized rule used by the package classifier."""

    ecosystem: str
    package_name: str
    category: str
    reason: str
    provider: Optional[str] = None


_PYTHON_NORMALIZE_RE = re.compile(r"[-_.]+")


def normalize_python_package_name(name: str) -> str:
    """Normalize a Python package name according to PEP 503."""
    return _PYTHON_NORMALIZE_RE.sub("-", name).lower()


def normalize_npm_package_name(name: str) -> str:
    """Normalize npm package names while preserving scoped package syntax."""
    return name.lower()


def normalize_package_name(name: str, ecosystem: str) -> str:
    """Normalize a package name for a supported ecosystem."""
    ecosystem = ecosystem.lower()
    if ecosystem == "python":
        return normalize_python_package_name(name)
    if ecosystem == "npm":
        return normalize_npm_package_name(name)
    return name.lower()


class AIClassifier:
    """Classifies package names using built-in and user-supplied rules."""

    SUPPORTED_ECOSYSTEMS = {"python", "npm"}

    def __init__(self, config_path: Optional[str] = None):
        self.warnings: list[str] = []
        self._rules: dict[tuple[str, str], ClassificationRule] = {}
        self._load_builtin_rules()
        if config_path:
            self.load_config(config_path, explicit=True)

    def classify(self, package_name: str, ecosystem: str) -> AIClassification:
        """Return AI classification for a package."""
        ecosystem = ecosystem.lower()
        normalized = normalize_package_name(package_name, ecosystem)
        rule = self._rules.get((ecosystem, normalized))
        if not rule:
            return AIClassification(is_ai=False)
        return AIClassification(
            is_ai=True,
            category=rule.category,
            reason=rule.reason,
            matched_rule=rule.package_name,
            provider=rule.provider,
        )

    def load_config(self, path: str, explicit: bool = True) -> None:
        """Load custom rules from YAML or JSON, extending built-in rules."""
        config_path = Path(path)
        if not config_path.exists():
            message = f"Classifier config not found: {path}"
            if explicit:
                raise ClassifierConfigError(message)
            self.warnings.append(message)
            return
        try:
            data = self._read_config(config_path)
            self._load_rules_from_data(data, source=str(config_path))
        except ClassifierConfigError:
            raise
        except Exception as exc:
            if explicit:
                raise ClassifierConfigError(
                    f"Invalid classifier config {path}: {exc}"
                ) from exc
            self.warnings.append(f"Could not load classifier config {path}: {exc}")

    def _load_builtin_rules(self) -> None:
        try:
            resource = resources.files("air_blackbox.aibom").joinpath(
                "ai_libraries.yaml"
            )
            with resource.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise ClassifierConfigError("classifier config must be a mapping")
            self._load_rules_from_data(
                data,
                source="air_blackbox.aibom:ai_libraries.yaml",
            )
        except Exception as exc:
            path = Path(__file__).with_name("ai_libraries.yaml")
            try:
                data = self._read_config(path)
                self._load_rules_from_data(data, source=str(path))
            except Exception as fallback_exc:
                raise ClassifierConfigError(
                    "Built-in AI library classifier rules could not be loaded: "
                    f"{exc}; fallback failed: {fallback_exc}"
                ) from fallback_exc

    def _read_config(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            if path.suffix.lower() == ".json":
                data = json.load(fh)
            else:
                data = yaml.safe_load(fh)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ClassifierConfigError("classifier config must be a mapping")
        return data

    def _load_rules_from_data(self, data: dict[str, Any], source: str) -> None:
        self._warn_unknown_fields(data, {"version", "packages"}, source)
        packages = data.get("packages", {})
        if packages is None:
            return
        if not isinstance(packages, dict):
            raise ClassifierConfigError("'packages' must be a mapping")

        for ecosystem, rules in packages.items():
            ecosystem_key = str(ecosystem).lower()
            if ecosystem_key not in self.SUPPORTED_ECOSYSTEMS:
                self.warnings.append(
                    f"Ignoring unsupported ecosystem '{ecosystem}' in {source}"
                )
                continue
            if not isinstance(rules, dict):
                raise ClassifierConfigError(f"'packages.{ecosystem}' must be a mapping")
            seen_normalized: dict[str, str] = {}
            for raw_name, raw_rule in rules.items():
                raw_name_str = str(raw_name)
                normalized = normalize_package_name(raw_name_str, ecosystem_key)
                previous = seen_normalized.get(normalized)
                if previous and previous != raw_name_str:
                    self.warnings.append(
                        f"Duplicate normalized {ecosystem_key} classifier entry "
                        f"'{normalized}' in {source}: '{previous}' and "
                        f"'{raw_name_str}'"
                    )
                seen_normalized[normalized] = raw_name_str
                rule = self._parse_rule(
                    ecosystem=ecosystem_key,
                    raw_name=raw_name_str,
                    normalized_name=normalized,
                    raw_rule=raw_rule,
                    source=source,
                )
                self._rules[(ecosystem_key, normalized)] = rule

    def _parse_rule(
        self,
        ecosystem: str,
        raw_name: str,
        normalized_name: str,
        raw_rule: Any,
        source: str,
    ) -> ClassificationRule:
        if raw_rule is None:
            raw_rule = {}
        if not isinstance(raw_rule, dict):
            raise ClassifierConfigError(
                f"Classifier rule for {ecosystem}:{raw_name} must be a mapping"
            )
        self._warn_unknown_fields(
            raw_rule,
            {"category", "reason", "provider"},
            f"{source} rule {ecosystem}:{raw_name}",
        )
        category = raw_rule.get("category")
        reason = raw_rule.get("reason")
        if not isinstance(category, str) or not category.strip():
            raise ClassifierConfigError(
                f"Classifier rule for {ecosystem}:{raw_name} requires category"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ClassifierConfigError(
                f"Classifier rule for {ecosystem}:{raw_name} requires reason"
            )
        provider = raw_rule.get("provider")
        if provider is not None and not isinstance(provider, str):
            raise ClassifierConfigError(
                f"Classifier rule for {ecosystem}:{raw_name} provider must be a string"
            )
        return ClassificationRule(
            ecosystem=ecosystem,
            package_name=normalized_name,
            category=category,
            reason=reason,
            provider=provider,
        )

    def _warn_unknown_fields(
        self,
        data: dict[str, Any],
        known_fields: set[str],
        source: str,
    ) -> None:
        for field in sorted(set(data) - known_fields):
            self.warnings.append(
                f"Ignoring unknown classifier field '{field}' in {source}"
            )
