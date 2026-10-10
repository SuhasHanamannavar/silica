# Base-Model Research & Selection Report (Phase 1 of model mission)

## Ranked recommendation
1. **Strongest practical base: Qwen/Qwen2.5-Coder-14B-Instruct** (Apache 2.0)
   - Best-in-class open code model; strong Verilog/SystemVerilog; tool-use capable;
     128k context; permissive license. Higher cost than 7B but justified for RTL gen/diagnosis.
2. **Smaller/frequent-task model: Qwen/Qwen2.5-Coder-7B-Instruct** (Apache 2.0) — default now.
   - Sufficient for spec structuring, log summarization, simple testbench gen; low latency/cost.
3. **Specialist HDL candidate to evaluate: nvidia/Llama-3.1-Nemotron-70B-Instruct** (Llama 3.1 license)
   - Upper-bound reference for engineering reasoning; too costly for per-stage calls;
     use as teacher/distillation reference only.
4. **Architecture decision: shared base + specialist LoRA adapters.**
   A single 7B/14B base with per-agent LoRA adapters (rtl, verification, eda-debug,
   physical/timing) gives the best measured trade-off: shared inference infra,
   per-task specialization, cheap rollback. Separate full models only if an adapter
   fails the acceptance gate.

## Rejected (with reason)
- StarCoder2-7b/15b: weaker reasoning than Qwen2.5-Coder; no clear advantage.
- DeepSeek-Coder-V2: MoE, costly to serve; license (DeepSeek Open) requires review.
- Llama-3.1-8B generalist: needs heavy RTL fine-tune; starts below Qwen-Coder on HDL.
- Any closed API (GPT-4/Claude): not deployable on HF; privacy risk for proprietary RTL.

## Acceptance gate (numeric thresholds set after baseline run)
- RTL synth. pass ≥ baseline + 5%
- Simulation pass ≥ baseline + 5%
- Repair success ≥ baseline + 5%
- Hallucination rate ≤ baseline + 3% (must not increase)
- p95 latency < 30s per stage call on chosen serving infra
