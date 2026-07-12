import copy
import re

from air_blackbox.aibom.classifier import AIClassifier
from air_blackbox.aibom.dependencies import discover_dependencies
from air_blackbox.aibom.generator import generate_aibom
from air_blackbox.aibom.models import (
    AIBOMInventory,
    AIClassification,
    DependencyComponent,
    DependencyScope,
    RuntimeModelComponent,
)
from air_blackbox.aibom.serializers import to_cyclonedx, to_spdx
from air_blackbox.gateway_client import GatewayStatus

META = {
    "project_name": "serializer-fixture",
    "project_version": "1.0.0",
    "timestamp": "2026-01-01T00:00:00Z",
    "serial_number": "urn:uuid:00000000-0000-4000-8000-000000000001",
    "document_namespace": "https://example.com/spdx/serializer-fixture",
    "tool_name": "air-blackbox",
    "tool_version": "test",
    "root_bom_ref": "root:serializer-fixture",
    "root_spdx_id": "SPDXRef-Root-SerializerFixture",
}


def test_cyclonedx_empty_inventory_structure_and_root_metadata():
    bom = to_cyclonedx(AIBOMInventory(), META)

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.6"
    assert bom["serialNumber"] == META["serial_number"]
    assert bom["metadata"]["component"]["bom-ref"] == "root:serializer-fixture"
    assert bom["metadata"]["component"]["type"] == "application"
    assert bom["components"] == []
    assert bom["dependencies"] == [{"ref": "root:serializer-fixture", "dependsOn": []}]


def test_cyclonedx_direct_python_ai_dependency_properties():
    inventory = AIBOMInventory(
        dependencies=[_dep("python", "openai", "1.2.3", ai=True)]
    )

    component = _cdx_component(to_cyclonedx(inventory, META), "pkg:pypi/openai@1.2.3")
    props = _props(component)

    assert component["type"] == "library"
    assert component["version"] == "1.2.3"
    assert component["purl"] == "pkg:pypi/openai@1.2.3"
    assert props["air-blackbox:ecosystem"] == "python"
    assert props["air-blackbox:dependency-scope"] == "direct"
    assert props["air-blackbox:ai-dependency"] == "true"
    assert props["air-blackbox:ai-category"] == "llm-sdk"
    assert props["air-blackbox:classification-reason"] == "AI SDK"
    assert props["air-blackbox:matched-rule"] == "openai"
    assert props["air-blackbox:provider"] == "OpenAI"


def test_cyclonedx_general_direct_dependency():
    inventory = AIBOMInventory(dependencies=[_dep("python", "requests", "2.31.0")])

    component = _cdx_component(
        to_cyclonedx(inventory, META), "pkg:pypi/requests@2.31.0"
    )
    props = _props(component)

    assert props["air-blackbox:ai-dependency"] == "false"
    assert "air-blackbox:ai-category" not in props


def test_cyclonedx_transitive_only_ai_dependency_graph():
    parent = _dep("npm", "wrapper", "1.0.0")
    child = _dep(
        "npm",
        "openai",
        "4.0.0",
        scope=DependencyScope.TRANSITIVE,
        parents=[parent.package_id],
        ai=True,
    )

    bom = to_cyclonedx(AIBOMInventory(dependencies=[parent, child]), META)

    assert _depends_on(bom, "root:serializer-fixture") == [parent.package_id]
    assert _depends_on(bom, parent.package_id) == [child.package_id]


def test_cyclonedx_shared_transitive_dependency_with_two_parents():
    parent_a = _dep("npm", "wrapper-a", "1.0.0")
    parent_b = _dep("npm", "wrapper-b", "1.0.0")
    child = _dep(
        "npm",
        "openai",
        "4.0.0",
        scope=DependencyScope.TRANSITIVE,
        parents=[parent_a.package_id, parent_b.package_id],
        ai=True,
    )

    bom = to_cyclonedx(AIBOMInventory(dependencies=[child, parent_b, parent_a]), META)

    assert _depends_on(bom, parent_a.package_id) == [child.package_id]
    assert _depends_on(bom, parent_b.package_id) == [child.package_id]


def test_cyclonedx_multiple_versions_remain_separate():
    inventory = AIBOMInventory(
        dependencies=[
            _dep("npm", "foo", "1.0.0"),
            _dep("npm", "foo", "2.0.0"),
        ]
    )

    bom = to_cyclonedx(inventory, META)

    assert _cdx_component(bom, "pkg:npm/foo@1.0.0")
    assert _cdx_component(bom, "pkg:npm/foo@2.0.0")


def test_cyclonedx_scoped_npm_purl_and_bom_ref():
    inventory = AIBOMInventory(
        dependencies=[_dep("npm", "@anthropic-ai/sdk", "1.2.3", ai=True)]
    )

    component = _cdx_component(
        to_cyclonedx(inventory, META),
        "pkg:npm/%40anthropic-ai/sdk@1.2.3",
    )

    assert component["purl"] == "pkg:npm/%40anthropic-ai/sdk@1.2.3"


def test_cyclonedx_missing_package_version_omits_version():
    inventory = AIBOMInventory(dependencies=[_dep("python", "openai", None, ai=True)])

    component = _cdx_component(to_cyclonedx(inventory, META), "pkg:pypi/openai")

    assert "version" not in component


def test_cyclonedx_runtime_model_with_provider_and_explicit_version():
    model = RuntimeModelComponent("gpt-4o", "OpenAI", "2024-08-06", 3, 1200)

    component = _single_model_component(
        to_cyclonedx(AIBOMInventory(runtime_models=[model]), META)
    )
    props = _props(component)

    assert component["type"] == "machine-learning-model"
    assert component["name"] == "gpt-4o"
    assert component["version"] == "2024-08-06"
    assert component["publisher"] == "OpenAI"
    assert props["air-blackbox:provider"] == "OpenAI"
    assert props["air-blackbox:observed-runs"] == "3"
    assert props["air-blackbox:observed-tokens"] == "1200"


def test_cyclonedx_runtime_model_without_provider_or_version():
    model = RuntimeModelComponent("unknown-model", None, None, 1, 0)

    component = _single_model_component(
        to_cyclonedx(AIBOMInventory(runtime_models=[model]), META)
    )

    assert "version" not in component
    assert "publisher" not in component
    assert "air-blackbox:provider" not in _props(component)


def test_cyclonedx_same_model_name_with_different_providers():
    inventory = AIBOMInventory(
        runtime_models=[
            RuntimeModelComponent("chat-model", "ProviderA", None, 1, 10),
            RuntimeModelComponent("chat-model", "ProviderB", None, 1, 10),
        ]
    )

    bom = to_cyclonedx(inventory, META)
    refs = [
        component["bom-ref"]
        for component in bom["components"]
        if component["type"] == "machine-learning-model"
    ]

    assert len(refs) == 2
    assert len(set(refs)) == 2


def test_cyclonedx_runtime_providers_and_tools_are_represented():
    inventory = AIBOMInventory(
        runtime_providers=["openai"], runtime_tools=["web_search"]
    )

    bom = to_cyclonedx(inventory, META)
    names = {component["name"] for component in bom["components"]}

    assert "openai API" in names
    assert "web_search" in names


def test_cyclonedx_parent_refs_resolve_and_bom_refs_unique():
    bom = to_cyclonedx(_graph_inventory(), META)
    refs = [component["bom-ref"] for component in bom["components"]]
    valid_refs = set(refs) | {"root:serializer-fixture"}

    assert len(refs) == len(set(refs))
    for entry in bom["dependencies"]:
        assert entry["ref"] in valid_refs
        for child in entry["dependsOn"]:
            assert child in valid_refs


def test_cyclonedx_stable_output_ordering():
    first = to_cyclonedx(_graph_inventory(), META)
    second = to_cyclonedx(copy.deepcopy(_graph_inventory()), META)

    assert first == second


def test_generate_aibom_status_compatibility():
    status = GatewayStatus(
        total_runs=2,
        models_observed=["gpt-4o"],
        providers_observed=["openai"],
        total_tokens=100,
        recent_runs=[
            {"model": "gpt-4o", "tokens": 70, "tool_calls": ["web_search"]},
            {"model": "gpt-4o", "tokens": 30, "tool_calls": []},
        ],
    )

    bom = generate_aibom(status, META)

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.6"
    assert any(component["name"] == "gpt-4o" for component in bom["components"])
    assert any(component["name"] == "openai API" for component in bom["components"])
    assert any(component["name"] == "web_search" for component in bom["components"])


def test_spdx_empty_inventory_structure_and_required_fields():
    doc = to_spdx(AIBOMInventory(), META)

    assert doc["spdxVersion"] == "SPDX-2.3"
    assert doc["dataLicense"] == "CC0-1.0"
    assert doc["SPDXID"] == "SPDXRef-DOCUMENT"
    assert doc["documentNamespace"] == META["document_namespace"]
    assert doc["creationInfo"]["created"] == META["timestamp"]


def test_spdx_root_package_and_describes_relationship():
    doc = to_spdx(AIBOMInventory(), META)

    assert _spdx_package(doc, "SPDXRef-Root-SerializerFixture")
    assert {
        "spdxElementId": "SPDXRef-DOCUMENT",
        "relationshipType": "DESCRIBES",
        "relatedSpdxElement": "SPDXRef-Root-SerializerFixture",
    } in doc["relationships"]


def test_spdx_direct_dependency_relationship():
    dependency = _dep("python", "requests", "2.31.0")

    doc = to_spdx(AIBOMInventory(dependencies=[dependency]), META)

    dep_id = _spdx_id_for_package(doc, "requests", "2.31.0")
    assert _relationship(doc, "SPDXRef-Root-SerializerFixture", "DEPENDS_ON", dep_id)


def test_spdx_transitive_parent_child_relationship():
    parent = _dep("npm", "wrapper", "1.0.0")
    child = _dep(
        "npm", "openai", "4.0.0", DependencyScope.TRANSITIVE, [parent.package_id], True
    )

    doc = to_spdx(AIBOMInventory(dependencies=[parent, child]), META)

    parent_id = _spdx_id_for_package(doc, "wrapper", "1.0.0")
    child_id = _spdx_id_for_package(doc, "openai", "4.0.0")
    assert _relationship(doc, parent_id, "DEPENDS_ON", child_id)


def test_spdx_shared_transitive_dependency():
    parent_a = _dep("npm", "wrapper-a", "1.0.0")
    parent_b = _dep("npm", "wrapper-b", "1.0.0")
    child = _dep(
        "npm",
        "openai",
        "4.0.0",
        DependencyScope.TRANSITIVE,
        [parent_a.package_id, parent_b.package_id],
        True,
    )

    doc = to_spdx(AIBOMInventory(dependencies=[parent_a, parent_b, child]), META)

    child_id = _spdx_id_for_package(doc, "openai", "4.0.0")
    assert _relationship(
        doc, _spdx_id_for_package(doc, "wrapper-a", "1.0.0"), "DEPENDS_ON", child_id
    )
    assert _relationship(
        doc, _spdx_id_for_package(doc, "wrapper-b", "1.0.0"), "DEPENDS_ON", child_id
    )


def test_spdx_multiple_versions_remain_separate_and_ids_valid():
    inventory = AIBOMInventory(
        dependencies=[_dep("npm", "foo", "1.0.0"), _dep("npm", "foo", "2.0.0")]
    )

    doc = to_spdx(inventory, META)

    first = _spdx_id_for_package(doc, "foo", "1.0.0")
    second = _spdx_id_for_package(doc, "foo", "2.0.0")
    assert first != second
    assert all(
        re.fullmatch(r"SPDXRef-[A-Za-z0-9.-]+", package["SPDXID"])
        for package in doc["packages"]
    )


def test_spdx_scoped_npm_purl_external_reference():
    inventory = AIBOMInventory(
        dependencies=[_dep("npm", "@anthropic-ai/sdk", "1.2.3", ai=True)]
    )

    package = _spdx_package_by_name(to_spdx(inventory, META), "@anthropic-ai/sdk")
    external_ref = package["externalRefs"][0]

    assert external_ref["referenceCategory"] == "PACKAGE-MANAGER"
    assert external_ref["referenceType"] == "purl"
    assert external_ref["referenceLocator"] == "pkg:npm/%40anthropic-ai/sdk@1.2.3"


def test_spdx_unknown_version_handling():
    inventory = AIBOMInventory(dependencies=[_dep("python", "openai", None, ai=True)])

    package = _spdx_package_by_name(to_spdx(inventory, META), "openai")

    assert package["versionInfo"] == "NOASSERTION"


def test_spdx_ai_classification_annotation():
    dependency = _dep("python", "openai", "1.2.3", ai=True)

    doc = to_spdx(AIBOMInventory(dependencies=[dependency]), META)
    package_id = _spdx_id_for_package(doc, "openai", "1.2.3")
    annotation = _annotation_for(doc, package_id)

    assert "air-blackbox:ai-dependency=true" in annotation["comment"]
    assert "air-blackbox:ai-category=llm-sdk" in annotation["comment"]
    assert "air-blackbox:provider=OpenAI" in annotation["comment"]


def test_spdx_runtime_model_with_provider_version_and_unknowns():
    inventory = AIBOMInventory(
        runtime_models=[
            RuntimeModelComponent("gpt-4o", "OpenAI", "2024-08-06", 1, 10),
            RuntimeModelComponent("unknown-model", None, None, 1, 0),
        ]
    )

    doc = to_spdx(inventory, META)
    known = _spdx_package_by_name(doc, "gpt-4o")
    unknown = _spdx_package_by_name(doc, "unknown-model")

    assert known["versionInfo"] == "2024-08-06"
    assert known["supplier"] == "Organization: OpenAI"
    assert unknown["versionInfo"] == "NOASSERTION"
    assert unknown["supplier"] == "NOASSERTION"
    assert "air-blackbox:model=true" in _annotation_for(doc, known["SPDXID"])["comment"]


def test_spdx_relationship_refs_resolve_ids_unique_and_ordered():
    doc = to_spdx(_graph_inventory(), META)
    ids = [package["SPDXID"] for package in doc["packages"]]
    valid = set(ids) | {"SPDXRef-DOCUMENT"}

    assert len(ids) == len(set(ids))
    assert doc["relationships"] == sorted(
        doc["relationships"], key=lambda r: tuple(r.values())
    )
    for relationship in doc["relationships"]:
        assert relationship["spdxElementId"] in valid
        assert relationship["relatedSpdxElement"] in valid


def test_spdx_deterministic_output_when_fixed_metadata_supplied():
    first = to_spdx(_graph_inventory(), META)
    second = to_spdx(copy.deepcopy(_graph_inventory()), META)

    assert first == second


def test_cross_format_dependency_identities_and_graph_match():
    inventory = _graph_inventory()
    cdx = to_cyclonedx(inventory, META)
    spdx = to_spdx(inventory, META)

    cdx_purls = {c["purl"] for c in cdx["components"] if c.get("purl")}
    spdx_purls = {
        ref["referenceLocator"]
        for package in spdx["packages"]
        for ref in package.get("externalRefs", [])
    }
    assert cdx_purls == spdx_purls
    assert _depends_on(cdx, "root:serializer-fixture") == [
        "pkg:npm/wrapper-a@1.0.0",
        "pkg:npm/wrapper-b@1.0.0",
    ]
    assert _relationship(
        spdx,
        "SPDXRef-Root-SerializerFixture",
        "DEPENDS_ON",
        _spdx_id_for_package(spdx, "wrapper-a", "1.0.0"),
    )


def test_cross_format_runtime_model_identities_and_no_invented_versions():
    inventory = AIBOMInventory(
        runtime_models=[RuntimeModelComponent("mystery", None, None, 1, 2)]
    )

    cdx = to_cyclonedx(inventory, META)
    spdx = to_spdx(inventory, META)
    cdx_model = _single_model_component(cdx)
    spdx_model = _spdx_package_by_name(spdx, "mystery")

    assert cdx_model["name"] == spdx_model["name"]
    assert "version" not in cdx_model
    assert spdx_model["versionInfo"] == "NOASSERTION"


def test_warnings_are_not_serialized_as_components():
    inventory = AIBOMInventory(warnings=["do not serialize"])

    cdx = to_cyclonedx(inventory, META)
    spdx = to_spdx(inventory, META)

    assert all(
        component.get("name") != "do not serialize" for component in cdx["components"]
    )
    assert all(
        package.get("name") != "do not serialize" for package in spdx["packages"]
    )


def test_discovery_to_serializer_integration_fixture(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"wrapper":"1.0.0"}}', encoding="utf-8"
    )
    (tmp_path / "package-lock.json").write_text(
        """
{
  "lockfileVersion": 3,
  "packages": {
    "": {"dependencies": {"wrapper": "1.0.0"}},
    "node_modules/wrapper": {"version": "1.0.0", "dependencies": {"openai": "4.0.0"}},
    "node_modules/openai": {"version": "4.0.0"}
  }
}
""",
        encoding="utf-8",
    )
    result = discover_dependencies(tmp_path, AIClassifier())
    inventory = AIBOMInventory(dependencies=result.dependencies)

    cdx = to_cyclonedx(inventory, META)
    spdx = to_spdx(inventory, META)

    assert _depends_on(cdx, "pkg:npm/wrapper@1.0.0") == ["pkg:npm/openai@4.0.0"]
    assert _relationship(
        spdx,
        _spdx_id_for_package(spdx, "wrapper", "1.0.0"),
        "DEPENDS_ON",
        _spdx_id_for_package(spdx, "openai", "4.0.0"),
    )


def _dep(
    ecosystem,
    name,
    version,
    scope=DependencyScope.DIRECT,
    parents=None,
    ai=False,
):
    normalized = name.lower().replace("_", "-")
    package_id = (
        f"pkg:pypi/{normalized}{'@' + version if version else ''}"
        if ecosystem == "python"
        else f"pkg:npm/{normalized.replace('@', '%40')}{'@' + version if version else ''}"
    )
    classification = (
        AIClassification(True, "llm-sdk", "AI SDK", normalized, "OpenAI")
        if ai
        else AIClassification(False)
    )
    return DependencyComponent(
        package_name=name,
        normalized_name=normalized,
        version=version,
        ecosystem=ecosystem,
        scope=scope,
        source_manifest="package-lock.json"
        if ecosystem == "npm"
        else "requirements.txt",
        package_id=package_id,
        parent_dependencies=parents or [],
        ai_classification=classification,
    )


def _graph_inventory():
    parent_a = _dep("npm", "wrapper-a", "1.0.0")
    parent_b = _dep("npm", "wrapper-b", "1.0.0")
    child = _dep(
        "npm",
        "openai",
        "4.0.0",
        DependencyScope.TRANSITIVE,
        [parent_a.package_id, parent_b.package_id],
        True,
    )
    return AIBOMInventory(dependencies=[child, parent_b, parent_a])


def _props(component):
    return {prop["name"]: prop["value"] for prop in component.get("properties", [])}


def _cdx_component(bom, bom_ref):
    matches = [
        component for component in bom["components"] if component["bom-ref"] == bom_ref
    ]
    assert len(matches) == 1
    return matches[0]


def _depends_on(bom, ref):
    matches = [entry for entry in bom["dependencies"] if entry["ref"] == ref]
    assert len(matches) == 1
    return matches[0]["dependsOn"]


def _single_model_component(bom):
    models = [
        component
        for component in bom["components"]
        if component["type"] == "machine-learning-model"
    ]
    assert len(models) == 1
    return models[0]


def _spdx_package(doc, spdx_id):
    matches = [package for package in doc["packages"] if package["SPDXID"] == spdx_id]
    assert len(matches) == 1
    return matches[0]


def _spdx_package_by_name(doc, name):
    matches = [package for package in doc["packages"] if package["name"] == name]
    assert len(matches) == 1
    return matches[0]


def _spdx_id_for_package(doc, name, version):
    matches = [
        package
        for package in doc["packages"]
        if package["name"] == name and package["versionInfo"] == version
    ]
    assert len(matches) == 1
    return matches[0]["SPDXID"]


def _relationship(doc, source, relationship_type, target):
    return {
        "spdxElementId": source,
        "relationshipType": relationship_type,
        "relatedSpdxElement": target,
    } in doc["relationships"]


def _annotation_for(doc, spdx_id):
    matches = [
        annotation
        for annotation in doc["annotations"]
        if annotation["SPDXID"] == spdx_id
    ]
    assert len(matches) == 1
    return matches[0]
