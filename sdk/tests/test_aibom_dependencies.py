import json

from air_blackbox.aibom.classifier import AIClassifier
from air_blackbox.aibom.dependencies import discover_dependencies
from air_blackbox.aibom.models import DependencyScope


def _discover(path, classifier=None):
    return discover_dependencies(path, classifier or AIClassifier())


def _by_name(result, name, ecosystem=None):
    matches = [
        component
        for component in result.dependencies
        if component.normalized_name == name
        and (ecosystem is None or component.ecosystem == ecosystem)
    ]
    assert matches, f"missing dependency {ecosystem or '*'}:{name}"
    return matches[0]


def _by_identity(result, ecosystem, name, version):
    matches = [
        component
        for component in result.dependencies
        if component.ecosystem == ecosystem
        and component.normalized_name == name
        and component.version == version
    ]
    assert len(matches) == 1, (
        f"expected one {ecosystem}:{name}@{version}, got {matches}"
    )
    return matches[0]


def _components_by_name(result, ecosystem, name):
    return [
        component
        for component in result.dependencies
        if component.ecosystem == ecosystem and component.normalized_name == name
    ]


def _assert_parent_refs_valid(result):
    package_ids = [component.package_id for component in result.dependencies]
    for component in result.dependencies:
        for parent in component.parent_dependencies:
            assert package_ids.count(parent) == 1


def test_requirements_direct_ai_and_general_dependencies(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "openai==1.2.3\nrequests==2.31.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    openai = _by_name(result, "openai", "python")
    requests = _by_name(result, "requests", "python")
    assert openai.scope == DependencyScope.DIRECT
    assert openai.version == "1.2.3"
    assert openai.ai_classification.is_ai
    assert not requests.ai_classification.is_ai


def test_pinned_and_ranged_python_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "openai==1.2.3\nanthropic>=0.25\nsentence-transformers~=3.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "python").version == "1.2.3"
    assert _by_name(result, "anthropic", "python").version is None
    assert _by_name(result, "sentence-transformers", "python").version is None
    assert all(
        component.scope == DependencyScope.DIRECT for component in result.dependencies
    )


def test_requirements_comments_markers_extras_and_blank_lines(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        """
# comment
transformers[torch]==4.45.0 ; python_version >= "3.10"

sentence_transformers>=3.0  # inline comment
""",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    transformers = _by_name(result, "transformers", "python")
    sentence_transformers = _by_name(result, "sentence-transformers", "python")
    assert transformers.version == "4.45.0"
    assert sentence_transformers.version is None
    assert transformers.ai_classification.is_ai


def test_requirements_inline_comment_backslash_does_not_continue_line(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "openai==1.0.0  # note C:\\\nrequests==2.0.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_identity(result, "python", "openai", "1.0.0")
    assert _by_identity(result, "python", "requests", "2.0.0")


def test_included_requirements_file(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "-r other-requirements.txt\n",
        encoding="utf-8",
    )
    (tmp_path / "other-requirements.txt").write_text(
        "openai==1.0.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "python").version == "1.0.0"
    assert "requirements.txt" in result.inspected_manifests
    assert "other-requirements.txt" in result.inspected_manifests


def test_circular_requirements_file_includes_warn_and_continue(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "-r other-requirements.txt\nopenai==1.0.0\n",
        encoding="utf-8",
    )
    (tmp_path / "other-requirements.txt").write_text(
        "-r requirements.txt\nanthropic==0.1.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "python").version == "1.0.0"
    assert _by_name(result, "anthropic", "python").version == "0.1.0"
    assert any(
        "circular requirements include" in warning for warning in result.warnings
    )


def test_malformed_requirement_lines_warn(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "not a valid requirement !!!\nopenai==1.0.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "python").version == "1.0.0"
    assert any("Malformed requirement" in warning for warning in result.warnings)


def test_pep_621_pyproject_dependencies(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = ["openai==1.2.3", "requests>=2"]
""",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "python").version == "1.2.3"
    assert _by_name(result, "requests", "python").scope == DependencyScope.DIRECT


def test_optional_pyproject_dependency_groups(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = []

[project.optional-dependencies]
ai = ["llama-index==0.10.0"]
ml = ["torch>=2"]
""",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "llama-index", "python").version == "0.10.0"
    assert _by_name(result, "torch", "python").version is None


def test_malformed_pyproject_toml_warns(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert result.failed_manifests == ["pyproject.toml"]
    assert any("Malformed TOML" in warning for warning in result.warnings)


def test_package_json_direct_dependencies(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"openai": "4.0.0"},
                "optionalDependencies": {"langchain": "^0.2.0"},
                "peerDependencies": {"react": "^18.0.0"},
                "devDependencies": {"@anthropic-ai/sdk": "1.0.0"},
            }
        ),
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "npm").version == "4.0.0"
    assert _by_name(result, "langchain", "npm").version is None
    assert _by_name(result, "react", "npm").version is None
    assert not any(
        c.normalized_name == "@anthropic-ai/sdk" for c in result.dependencies
    )


def test_scoped_npm_dependencies(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"@Anthropic-AI/SDK": "1.2.3"}}),
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    sdk = _by_name(result, "@anthropic-ai/sdk", "npm")
    assert sdk.package_id == "pkg:npm/%40anthropic-ai/sdk@1.2.3"
    assert sdk.ai_classification.provider == "Anthropic"


def test_package_json_version_ranges_not_exact_versions(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "openai": "^4.0.0",
                    "langchain": "~0.2.0",
                    "ai": "latest",
                    "local": "file:../local",
                }
            }
        ),
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert all(component.version is None for component in result.dependencies)


def test_package_lock_direct_dependency(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "^4.0.0"}},
            "node_modules/openai": {"version": "4.2.0"},
        },
    )

    result = _discover(tmp_path)

    openai = _by_name(result, "openai", "npm")
    assert openai.version == "4.2.0"
    assert openai.scope == DependencyScope.DIRECT


def test_package_lock_transitive_only_ai_dependency(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"wrapper": "1.0.0"}},
            "node_modules/wrapper": {
                "version": "1.0.0",
                "dependencies": {"openai": "4.0.0"},
            },
            "node_modules/openai": {"version": "4.0.0"},
        },
    )

    result = _discover(tmp_path)

    openai = _by_name(result, "openai", "npm")
    wrapper = _by_name(result, "wrapper", "npm")
    assert openai.scope == DependencyScope.TRANSITIVE
    assert openai.ai_classification.is_ai
    assert wrapper.package_id in openai.parent_dependencies


def test_shared_transitive_dependency_has_multiple_parents(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"wrapper-a": "1.0.0", "wrapper-b": "1.0.0"}},
            "node_modules/wrapper-a": {
                "version": "1.0.0",
                "dependencies": {"openai": "4.0.0"},
            },
            "node_modules/wrapper-b": {
                "version": "1.0.0",
                "dependencies": {"openai": "4.0.0"},
            },
            "node_modules/openai": {"version": "4.0.0"},
        },
    )

    result = _discover(tmp_path)

    openai = _by_name(result, "openai", "npm")
    assert len(openai.parent_dependencies) == 2


def test_nested_node_modules_paths(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"wrapper": "1.0.0"}},
            "node_modules/wrapper": {
                "version": "1.0.0",
                "dependencies": {"@scope/package": "2.0.0"},
            },
            "node_modules/wrapper/node_modules/@scope/package": {"version": "2.0.0"},
        },
    )

    result = _discover(tmp_path)

    nested = _by_name(result, "@scope/package", "npm")
    wrapper = _by_name(result, "wrapper", "npm")
    assert nested.version == "2.0.0"
    assert nested.scope == DependencyScope.TRANSITIVE
    assert wrapper.package_id in nested.parent_dependencies


def test_cyclic_dependency_graph_does_not_loop(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"a": "1.0.0"}},
            "node_modules/a": {"version": "1.0.0", "dependencies": {"b": "1.0.0"}},
            "node_modules/b": {"version": "1.0.0", "dependencies": {"a": "1.0.0"}},
        },
    )

    result = _discover(tmp_path)

    assert _by_name(result, "a", "npm").scope == DependencyScope.DIRECT
    assert _by_name(result, "b", "npm").scope == DependencyScope.TRANSITIVE


def test_missing_lockfile_versions(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "*"}},
            "node_modules/openai": {},
        },
    )

    result = _discover(tmp_path)

    openai = _by_name(result, "openai", "npm")
    assert openai.version is None
    assert openai.package_id == "pkg:npm/openai"


def test_malformed_package_lock_json_warns(tmp_path):
    (tmp_path / "package-lock.json").write_text("{bad json", encoding="utf-8")

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert result.failed_manifests == ["package-lock.json"]
    assert any("Malformed JSON" in warning for warning in result.warnings)


def test_deduplication_between_package_json_and_package_lock(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "^4.0.0"}}),
        encoding="utf-8",
    )
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "^4.0.0"}},
            "node_modules/openai": {"version": "4.2.0"},
        },
    )

    result = _discover(tmp_path)

    openai_components = [
        component
        for component in result.dependencies
        if component.normalized_name == "openai" and component.ecosystem == "npm"
    ]
    assert len(openai_components) == 1
    assert openai_components[0].scope == DependencyScope.DIRECT


def test_exact_lockfile_version_replaces_manifest_range(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "^4.0.0"}}),
        encoding="utf-8",
    )
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "^4.0.0"}},
            "node_modules/openai": {"version": "4.2.0"},
        },
    )

    result = _discover(tmp_path)

    assert _by_name(result, "openai", "npm").version == "4.2.0"


def test_excluded_directories_are_not_scanned(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "4.0.0"}}),
        encoding="utf-8",
    )
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "requirements.txt").write_text(
        "anthropic==0.1.0\n",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert result.inspected_manifests == []


def test_empty_scan_directory(tmp_path):
    result = _discover(tmp_path)

    assert result.dependencies == []
    assert result.warnings == []
    assert result.inspected_manifests == []
    assert result.failed_manifests == []


def test_custom_classifier_rule_applied_during_discovery(tmp_path):
    config = tmp_path / "classifier.yaml"
    config.write_text(
        """
packages:
  python:
    internal-ai:
      category: llm-sdk
      reason: Internal AI SDK.
      provider: Internal
""",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("internal-ai==1.0.0\n", encoding="utf-8")

    result = _discover(tmp_path, AIClassifier(str(config)))

    dependency = _by_name(result, "internal-ai", "python")
    assert dependency.ai_classification.is_ai
    assert dependency.ai_classification.provider == "Internal"


def test_symlinked_requirements_outside_root_is_skipped(tmp_path):
    outside = tmp_path.parent / "outside-requirements.txt"
    outside.write_text("openai==9.9.9\n", encoding="utf-8")
    link = tmp_path / "requirements.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert any("symlinked manifest" in warning for warning in result.warnings)


def test_symlinked_package_lock_outside_root_is_skipped(tmp_path):
    outside = tmp_path.parent / "outside-package-lock.json"
    outside.write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {"node_modules/openai": {"version": "9.9.9"}},
            }
        ),
        encoding="utf-8",
    )
    link = tmp_path / "package-lock.json"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert any("symlinked manifest" in warning for warning in result.warnings)


def test_requirements_include_parent_path_outside_root_is_skipped(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("openai==9.9.9\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("-r ../outside.txt\n", encoding="utf-8")

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert any("outside scan path" in warning for warning in result.warnings)


def test_requirements_include_absolute_path_outside_root_is_skipped(tmp_path):
    outside = tmp_path.parent / "absolute-outside.txt"
    outside.write_text("openai==9.9.9\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(f"-r {outside}\n", encoding="utf-8")

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert any("outside scan path" in warning for warning in result.warnings)


def test_requirements_safe_include_inside_root(tmp_path):
    nested = tmp_path / "reqs"
    nested.mkdir()
    (tmp_path / "requirements.txt").write_text("-r reqs/base.txt\n", encoding="utf-8")
    (nested / "base.txt").write_text("openai==1.0.0\n", encoding="utf-8")

    result = _discover(tmp_path)

    assert (
        _by_identity(result, "python", "openai", "1.0.0").scope
        == DependencyScope.DIRECT
    )


def test_requirements_unreadable_include_keeps_parent_dependencies(
    tmp_path, monkeypatch
):
    nested = tmp_path / "reqs"
    nested.mkdir()
    (tmp_path / "requirements.txt").write_text(
        "openai==1.2.3\nrequests==2.31.0\n-r reqs/sub.txt\n",
        encoding="utf-8",
    )
    (nested / "sub.txt").write_text("anthropic==0.5.0\n", encoding="utf-8")

    from air_blackbox.aibom import requirements_parser

    original_read = requirements_parser._read_requirement_lines

    def fail_for_include(path):
        if path.name == "sub.txt":
            raise OSError("permission denied")
        return original_read(path)

    monkeypatch.setattr(
        requirements_parser,
        "_read_requirement_lines",
        fail_for_include,
    )

    result = _discover(tmp_path)

    assert _by_identity(result, "python", "openai", "1.2.3")
    assert _by_identity(result, "python", "requests", "2.31.0")
    assert _components_by_name(result, "python", "anthropic") == []
    assert result.failed_manifests == ["reqs/sub.txt"]
    assert any("Failed to read reqs/sub.txt" in warning for warning in result.warnings)


def test_package_json_exact_version_differs_from_lockfile_installed_version(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "4.0.0"}}),
        encoding="utf-8",
    )
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "4.0.0"}},
            "node_modules/openai": {"version": "4.2.0"},
        },
    )

    result = _discover(tmp_path)

    openai = _by_identity(result, "npm", "openai", "4.2.0")
    assert len(_components_by_name(result, "npm", "openai")) == 1
    assert openai.scope == DependencyScope.DIRECT
    assert openai.source_manifest == "package-lock.json,package.json"


def test_package_json_range_plus_lockfile_exact_version_merges(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "^4.0.0"}}),
        encoding="utf-8",
    )
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"openai": "^4.0.0"}},
            "node_modules/openai": {"version": "4.2.0"},
        },
    )

    result = _discover(tmp_path)

    assert len(_components_by_name(result, "npm", "openai")) == 1
    assert (
        _by_identity(result, "npm", "openai", "4.2.0").scope == DependencyScope.DIRECT
    )


def test_two_installed_versions_of_same_package_are_preserved(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"a": "1.0.0", "b": "1.0.0"}},
            "node_modules/a": {"version": "1.0.0", "dependencies": {"foo": "1.0.0"}},
            "node_modules/a/node_modules/foo": {"version": "1.0.0"},
            "node_modules/b": {"version": "1.0.0", "dependencies": {"foo": "2.0.0"}},
            "node_modules/b/node_modules/foo": {"version": "2.0.0"},
        },
    )

    result = _discover(tmp_path)

    foo_1 = _by_identity(result, "npm", "foo", "1.0.0")
    foo_2 = _by_identity(result, "npm", "foo", "2.0.0")
    assert (
        _by_identity(result, "npm", "a", "1.0.0").package_id
        in foo_1.parent_dependencies
    )
    assert (
        _by_identity(result, "npm", "b", "1.0.0").package_id
        in foo_2.parent_dependencies
    )
    _assert_parent_refs_valid(result)


def test_unversioned_lockfile_package_does_not_merge_with_versioned_same_name(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"a": "1.0.0", "b": "1.0.0"}},
            "node_modules/a": {"version": "1.0.0", "dependencies": {"foo": "*"}},
            "node_modules/a/node_modules/foo": {},
            "node_modules/b": {"version": "1.0.0", "dependencies": {"foo": "2.0.0"}},
            "node_modules/b/node_modules/foo": {"version": "2.0.0"},
        },
    )

    result = _discover(tmp_path)

    assert _by_identity(result, "npm", "foo", None)
    assert _by_identity(result, "npm", "foo", "2.0.0")
    assert len(_components_by_name(result, "npm", "foo")) == 2


def test_package_lock_root_without_dependencies_uses_top_level_direct_metadata(
    tmp_path,
):
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "dependencies": {"openai": "^4.0.0"},
                "packages": {"": {}, "node_modules/openai": {"version": "4.2.0"}},
            }
        ),
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert (
        _by_identity(result, "npm", "openai", "4.2.0").scope == DependencyScope.DIRECT
    )


def test_package_lock_root_without_dependencies_uses_sibling_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"openai": "^4.0.0"}}),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {"": {}, "node_modules/openai": {"version": "4.2.0"}},
            }
        ),
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert (
        _by_identity(result, "npm", "openai", "4.2.0").scope == DependencyScope.DIRECT
    )


def test_ambiguous_dependency_edge_creates_no_incorrect_parent(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"wrapper": "1.0.0"}},
            "node_modules/wrapper": {"version": "1.0.0", "dependencies": {"foo": "*"}},
            "node_modules/a/node_modules/foo": {"version": "1.0.0"},
            "node_modules/b/node_modules/foo": {"version": "2.0.0"},
        },
    )

    result = _discover(tmp_path)

    wrapper = _by_identity(result, "npm", "wrapper", "1.0.0")
    assert (
        wrapper.package_id
        not in _by_identity(result, "npm", "foo", "1.0.0").parent_dependencies
    )
    assert (
        wrapper.package_id
        not in _by_identity(result, "npm", "foo", "2.0.0").parent_dependencies
    )
    assert any(
        "Ambiguous package-lock dependency edge" in warning
        for warning in result.warnings
    )


def test_shared_transitive_dependency_parent_ids_are_exact(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"wrapper-a": "1.0.0", "wrapper-b": "1.0.0"}},
            "node_modules/wrapper-a": {
                "version": "1.0.0",
                "dependencies": {"openai": "4.0.0"},
            },
            "node_modules/wrapper-b": {
                "version": "1.0.0",
                "dependencies": {"openai": "4.0.0"},
            },
            "node_modules/openai": {"version": "4.0.0"},
        },
    )

    result = _discover(tmp_path)

    openai = _by_identity(result, "npm", "openai", "4.0.0")
    expected = {
        _by_identity(result, "npm", "wrapper-a", "1.0.0").package_id,
        _by_identity(result, "npm", "wrapper-b", "1.0.0").package_id,
    }
    assert set(openai.parent_dependencies) == expected
    _assert_parent_refs_valid(result)


def test_cycle_parent_ids_are_exact(tmp_path):
    _write_package_lock(
        tmp_path,
        {
            "": {"dependencies": {"a": "1.0.0"}},
            "node_modules/a": {"version": "1.0.0", "dependencies": {"b": "1.0.0"}},
            "node_modules/b": {"version": "1.0.0", "dependencies": {"a": "1.0.0"}},
        },
    )

    result = _discover(tmp_path)

    a = _by_identity(result, "npm", "a", "1.0.0")
    b = _by_identity(result, "npm", "b", "1.0.0")
    assert a.package_id in b.parent_dependencies
    assert b.package_id in a.parent_dependencies
    _assert_parent_refs_valid(result)


def test_unsupported_requirement_forms_are_deterministic(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        """
-e .
-e git+https://example.com/repo.git#egg=vcs_pkg
local/path
openai @ https://example.com/openai.whl
requests==2.0.0 \\
    --hash=sha256:abcdef
broken req ; ; bad marker
""",
        encoding="utf-8",
    )

    result = _discover(tmp_path)

    assert _by_identity(result, "python", "vcs-pkg", None)
    assert _by_identity(result, "python", "openai", None)
    assert _by_identity(result, "python", "requests", "2.0.0")
    assert any("Malformed requirement" in warning for warning in result.warnings)


def test_large_manifest_is_skipped_with_warning(tmp_path, monkeypatch):
    import air_blackbox.aibom.dependency_utils as dependency_utils

    monkeypatch.setattr(dependency_utils, "MAX_MANIFEST_BYTES", 10)
    (tmp_path / "requirements.txt").write_text("openai==1.0.0\n", encoding="utf-8")

    result = _discover(tmp_path)

    assert result.dependencies == []
    assert any("larger than" in warning for warning in result.warnings)


def _write_package_lock(tmp_path, packages):
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "test-project",
                "lockfileVersion": 3,
                "packages": packages,
            }
        ),
        encoding="utf-8",
    )
