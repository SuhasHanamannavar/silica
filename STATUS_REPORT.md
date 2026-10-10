# Silica Implementation Status Report

Date: 2026-10-11. All claims below are backed by executed code; nothing is simulated.

## 1. Repository audit (Phase 1)
- **Stack**: zero-dependency Python stdlib backend (`server.py`), static HTML/CSS/JS frontend, Vercel static deployment (silica-kappa.vercel.app).
- **Working before**: monolithic 5-stage EDA flow (lint/compile/simulate/synthesis/report) with narrow rule-based recovery; real Verilator + Yosys when run locally; Vercel falls back to recorded transcript.
- **Missing**: specialist agents, typed contracts, HF model serving, multi-agent orchestration, eval benchmark, training pipeline, sandboxing, audit trails.
- **Environment verified**: 2 CPU cores, 3.9GB RAM, **no GPU**; Python 3.12; installed `verilator 4.038`, `yosys 0.9`, `iverilog`; `HF_TOKEN` not set; `SILICA_ALLOW_EXTERNAL_LLM=0` (privacy default).

## 2. Implemented & tested (real EDA execution)
| Component | Location | Status | Evidence |
|---|---|---|---|
| 8 specialist agents w/ typed contracts | `silica_agents/contracts.py`, `specialists.py` | ✅ Implemented | 4 active + 2 blocked (honest) + diagnosis + signoff |
| Domain-specific versioned prompts | `silica_agents/prompts.py` | ✅ v1.0.0 | recorded in every audit trail |
| HF serving adapter (retries, privacy guard, fallback, audit) | `silica_agents/hf_serving.py` | ✅ Implemented | health endpoint; deterministic fallback recorded |
| Sandboxed EDA execution (allowlist, timeout, env scrub) | `silica_agents/sandbox.py` | ✅ Implemented | violations return `blocked` |
| Multi-agent orchestrator (prereqs, checkpoint, recovery, cancel) | `silica_agents/orchestrator.py` | ✅ Tested | smoke + benchmark pass |
| Failure diagnosis & bounded recovery | `specialists.py:FailureDiagnosisAgent` | ✅ Tested | broken RTL recovered in 2 attempts from real Verilator evidence |
| Signoff honesty (never infers signoff from missing reports) | `specialists.py:SignoffReportAgent` | ✅ Tested | disposition = `incomplete_awaiting_human_review` when physical/timing blocked |
| Backend integration (server.py uses orchestrator) | `server.py` | ✅ Wired | `/api/agents/health`; `/api/projects/<id>/run` uses agent pipeline with fallback |
| Eval benchmark (6 cases, real EDA) | `eval/benchmark.py` | ✅ 6/6 PASS | see below |

## 3. Benchmark results (executed, real tools)
```
clean_counter_w4               PASS   (rtl+verif+synth passed)
broken_counter_recovered       PASS   (recovery=2, bounded; all stages pass)
clean_counter_w8               PASS   (parameterized width regression)
invalid_rtl_rejected           PASS   (empty RTL -> rtl_design failed, no false pass)
physical_timing_blocked_honest PASS   (phys=blocked timing=blocked, never passed)
signoff_not_falsely_complete   PASS   (disposition incomplete, not "passed")
OVERALL: ALL PASS
```

## 4. Hugging Face status (Phase 4)
- **Model serving adapter**: implemented and connected to every agent (`HFServingAdapter`). Default model `Qwen/Qwen2.5-Coder-7B-Instruct` (Apache 2.0). Configurable via `SILICA_LLM_MODEL`.
- **Privacy**: external LLM calls blocked unless `SILICA_ALLOW_EXTERNAL_LLM=1`; `HF_TOKEN` read from env only, never logged or exposed to frontend.
- **Model evaluation matrix**: `training/model_eval_matrix.md` (6 candidates, 5-metric protocol). **Not executed** — requires HF_TOKEN + consent. Baseline + deterministic fallback active.
- **Dataset prep**: `training/dataset_prep.py` — builds SFT examples only from real executed EDA runs (0 in repo data/; populated after real runs). Provenance + license + verification metadata preserved. Train/val/test split by design family.
- **Training script**: `training/train_lora.py` — reproducible LoRA/SFT (PEFT). **Refuses to run without GPU** (exits with error) — has NOT been executed here. Must run on external GPU host.
- **No fine-tuning claimed complete.** No model has been trained or uploaded to HF Hub.

## 5. Blocked / honestly labeled (not simulated)
- **Physical design (stage 5)**: BLOCKED — OpenROAD not installed; no PDK/LEF/LIB available.
- **Timing & physical verification (stage 6)**: BLOCKED — requires placed-and-routed design + OpenSTA/DRC tools.
- **LLM-augmented generation**: FALLBACK — deterministic baseline used (recorded in audit). Activates with `HF_TOKEN` + `SILICA_ALLOW_EXTERNAL_LLM=1`.
- **GPU training**: not available; scripts provided for external GPU.

## 6. Definition-of-Done checklist
- [x] Each specialist has defined scope, interface, tools, evaluation suite.
- [x] ≥1 complete supported engineering path executes real EDA tools end to end (spec→RTL→verif→synth).
- [x] Agent outputs checked by independent engineering validation (contract validators + real EDA).
- [x] ≥1 deliberately introduced failure diagnosed, bounded-recovered, regression-tested (broken counter case).
- [x] Baseline model evaluated against held-out engineering tasks (deterministic baseline; LLM matrix protocol defined, execution pending token).
- [ ] Fine-tuning completed — NOT DONE (no GPU); reproducible scripts provided.
- [x] HF deployment status verified OR blockers documented (adapter connected; external-call gated by privacy flag; no model trained).
- [x] Serving adapter connected to relevant agents.
- [x] Silica displays genuine progress/errors/artifacts (orchestrator events + logs persisted).
- [x] All unsupported stages explicitly identified (physical/timing blocked).
- [x] Setup/training/eval/deployment/rollback instructions documented (README + training/ + this report).

## 7. Next highest-priority engineering tasks
1. Obtain `HF_TOKEN`, set `SILICA_ALLOW_EXTERNAL_LLM=1`, run model-eval matrix; promote best model.
2. Install OpenROAD + sky130 PDK; unblock physical-design stage (floorplan→placement→route).
3. Install OpenSTA; add SDC constraint editor + real timing reports.
4. Populate SFT dataset from real executed runs; run LoRA on external GPU; benchmark improvement.
5. Per-stage log streaming + run-comparison view in UI.
6. User auth + per-project artifact storage.
