# AIR Blackbox

**AI governance control plane — compliance, inventory, incident response, and audit for AI agents.**

[![PyPI](https://img.shields.io/pypi/v/air-blackbox)](https://pypi.org/project/air-blackbox/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/airblackbox/gateway/blob/main/LICENSE)
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
| `discover` | AI-BOM (CycloneDX), shadow AI detection, model version tracking |
| `replay` | Full incident reconstruction, HMAC chain verification |
| `export` | Signed evidence package: compliance + AI-BOM + audit chain |

## Links

- **Website**: [airblackbox.ai](https://airblackbox.ai)
- **Gateway**: [github.com/airblackbox/gateway](https://github.com/airblackbox/gateway)
- **Docs**: [gateway/docs](https://github.com/airblackbox/gateway/tree/main/docs)
- **License**: Apache-2.0
