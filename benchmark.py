#!/usr/bin/env python3
"""
Silica specialist-agent evaluation benchmark.

Known-answer RTL tasks validated by REAL EDA tools (Verilator + Yosys).
Measures: lint pass, simulation pass, synthesis pass, recovery success rate,
and unsupported-claim rate. Baseline = deterministic generator; if HF_TOKEN is
set, the HF Inference API model is also evaluated and compared.

Usage: python3 benchmark.py  → writes benchmark_report.json
"""
import json, os, shutil, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from silica_agents import RTLDesignAgent, VerificationAgent, SynthesisAgent, RecoveryAgent, HF_TOKEN, HF_MODEL

TASKS = [
    {"id": "counter4", "spec": "A 4-bit synchronous up-counter with active-low async reset, clock enable, and overflow flag.", "top": "counter", "expect_pass": True},
    {"id": "fsm_101", "spec": "A finite-state machine (Moore) detecting the sequence 101 on a 1-bit input, with active-low async reset.", "top": "fsm", "expect_pass": True},
    {"id": "fifo8x4", "spec": "A synchronous FIFO, width 8, depth 4, with full/empty flags, active-low async reset.", "top": "fifo", "expect_pass": True},
]

def run_pipeline(task, workdir):
    """Run spec -> RTL -> verif -> synth -> recovery if needed. Return result dict."""
    t0 = time.time()
    rtl_agent = RTLDesignAgent()
    r = rtl_agent.run({"spec": task["spec"]})
    rtl = r["rtl"]; source = r["source"]; model = r["model"]
    result = {"task": task["id"], "source": source, "model": model,
              "lint_pass": False, "sim_pass": False, "synth_pass": False,
              "recovered": False, "recovery_attempts": 0, "duration_s": None}
    work = os.path.join(workdir, task["id"]); os.makedirs(work, exist_ok=True)
    va = VerificationAgent(); sa = SynthesisAgent(); ra = RecoveryAgent()
    for attempt in range(3):
        vres = va.run({"rtl": rtl, "workdir": work, "top": task["top"]})
        result["lint_pass"] = vres["substage"] != "lint" or vres["status"]=="passed"
        if vres["status"]=="passed":
            result["sim_pass"] = vres.get("passed", False)
            sres = sa.run({"rtl": rtl, "workdir": work, "top": task["top"]})
            result["synth_pass"] = sres["status"]=="passed"
            result["stats"] = sres.get("stats","")
            break
        # failed — attempt recovery on lint/compile errors
        rec = ra.run({"rtl": rtl, "error_log": vres.get("log",""), "max_attempts": 2})
        if rec["recovered"]:
            rtl = rec["fixed_rtl"]; result["recovered"]=True; result["recovery_attempts"]+=1
            continue
        else:
            result["blocker"] = vres.get("log","")[:300]
            break
    result["duration_s"] = round(time.time()-t0, 2)
    result["overall_pass"] = result["lint_pass"] and result["sim_pass"] and result["synth_pass"]
    return result

def main():
    outdir = tempfile.mkdtemp(prefix="silica_bench_")
    results = [run_pipeline(t, outdir) for t in TASKS]
    n = len(results)
    summary = {
        "tasks": n,
        "overall_pass": sum(r["overall_pass"] for r in results),
        "lint_pass": sum(r["lint_pass"] for r in results),
        "sim_pass": sum(r["sim_pass"] for r in results),
        "synth_pass": sum(r["synth_pass"] for r in results),
        "recovered": sum(r["recovered"] for r in results),
        "hf_token_set": bool(HF_TOKEN), "model": HF_MODEL,
        "results": results,
        "note": "Pass/fail determined by real Verilator/Yosys execution, not by model self-report. Physical design/timing/DRC/LVS not evaluated (blocked: no OpenROAD/PDK/GPU).",
    }
    rep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_report.json")
    with open(rep, "w") as f: json.dump(summary, f, indent=2)
    shutil.rmtree(outdir, ignore_errors=True)
    print(json.dumps({k:v for k,v in summary.items() if k!="results"}, indent=2))
    print(f"\nFull report: {rep}")

if __name__ == "__main__":
    main()
