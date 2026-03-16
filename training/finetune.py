"""
AIR Blackbox — EU AI Act Compliance LLM Fine-Tune
==================================================
Fine-tunes Llama-3.1-8B-Instruct using Unsloth + LoRA on 4,602 compliance
analysis examples. The resulting model replaces regex-based pattern matching
with actual reasoning about EU AI Act compliance.

Requirements:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps "trl<0.9.0" peft accelerate bitsandbytes

Usage:
    python finetune.py                      # Full train
    python finetune.py --test               # Quick 10-step test run
    python finetune.py --push-to-hub        # Train + push to HuggingFace Hub

Output:
    ./air-compliance-model/          — merged fp16 model
    ./air-compliance-model-gguf/     — GGUF quantized (Q4_K_M, Q8_0)
    ./air-compliance-lora/           — LoRA adapter only
"""

import argparse
import json
import os

def load_training_data(path="training_data_combined_v3.jsonl"):
    """Load JSONL training data into Alpaca-style format for SFT."""
    examples = []
    with open(path, "r") as f:
        for line in f:
            row = json.loads(line.strip())
            # Handle both string and dict output formats
            output = row.get("output", "")
            if isinstance(output, dict):
                output = json.dumps(output, indent=2)

            examples.append({
                "instruction": row.get("instruction", ""),
                "input": row.get("input", ""),
                "output": output,
            })
    print(f"Loaded {len(examples):,} training examples")
    return examples


def format_alpaca(example):
    """Format a single example as an Alpaca-style prompt."""
    if example["input"]:
        return f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{example['instruction']}

### Input:
{example['input']}

### Response:
{example['output']}"""
    else:
        return f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{example['instruction']}

### Response:
{example['output']}"""


def main():
    parser = argparse.ArgumentParser(description="AIR Blackbox Compliance LLM Fine-Tune")
    parser.add_argument("--test", action="store_true", help="Quick test run (10 steps)")
    parser.add_argument("--push-to-hub", action="store_true", help="Push to HuggingFace Hub after training")
    parser.add_argument("--hub-model", default="airblackbox/air-compliance-llama3.1-8b", help="HuggingFace Hub model name")
    parser.add_argument("--data", default="training_data_combined_v3.jsonl", help="Training data path")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Per-device batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument("--max-seq-length", type=int, default=4096, help="Max sequence length")
    parser.add_argument("--no-gguf", action="store_true", help="Skip GGUF quantization")
    args = parser.parse_args()

    # ── Step 1: Load data ──
    print("=" * 60)
    print("AIR Blackbox — EU AI Act Compliance LLM Fine-Tune")
    print("=" * 60)

    examples = load_training_data(args.data)

    # ── Step 2: Load model with Unsloth ──
    print("\n[1/5] Loading Llama-3.1-8B-Instruct with 4-bit quantization...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        max_seq_length=args.max_seq_length,
        dtype=None,  # Auto-detect
        load_in_4bit=True,
    )

    # ── Step 3: Apply LoRA adapters ──
    print(f"\n[2/5] Applying LoRA adapters (r={args.lora_r}, alpha={args.lora_alpha})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=args.lora_alpha,
        lora_dropout=0,  # Optimized for Unsloth
        bias="none",
        use_gradient_checkpointing="unsloth",  # 30% less VRAM
        random_state=3407,
    )

    # Print trainable parameters
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"   Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ── Step 4: Prepare dataset ──
    print(f"\n[3/5] Preparing {len(examples):,} training examples...")
    from datasets import Dataset

    formatted = [{"text": format_alpaca(ex)} for ex in examples]
    dataset = Dataset.from_list(formatted)

    # ── Step 5: Train ──
    print(f"\n[4/5] Training for {'10 steps (test mode)' if args.test else f'{args.epochs} epochs'}...")
    from trl import SFTTrainer
    from transformers import TrainingArguments

    max_steps = 10 if args.test else -1
    num_epochs = 1 if args.test else args.epochs

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        dataset_num_proc=2,
        packing=True,  # Pack short examples together for efficiency
        args=TrainingArguments(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=4,
            warmup_steps=5 if args.test else 50,
            max_steps=max_steps,
            num_train_epochs=num_epochs,
            learning_rate=args.lr,
            fp16=True,
            logging_steps=1 if args.test else 25,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir="./training_output",
            report_to="none",
            save_strategy="epoch" if not args.test else "no",
        ),
    )

    print("\n" + "─" * 40)
    stats = trainer.train()
    print("─" * 40)
    print(f"\n   Training loss: {stats.training_loss:.4f}")
    print(f"   Training time: {stats.metrics.get('train_runtime', 0):.0f}s")

    # ── Step 6: Save ──
    print("\n[5/5] Saving model...")

    # Save LoRA adapter
    model.save_pretrained("./air-compliance-lora")
    tokenizer.save_pretrained("./air-compliance-lora")
    print("   LoRA adapter saved to ./air-compliance-lora/")

    # Save merged fp16 model
    model.save_pretrained_merged("./air-compliance-model", tokenizer, save_method="merged_16bit")
    print("   Merged fp16 model saved to ./air-compliance-model/")

    # GGUF quantization
    if not args.no_gguf:
        print("\n   Quantizing to GGUF (Q4_K_M + Q8_0)...")
        try:
            model.save_pretrained_gguf(
                "./air-compliance-model-gguf",
                tokenizer,
                quantization_method=["q4_k_m", "q8_0"],
            )
            print("   GGUF models saved to ./air-compliance-model-gguf/")
        except Exception as e:
            print(f"   GGUF quantization failed (may need llama.cpp): {e}")
            print("   You can quantize manually with: python -m llama_cpp.convert ...")

    # Push to Hub
    if args.push_to_hub:
        print(f"\n   Pushing to HuggingFace Hub: {args.hub_model}")
        model.push_to_hub_merged(args.hub_model, tokenizer, save_method="merged_16bit")
        print(f"   Model available at: https://huggingface.co/{args.hub_model}")

    print("\n" + "=" * 60)
    print("DONE! Your EU AI Act compliance LLM is ready.")
    print("=" * 60)
    print(f"""
Next steps:
  1. Test locally:
     from unsloth import FastLanguageModel
     model, tok = FastLanguageModel.from_pretrained("./air-compliance-model")

  2. Run with Ollama (GGUF):
     ollama create air-compliance -f Modelfile
     ollama run air-compliance "Analyze this code for EU AI Act compliance..."

  3. Integrate with AIR Blackbox scanner:
     air-blackbox scan --model ./air-compliance-model --scan /path/to/project
""")


if __name__ == "__main__":
    main()
