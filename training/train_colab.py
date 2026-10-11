#!/usr/bin/env python3
"""Silica LoRA fine-tuning — run on Colab T4 GPU. Usage: HF_TOKEN=hf_... STAGE=rtl python3 train_colab.py"""
import os, torch
from datasets import load_dataset
from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
from peft import LoraConfig, TaskType
from trl import SFTTrainer

STAGE = os.environ.get("STAGE", "rtl")
BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
USER = "SILICAM"
OUTPUT_REPO = f"{USER}/silica-{STAGE}-lora-v1"
DATASET_REPO = f"{USER}/silica-{STAGE}-data"
HF_TOKEN = os.environ.get("HF_TOKEN")

print(f"=== Silica {STAGE.upper()} LoRA training -> {OUTPUT_REPO} ===")
login(token=HF_TOKEN)
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'}")

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, quantization_config=bnb, device_map="auto", trust_remote_code=True)

peft = LoraConfig(task_type=TaskType.CAUSAL_LM, r=16, lora_alpha=32, lora_dropout=0.05,
                  target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])

ds = load_dataset(DATASET_REPO, split="train")
def fmt(b):
    return {"text": [f"<|im_start|>system\n{s}<|im_end|>\n<|im_start|>user\n{u}<|im_end|>\n<|im_start|>assistant\n{a}<|im_end|>"
                     for s,u,a in zip(b["system"], b["user"], b["assistant"])]}
ds = ds.map(fmt, batched=True)

args = TrainingArguments(output_dir=f"./silica-{STAGE}", num_train_epochs=3, per_device_train_batch_size=2,
    gradient_accumulation_steps=4, learning_rate=2e-4, bf16=True, logging_steps=2, save_strategy="no",
    report_to="none", push_to_hub=True, hub_model_id=OUTPUT_REPO, hub_token=HF_TOKEN)

trainer = SFTTrainer(model=model, train_dataset=ds, dataset_text_field="text", max_seq_length=1024,
                     tokenizer=tok, args=args, peft_config=peft)
trainer.train()
trainer.push_to_hub()
tok.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
print(f"DONE. Adapter pushed to https://huggingface.co/{OUTPUT_REPO}")
