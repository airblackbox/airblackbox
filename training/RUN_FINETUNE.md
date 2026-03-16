# AIR Blackbox — Fine-Tune Guide

## Quick Start (Google Colab — Free GPU)

1. Upload `training_data_combined_v3.jsonl` and `finetune.py` to Colab
2. Run:

```python
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps "trl<0.9.0" peft accelerate bitsandbytes datasets

# Test run first (10 steps, ~2 min)
!python finetune.py --test

# Full training (~45 min on T4, ~20 min on A100)
!python finetune.py --push-to-hub --hub-model airblackbox/air-compliance-llama3.1-8b
```

## What You Get

| Output | Path | Size |
|--------|------|------|
| LoRA adapter | `./air-compliance-lora/` | ~50MB |
| Merged fp16 model | `./air-compliance-model/` | ~16GB |
| GGUF Q4_K_M | `./air-compliance-model-gguf/` | ~4.5GB |
| GGUF Q8_0 | `./air-compliance-model-gguf/` | ~8.5GB |

## Run with Ollama (Local)

```bash
cd training/
ollama create air-compliance -f Modelfile
ollama run air-compliance "from langchain import Agent..."
```

## Training Data Stats

- **4,602 examples** covering all 6 EU AI Act articles
- Frameworks: LangChain, CrewAI, OpenAI, Claude Agent SDK, Haystack, AutoGen
- Mix of: full analyses, single-article findings, compliant + non-compliant code
- Output format: structured markdown with article-by-article findings

## GPU Requirements

| GPU | Estimated Time | VRAM Used |
|-----|---------------|-----------|
| T4 (Colab Free) | ~45 min | ~12GB |
| A100 40GB | ~20 min | ~18GB |
| RTX 4090 | ~25 min | ~20GB |

## Why This Matters

The regex scanner catches patterns. The fine-tuned model **reasons** about compliance:
- Understands code semantics, not just keyword matching
- Catches subtle compliance gaps that regex misses
- Generates specific, actionable recommendations
- Scores code quality on a nuanced scale
