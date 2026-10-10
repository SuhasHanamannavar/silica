# Silica Model Evaluation Matrix (Phase 4.1)

Candidate open-weight code/reasoning models for Silica specialist agents.
Selection criteria: RTL correctness & synthesizability, Verilog/SystemVerilog
understanding, verification-test quality, EDA-log interpretation, failure
diagnosis & repair, tool-use accuracy, engineering-hallucination rate,
latency/memory/cost, license, and commercial-deployment restrictions.

| Model | Size | License | RTL synth. | Verilog understand | Testbench quality | EDA-log diag | Tool-use | Hallucination (est.) | Inference cost | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-Coder-7B-Instruct | 7B | Apache 2.0 | High | High | Med-High | Med-High | Good | Low-Med | Low (serverless) | Default; strong code, permissive license |
| Qwen/Qwen2.5-Coder-14B-Instruct | 14B | Apache 2.0 | High+ | High+ | High | High | Good | Low | Med | Better quality, 2x cost |
| deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct | 16B (MoE) | DeepSeek Open (commercial allowed w/ conditions) | High | High | Med | Med | Med | Low | Med | Strong Verilog; license review required |
| bigcode/starcoder2-7b | 7B | Apache 2.0 | Med | Med | Med | Low | Low | Med | Low | Weaker reasoning; good base for LoRA |
| meta-llama/Llama-3.1-8B-Instruct | 8B | Llama 3.1 (commercial allowed) | Med | Med-High | Med | Med | Good | Med | Low | Generalist; needs RTL fine-tune |
| nvidia/Llama-3.1-Nemotron-70B-Instruct | 70B | Llama 3.1 | Very High | Very High | High | High | Excellent | Very Low | High | Upper-bound reference; too costly for per-stage calls |

## Evaluation protocol (held-out engineering tasks)
1. **RTLGen-20**: 20 small spec→RTL tasks; score = % that pass Verilator lint + Yosys synth.
2. **Verify-10**: 10 RTL→testbench tasks; score = % with zero simulation mismatches.
3. **Diag-15**: 15 broken-RTL + real EDA-log pairs; score = % correctly root-caused & repaired (re-run passes).
4. **Hallucination-10**: 10 trick questions requiring "not enough evidence"; score = % that escalate rather than invent.
5. **ToolUse-10**: 10 tool-call sequences; score = % correct argv + no forbidden-tool calls.

Baseline = Qwen2.5-Coder-7B-Instruct with deterministic fallback + retrieval.
A candidate is promoted only if it improves ≥2 of 5 metrics by ≥5% absolute with
no regression >3% on any metric, and license permits commercial use.

## Status
- Baseline configured in `silica_agents/hf_serving.py` (env `SILICA_LLM_MODEL`).
- Held-out benchmark cases defined in `eval/benchmark.py` (real EDA execution).
- Full LLM-graded matrix NOT yet executed: requires `HF_TOKEN` + `SILICA_ALLOW_EXTERNAL_LLM=1`.
  Run with: `HF_TOKEN=... SILICA_ALLOW_EXTERNAL_LLM=1 python3 eval/benchmark.py`
  and compare per-model by setting `SILICA_LLM_MODEL`.
