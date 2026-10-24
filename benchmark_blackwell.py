"""
The Blackwell Benchmark: 
Feed Silica the 2022-era context (what NVIDIA knew when designing Blackwell).
See how close Silica gets to the ACTUAL Blackwell B200 specs.
"""
from typing import Dict
from product_architect.orchestrator import ProductArchitectOrchestrator

# 2022-era inputs — what architects knew when starting Blackwell design
BLACKWELL_INPUTS = {
    "product_brief": "Next-generation AI training and inference GPU, successor to Hopper H100. Optimize for trillion-parameter LLMs and agentic AI workloads. Must maintain full CUDA backwards compatibility.",
    "target_market": "hyperscale datacenter",
    "key_workloads": ["LLM training 70B+", "LLM autoregressive decode inference", "LLM prefill", "diffusion models"],
    "power_budget_w": 1000,
    "process_node": "TSMC 4nm",
    "competitors": ["AMD MI300", "Google TPU v5"],
}

# Actual Blackwell B200 specs (from public sources)
BLACKWELL_ACTUAL = {
    "sm_count": 148,
    "boost_clock_mhz": 2100,
    "hbm_generation": "HBM3e",
    "hbm_capacity_gb": 192,
    "hbm_bandwidth_tbs": 8.0,
    "hbm_stacks": 6,
    "l2_cache_mb": 192,
    "nvlink_generation": "5.0",
    "nvlink_bandwidth_tbs": 1.8,
    "chiplet_design": True,
    "fp8_support": True,
    "nvfp4_support": True,
    "tdp_watts": 1000,
}

def score_result(pipeline: Dict) -> Dict:
    """Score Silica's output against actual Blackwell specs."""
    func = pipeline["stages"]["functional_spec"]["spec"]
    nfr = pipeline["stages"]["non_functional_spec"]["spec"]
    
    sm = func.get("compute_architecture", {}).get("sm_architecture", {})
    hbm = func.get("memory_hierarchy", {}).get("hbm_subsystem", {})
    l2 = func.get("memory_hierarchy", {}).get("l2_cache", {})
    nvlink = func.get("interconnect", {}).get("nvlink", {})
    area = nfr.get("area_budget", {})
    
    scores = {}
    
    # SM count: within 20% = correct
    sm_count = sm.get("total_sm_count", 0)
    sm_error = abs(sm_count - BLACKWELL_ACTUAL["sm_count"]) / BLACKWELL_ACTUAL["sm_count"]
    scores["sm_count"] = {
        "silica": sm_count,
        "actual": BLACKWELL_ACTUAL["sm_count"], 
        "error_pct": round(sm_error * 100, 1),
        "correct": sm_error < 0.2
    }
    
    # HBM generation
    scores["hbm_generation"] = {
        "silica": hbm.get("hbm_generation", "?"), 
        "actual": BLACKWELL_ACTUAL["hbm_generation"],
        "correct": hbm.get("hbm_generation") == BLACKWELL_ACTUAL["hbm_generation"]
    }
    
    # HBM bandwidth: within 20%
    bw = hbm.get("total_bandwidth_tbs", 0)
    bw_error = abs(bw - BLACKWELL_ACTUAL["hbm_bandwidth_tbs"]) / BLACKWELL_ACTUAL["hbm_bandwidth_tbs"]
    scores["hbm_bandwidth"] = {
        "silica": bw,
        "actual": BLACKWELL_ACTUAL["hbm_bandwidth_tbs"],
        "error_pct": round(bw_error * 100, 1),
        "correct": bw_error < 0.2
    }
    
    # L2 cache: within 25%
    l2_size = l2.get("total_size_mb", 0)
    l2_error = abs(l2_size - BLACKWELL_ACTUAL["l2_cache_mb"]) / BLACKWELL_ACTUAL["l2_cache_mb"]
    scores["l2_cache"] = {
        "silica": l2_size,
        "actual": BLACKWELL_ACTUAL["l2_cache_mb"],
        "error_pct": round(l2_error * 100, 1),
        "correct": l2_error < 0.25
    }
    
    # Chiplet decision
    chiplet = area.get("chiplet_required", False)
    scores["chiplet_decision"] = {
        "silica": chiplet,
        "actual": BLACKWELL_ACTUAL["chiplet_design"],
        "correct": chiplet == BLACKWELL_ACTUAL["chiplet_design"]
    }
    
    # NVLink generation
    nvlink_gen = nvlink.get("generation", "?")
    scores["nvlink_generation"] = {
        "silica": nvlink_gen,
        "actual": BLACKWELL_ACTUAL["nvlink_generation"],
        "correct": str(nvlink_gen) == str(BLACKWELL_ACTUAL["nvlink_generation"])
    }
    
    # FP8 support
    has_fp8 = any(f.get("format") == "FP8" and f.get("enabled") 
                  for f in func.get("compute_architecture", {}).get("precision_formats", []))
    scores["fp8_support"] = {
        "silica": has_fp8,
        "actual": BLACKWELL_ACTUAL["fp8_support"],
        "correct": has_fp8 == BLACKWELL_ACTUAL["fp8_support"]
    }
    
    # Overall score
    correct = sum(1 for s in scores.values() if s.get("correct"))
    total = len(scores)
    scores["overall"] = {
        "correct_decisions": correct,
        "total_decisions": total, 
        "score_pct": round(correct / total * 100, 1)
    }
    
    return scores

if __name__ == "__main__":
    import sys
    # Ensure UTF-8 output on Windows terminal
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
            
    print("=== SILICA PRODUCT ARCHITECT: BLACKWELL BENCHMARK ===")
    print("Inputs: 2022-era context (what NVIDIA architects had)")
    print("Goal: See how close Silica gets to actual Blackwell B200\n")
    
    orch = ProductArchitectOrchestrator()
    pipeline = orch.run(BLACKWELL_INPUTS, use_multipass=True)
    
    print("\n=== SCORING ===")
    scores = score_result(pipeline)
    
    for metric, data in scores.items():
        if metric == "overall":
            print(f"\n  OVERALL: {data['correct_decisions']}/{data['total_decisions']} correct ({data['score_pct']}%)")
        else:
            status = "[PASS]" if data.get("correct") else "[FAIL]"
            print(f"  {status} {metric}: silica={data.get('silica')}, actual={data.get('actual')} (error: {data.get('error_pct', 'N/A')}%)")
    
    print(f"\n  NVIDIA Level 2 target: >=70% correct")
    print(f"  Current level: {'ACHIEVED' if scores['overall']['score_pct'] >= 70 else 'IMPROVEMENT NEEDED'}")
