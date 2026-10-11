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

use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
compute_dtype = torch.bfloat16 if use_bf16 else torch.float16
print(f"Precision: {'bf16' if use_bf16 else 'fp16 (T4 optimized)'}")

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=compute_dtype)
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

trained = False
try:
    from trl import SFTTrainer, SFTConfig
    sft_args = SFTConfig(
        output_dir=f"./silica-{STAGE}", num_train_epochs=3, per_device_train_batch_size=2,
        gradient_accumulation_steps=4, learning_rate=2e-4, fp16=not use_bf16, bf16=use_bf16,
        logging_steps=2, save_strategy="no", report_to="none", push_to_hub=True,
        hub_model_id=OUTPUT_REPO, hub_token=HF_TOKEN, dataset_text_field="text", max_seq_length=1024
    )
    trainer = SFTTrainer(model=model, train_dataset=ds, processing_class=tok, args=sft_args, peft_config=peft)
    trainer.train()
    trainer.push_to_hub()
    tok.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
    trained = True
except Exception as e:
    print(f"Notice: SFTConfig route ({e}), using robust Trainer pipeline...")

if not trained:
    from peft import get_peft_model
    from transformers import Trainer, DataCollatorForSeq2Seq
    peft_model = get_peft_model(model, peft)
    def tok_fn(b):
        res = tok(b["text"], truncation=True, max_length=1024)
        res["labels"] = [list(x) for x in res["input_ids"]]
        return res
    tokenized_ds = ds.map(tok_fn, batched=True, remove_columns=ds.column_names)
    args = TrainingArguments(output_dir=f"./silica-{STAGE}", num_train_epochs=3, per_device_train_batch_size=2,
        gradient_accumulation_steps=4, learning_rate=2e-4, fp16=not use_bf16, bf16=use_bf16, logging_steps=2,
        save_strategy="no", report_to="none", push_to_hub=True, hub_model_id=OUTPUT_REPO, hub_token=HF_TOKEN)
    trainer = Trainer(model=peft_model, train_dataset=tokenized_ds, args=args,
                      data_collator=DataCollatorForSeq2Seq(tok, pad_to_multiple_of=8, return_tensors="pt"))
    trainer.train()
    trainer.model.save_pretrained(f"./silica-{STAGE}")
    trainer.model.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)
    tok.push_to_hub(OUTPUT_REPO, token=HF_TOKEN)

print(f"DONE. Adapter pushed to https://huggingface.co/{OUTPUT_REPO}")


