"""Internal AI-BOM component models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DependencyScope(str, Enum):
    """How a package dependency was introduced into the project."""

    DIRECT = "direct"
    TRANSITIVE = "transitive"
    UNKNOWN = "unknown"


@dataclass
class AIClassification:
    """Classifier result for a package dependency."""

    is_ai: bool = False
    category: Optional[str] = None
    reason: Optional[str] = None
    matched_rule: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class DependencyComponent:
    """Normalized package dependency discovered from project manifests."""

    package_name: str
    normalized_name: str
    version: Optional[str] = None
    ecosystem: str = "unknown"
    scope: DependencyScope = DependencyScope.UNKNOWN
    source_manifest: Optional[str] = None
    package_id: Optional[str] = None
    parent_dependencies: list[str] = field(default_factory=list)
    ai_classification: AIClassification = field(default_factory=AIClassification)


@dataclass
class RuntimeModelComponent:
    """Model observed at runtime from gateway or trust-layer records."""

    model_name: str
    model_provider: Optional[str] = None
    model_version: Optional[str] = None
    observed_runs: int = 0
    observed_tokens: int = 0


@dataclass
class AIBOMInventory:
    """Combined runtime and static dependency inventory."""

    runtime_models: list[RuntimeModelComponent] = field(default_factory=list)
    runtime_providers: list[str] = field(default_factory=list)
    runtime_tools: list[str] = field(default_factory=list)
    dependencies: list[DependencyComponent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
