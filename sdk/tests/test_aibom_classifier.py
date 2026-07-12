import json
from importlib import resources

import pytest
import yaml

from air_blackbox.aibom.classifier import (
    AIClassifier,
    ClassifierConfigError,
    normalize_npm_package_name,
    normalize_python_package_name,
)
from air_blackbox.aibom.models import (
    AIBOMInventory,
    AIClassification,
    DependencyComponent,
    DependencyScope,
    RuntimeModelComponent,
)


def test_known_python_ai_package():
    result = AIClassifier().classify("openai", "python")
    assert result.is_ai
    assert result.category == "llm-sdk"
    assert result.provider == "OpenAI"
    assert result.matched_rule == "openai"


def test_known_npm_ai_package():
    result = AIClassifier().classify("@anthropic-ai/sdk", "npm")
    assert result.is_ai
    assert result.category == "llm-sdk"
    assert result.provider == "Anthropic"


def test_ordinary_non_ai_package():
    result = AIClassifier().classify("requests", "python")
    assert not result.is_ai
    assert result.category is None
    assert result.provider is None


@pytest.mark.parametrize(
    "name",
    ["sentence_transformers", "Sentence.Transformers", "sentence-transformers"],
)
def test_python_normalization_resolves_consistently(name):
    assert normalize_python_package_name(name) == "sentence-transformers"
    result = AIClassifier().classify(name, "python")
    assert result.is_ai
    assert result.matched_rule == "sentence-transformers"


def test_scoped_npm_package_normalization():
    assert normalize_npm_package_name("@Anthropic-AI/SDK") == "@anthropic-ai/sdk"
    result = AIClassifier().classify("@Anthropic-AI/SDK", "npm")
    assert result.is_ai
    assert result.matched_rule == "@anthropic-ai/sdk"


def test_custom_package_extends_defaults(tmp_path):
    config = tmp_path / "classifier.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "packages": {
                    "python": {
                        "my-ai-sdk": {
                            "category": "llm-sdk",
                            "reason": "Internal AI SDK.",
                            "provider": "Internal",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    classifier = AIClassifier(str(config))
    result = classifier.classify("my_ai_sdk", "python")
    assert result.is_ai
    assert result.provider == "Internal"


def test_custom_package_overrides_builtin_rule(tmp_path):
    config = tmp_path / "classifier.json"
    config.write_text(
        json.dumps(
            {
                "packages": {
                    "python": {
                        "openai": {
                            "category": "internal-wrapper",
                            "reason": "Company-approved OpenAI wrapper.",
                            "provider": "Internal AI Platform",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = AIClassifier(str(config)).classify("openai", "python")
    assert result.is_ai
    assert result.category == "internal-wrapper"
    assert result.reason == "Company-approved OpenAI wrapper."
    assert result.provider == "Internal AI Platform"


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("bad.yaml", "packages: ["),
        ("bad.json", "{bad json"),
    ],
)
def test_invalid_yaml_or_json_raises_classifier_error(tmp_path, filename, content):
    config = tmp_path / filename
    config.write_text(content, encoding="utf-8")

    with pytest.raises(ClassifierConfigError):
        AIClassifier(str(config))


def test_missing_configuration_file_raises_classifier_error(tmp_path):
    with pytest.raises(ClassifierConfigError, match="not found"):
        AIClassifier(str(tmp_path / "missing.yaml"))


def test_duplicate_normalized_entries_warn_and_last_rule_wins(tmp_path):
    config = tmp_path / "classifier.yaml"
    config.write_text(
        """
packages:
  python:
    sentence_transformers:
      category: first
      reason: First rule.
    Sentence.Transformers:
      category: second
      reason: Second rule.
""",
        encoding="utf-8",
    )

    classifier = AIClassifier(str(config))
    result = classifier.classify("sentence-transformers", "python")
    assert result.category == "second"
    assert any(
        "Duplicate normalized python classifier entry" in warning
        for warning in classifier.warnings
    )


def test_unknown_optional_fields_are_warned_and_ignored(tmp_path):
    config = tmp_path / "classifier.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "unexpected_top_level": True,
                "packages": {
                    "npm": {
                        "my-ai-sdk": {
                            "category": "llm-sdk",
                            "reason": "Custom SDK.",
                            "extra": "ignored",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    classifier = AIClassifier(str(config))
    result = classifier.classify("my-ai-sdk", "npm")
    assert result.is_ai
    assert any("unexpected_top_level" in warning for warning in classifier.warnings)
    assert any("extra" in warning for warning in classifier.warnings)


def test_defaults_remain_available_after_custom_configuration_loaded(tmp_path):
    config = tmp_path / "classifier.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "packages": {
                    "npm": {
                        "my-ai-sdk": {
                            "category": "llm-sdk",
                            "reason": "Custom SDK.",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    classifier = AIClassifier(str(config))
    assert classifier.classify("my-ai-sdk", "npm").is_ai
    assert classifier.classify("openai", "python").is_ai
    assert classifier.classify("@langchain/core", "npm").is_ai


def test_builtin_classifier_config_loads_as_package_resource():
    resource = resources.files("air_blackbox.aibom").joinpath("ai_libraries.yaml")
    assert resource.is_file()

    classifier = AIClassifier()
    assert classifier.classify("openai", "python").is_ai


def test_models_keep_package_and_runtime_model_data_separate():
    dependency = DependencyComponent(
        package_name="openai",
        normalized_name="openai",
        version="1.0.0",
        ecosystem="python",
        scope=DependencyScope.DIRECT,
        source_manifest="requirements.txt",
        package_id="pkg:pypi/openai@1.0.0",
        parent_dependencies=[],
        ai_classification=AIClassification(
            is_ai=True,
            category="llm-sdk",
            reason="OpenAI SDK.",
            matched_rule="openai",
            provider="OpenAI",
        ),
    )
    runtime_model = RuntimeModelComponent(
        model_name="gpt-4o",
        model_provider="OpenAI",
        model_version=None,
        observed_runs=2,
        observed_tokens=100,
    )
    inventory = AIBOMInventory(
        dependencies=[dependency],
        runtime_models=[runtime_model],
        runtime_providers=["openai"],
        runtime_tools=["web_search"],
        warnings=["sample warning"],
    )

    assert inventory.dependencies[0].package_name == "openai"
    assert not hasattr(inventory.dependencies[0], "model_name")
    assert inventory.runtime_models[0].model_name == "gpt-4o"
    assert inventory.runtime_models[0].model_version is None
