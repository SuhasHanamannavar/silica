# Hugging Face Model Deployment Guide (Phase 6)

## Current status (honest)
- **No model has been trained or uploaded.** This VM has no GPU; `train_lora.py`
  refuses to run without CUDA. No `HF_TOKEN` is configured. No weights exist.
- The **serving adapter is fully implemented and connected** to every Silica agent
  (`silica_agents/hf_serving.py`). It supports HF Inference API (serverless),
  dedicated endpoints, or self-hosted — configurable via env vars.
- To activate LLM augmentation: `HF_TOKEN=hf_... SILICA_ALLOW_EXTERNAL_LLM=1
  SILICA_LLM_MODEL=<model-revision> python3 server.py`. Without these, the
  deterministic baseline is used and the fallback is recorded in every audit trail.

## Model card template (training/MODEL_CARD_TEMPLATE.md)
Every promoted model must ship with this card in its HF repo.

```yaml
---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-7B-Instruct
tags: [semiconductor, rtl, verilog, eda, silica]
---
# Silica-<specialty>-<version>
- Architecture: <base> + LoRA (r=16, alpha=32, target=q/k/v/o_proj)
- Training data: <N> verified examples; provenance in data/silica_sft/; license per example
- Training config: epochs=<n>, lr=<lr>, batch=<bs>, seq_len=1024, bf16
- Evaluation: vs baseline on held-out RTLGen-20 / Verify-10 / Diag-15 / Hallucination-10 / ToolUse-10
  - RTL synth. pass: <baseline>% -> <new>%
  - Simulation pass: <baseline>% -> <new>%
  - Repair success: <baseline>% -> <new>%
  - Hallucination rate: <baseline>% -> <new>%
- Limitations: single-clock small designs; no physical-design claims; never signoff without independent EDA evidence
- Intended use: Silica specialist agent only; not for production signoff
- Rollback: previous revision <rev>; set SILICA_LLM_MODEL to roll back
```

## Deployment steps (on a GPU host or with trained adapter)
1. Run `python3 training/train_lora.py ...` on a CUDA host; adapter saved to `models/`.
2. `huggingface-cli login` (token with `write` scope).
3. `huggingface-cli upload SILICAM/silica-rtl-lora-v1 models/silica-rtl-lora-v1 . --include="*.safetensors,*.json,*.md,tokenizer*"`.
4. Verify endpoint: `python3 -c "from silica_agents.hf_serving import HFServingAdapter; h=HFServingAdapter(model='SILICAM/silica-rtl-lora-v1'); print(h.complete('...','generate a counter',64))"`.
5. Run `python3 eval/benchmark.py` with `SILICA_LLM_MODEL` set to the new revision; compare to baseline.
6. Promote only if ≥2 metrics improve ≥5% with no regression >3%.
7. Pin revision in `SILICA_LLM_MODEL` (include `@<commit-sha>` for immutability).

## Rollback
- `SILICA_LLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct` (baseline) — serving adapter picks it up at next agent call.
- Keep the last 3 accepted revisions; never delete a pinned revision from HF Hub.

## Privacy
- Proprietary RTL is never sent to external inference unless `SILICA_ALLOW_EXTERNAL_LLM=1`.
- `HF_TOKEN` read from env only; never logged, never in frontend, never in git.
- For private models, use a dedicated HF Inference Endpoint with private repo access.
