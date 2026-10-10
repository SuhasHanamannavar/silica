#!/usr/bin/env python3
"""
Reproducible LoRA / SFT fine-tuning script for Silica specialist agents (Phase 4.3).
Intended to run on an external GPU environment (this VM has NO GPU — do not claim
training completed here). Uses Hugging Face Transformers + PEFT + datasets.

Usage (on a GPU host with the dataset prepared by dataset_prep.py):
  pip install -r training/requirements.txt
  HF_TOKEN=hf_... python3 training/train_lora.py \
      --base_model Qwen/Qwen2.5-Coder-7B-Instruct \
      --dataset data/silica_sft/train.jsonl \
      --output_dir models/silica-rtl-lora-v1 \
      --num_train_epochs 3 --batch_size 2 --lr 2e-4

The trained adapter is pushed to HF Hub with a versioned model card. Register
the new revision in silica_agents/hf_serving.py via SILICA_LLM_MODEL env var.
"""
import argparse, os, json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--num_train_epochs", type=float, default=3)
    ap.add_argument("--batch_size", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora_r", type=int, default=16)
    ap.add_argument("--lora_alpha", type=int, default=32)
    ap.add_argument("--push_to_hub", action="store_true")
    args = ap.parse_args()

    # Guard: refuse to run on a CPU-only host to avoid pretending training happened.
    try:
        import torch
        if not torch.cuda.is_available():
            print("ERROR: no GPU detected. This script must run on a CUDA host. "
                  "It has NOT been executed here. Exiting.")
            return 2
    except ImportError:
        print("ERROR: torch not installed. pip install -r training/requirements.txt on a GPU host.")
        return 2

    from datasets import load_dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model, TaskType

    tok = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    tok.pad_token = tok.eos_token
    ds = load_dataset("json", data_files=args.dataset, split="train")

    def fmt(ex):
        return {"text": f"<|im_start|>system\n{ex['system']}<|im_end|>\n"
                        f"<|im_start|>user\n{ex['user']}<|im_end|>\n"
                        f"<|im_start|>assistant\n{ex['assistant']}<|im_end|>"}
    ds = ds.map(fmt)
    cols = ds.column_names
    ds = ds.map(lambda e: tok(e["text"], truncation=True, max_length=1024), batched=True, remove_columns=cols)

    model = AutoModelForCausalLM.from_pretrained(args.base_model, torch_dtype="bfloat16", trust_remote_code=True)
    lora = LoraConfig(task_type=TaskType.CAUSAL_LM, r=args.lora_r, lora_alpha=args.lora_alpha,
                      lora_dropout=0.05, target_modules=["q_proj","k_proj","v_proj","o_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir=args.output_dir, num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.batch_size, learning_rate=args.lr,
        logging_steps=10, save_strategy="epoch", bf16=True,
        report_to="none", push_to_hub=args.push_to_hub,
        hub_model_id=os.path.basename(args.output_dir),
    )
    trainer = Trainer(model=model, args=targs, train_dataset=ds)
    trainer.train()
    trainer.save_model(args.output_dir)
    tok.save_pretrained(args.output_dir)

    # versioned model card
    card = {
        "base_model": args.base_model, "lora_r": args.lora_r, "lora_alpha": args.lora_alpha,
        "epochs": args.num_train_epochs, "lr": args.lr, "dataset": args.dataset,
        "trained_at": "external GPU host (not this VM)", "silica_prompt_version": "silica-prompts-v1.0.0",
    }
    with open(os.path.join(args.output_dir, "silica_training_meta.json"), "w") as f:
        json.dump(card, f, indent=2)
    print(f"Training complete. Adapter saved to {args.output_dir}. "
          f"Promote only after eval/benchmark.py shows measurable improvement over baseline.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
