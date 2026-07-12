# AIR Blackbox

**AI governance control plane — compliance, inventory, incident response, and audit for AI agents.**

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/airblackbox/airblackbox/blob/main/LICENSE)
[![EU AI Act](https://img.shields.io/badge/EU_AI_Act-ready-green)](https://airblackbox.ai)

## Install

```bash
pip install air-blackbox
```

With framework support:

```bash
pip install air-blackbox[langchain]    # LangChain trust layer
pip install air-blackbox[crewai]       # CrewAI trust layer
pip install air-blackbox[openai]       # OpenAI Agents SDK trust layer
pip install air-blackbox[all]          # Everything
```

## Four Commands

```bash
air-blackbox comply      # EU AI Act compliance from live traffic
air-blackbox discover    # Shadow AI inventory + AI-BOM generation
air-blackbox replay      # Incident reconstruction from audit chain
air-blackbox export      # Signed evidence bundle for auditors
```

## Quick Start

```python
from air_blackbox import AirBlackbox

air = AirBlackbox()
client = air.wrap(openai.OpenAI())
# Every LLM call is now HMAC-logged through the gateway
```

With framework auto-detection:

```python
from air_blackbox import AirTrust

trust = AirTrust()
trust.attach(your_langchain_agent)
# Framework auto-detected. Audit trails active.
```

## What It Does

| Command | What You Get |
|---------|-------------|
| `comply` | Per-article EU AI Act status (Art. 9-15) from live gateway traffic |
| `discover` | Runtime AI inventory plus static dependency AI-BOM/SBOM output in table, CycloneDX 1.6, or SPDX 2.3 |
| `replay` | Full incident reconstruction, HMAC chain verification |
| `export` | Signed evidence package: compliance + AI-BOM + audit chain |

## Discover AI-BOM and SBOM Output

```bash
air-blackbox discover --scan-path . --format table
air-blackbox discover --scan-path . --format cyclonedx
air-blackbox discover --scan-path . --format spdx
air-blackbox discover --scan-path . --format json   # alias for CycloneDX 1.6 JSON
```

`discover` combines runtime-observed models, providers, and tools with static package dependency scanning. Static scanning still works when no gateway traffic or `.air.json` records exist.

Supported static manifests:

- `requirements.txt`: declared direct Python dependencies only.
- `pyproject.toml`: PEP 621 direct and optional Python dependencies only.
- `package.json`: direct npm dependencies; `devDependencies` are currently excluded.
- `package-lock.json`: npm lockfile v2/v3 installed direct and transitive dependencies when graph data is available.

Discovery does not perform Python transitive resolution, inspect global environments, call package managers, or use the network. Each package in a reliable dependency graph is classified independently, so an AI SDK can be detected even when it is only transitive, for example `application -> wrapper-package -> openai`.

Custom classifier rules extend the built-in AI-library list, and matching custom rules override defaults:

```bash
air-blackbox discover   --scan-path .   --ai-libraries custom-ai-libraries.yaml   --format cyclonedx
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

Python package names use PEP 503 normalization. npm scoped package names are supported. Invalid explicit classifier configuration exits with an error before emitting machine-readable output.

Use `--output` to write machine-readable JSON:

```bash
air-blackbox discover --scan-path . --format spdx --output sbom.spdx.json
```

Warnings and diagnostics go to stderr. JSON files use UTF-8 and end with a newline. Table output cannot be combined with `--output`.

Model metadata includes model name, provider when observed, and explicit model version when available. The AIR record/schema version is not used as a model version. SPDX 2.3 represents runtime models as packages with annotations; formal schema validation is not currently part of the test suite.


## Links

- **Website**: [airblackbox.ai](https://airblackbox.ai)
- **Gateway**: [github.com/airblackbox/airblackbox](https://github.com/airblackbox/airblackbox)
- **Docs**: [gateway/docs](https://github.com/airblackbox/airblackbox/tree/main/docs)
- **License**: Apache-2.0
