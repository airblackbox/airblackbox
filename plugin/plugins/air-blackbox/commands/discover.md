---
description: Discover runtime AI components and static AI dependencies with AIR Blackbox
---

# /air-discover

Discover runtime-observed AI components and statically discovered AI-related dependencies in the current project.

## Steps

1. Run the AIR Blackbox discovery command from the project root:

```bash
air-blackbox discover --scan-path . --format table 2>&1 || echo "If air-blackbox is not installed, run: pip install air-blackbox"
```

2. Present the inventory in a concise table covering:
   - Runtime models, providers, and tools from gateway or `.air.json` records
   - Static package dependencies from supported manifests
   - Package ecosystem, version when known, direct/transitive scope, AI classification, and source manifest

3. For machine-readable AI-BOM/SBOM output, suggest one of:

```bash
air-blackbox discover --scan-path . --format cyclonedx --output aibom.cdx.json
air-blackbox discover --scan-path . --format spdx --output sbom.spdx.json
```

`--format json` remains an alias for CycloneDX 1.6 JSON. `--format spdx` targets SPDX 2.3 JSON. Warnings are written to stderr so JSON stdout remains parseable.

4. Explain static scanning accurately:
   - Supported files: `requirements.txt`, `pyproject.toml`, `package.json`, `package-lock.json`
   - Python manifests provide declared direct dependencies only
   - `package-lock.json` v2/v3 can provide reliable npm transitive dependencies
   - No package-manager commands or network calls are used
   - npm `devDependencies` are currently excluded

5. If the project uses private or internal AI SDKs, suggest a custom classifier file:

```bash
air-blackbox discover \
  --scan-path . \
  --ai-libraries custom-ai-libraries.yaml \
  --format cyclonedx
```

```yaml
version: 1
packages:
  python:
    my-ai-sdk:
      category: llm-sdk
      provider: Example AI
      reason: Internal AI SDK
  npm:
    "@example/ai-client":
      category: llm-sdk
      provider: Example AI
      reason: Internal AI client
```

Custom rules extend built-in defaults, and matching custom rules override defaults.
