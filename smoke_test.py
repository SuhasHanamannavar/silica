#!/usr/bin/env python3
"""Smoke test: run the full multi-agent pipeline on (a) clean counter RTL and
(b) intentionally-broken RTL that must be recovered by the diagnosis agent.
Uses REAL EDA tools (Verilator + Yosys). No LLM required (deterministic fallback).
"""
import json, os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from silica_agents import Orchestrator

WORK = tempfile.mkdtemp(prefix="silica_smoke_")
print(f"[smoke] work dir: {WORK}")

CLEAN_RTL = """module counter #(parameter WIDTH=4) (
  input  wire             clk,
  input  wire             rst_n,
  input  wire             en,
  output reg  [WIDTH-1:0] count,
  output wire             overflow
);
  assign overflow = & count;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)    count <= {WIDTH{1'b0}};
    else if (en)   count <= count + 1'b1;
  end
endmodule
"""

BROKEN_RTL = """module counter #(parameter WIDTH=4) (
  input  wire             clk,
  input  wire             rst_n,
  input  wire             en,
  output reg  [WIDTH-1:0] count,
  output wire             overflow
);
  assign overflow = & cnt
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)    count <= {WIDTH{1'b0}};
    else if (en)   count <= count + 1'b1;
  end
endmodule
"""

def summarize(label, run):
    d = run.to_dict()
    print(f"\n=== {label} ===")
    print(f"  run_id: {d['id']}  status: {d['status']}  recovery_attempts: {d['recovery_attempts']}")
    for aid, st in d["stages"].items():
        print(f"  - {aid:28s} {st['status']:12s} attempts={st['attempts']}")
    if d.get("events"):
        for e in d["events"][-6:]:
            print(f"    event: {e.get('kind')} { {k:v for k,v in e.items() if k not in ('ts','kind')} }")
    return d

orch = Orchestrator(os.path.join(WORK, "projects"))

# --- Case 1: clean RTL, full pipeline ---
os.makedirs(os.path.join(WORK, "projects", "p_clean"), exist_ok=True)
r1 = orch.run_pipeline("p_clean", "4-bit up counter", rtl_override=CLEAN_RTL)
d1 = summarize("CASE 1: clean RTL", r1)
ok1 = d1["status"] in ("passed", "complete", "incomplete", "incomplete_awaiting_human_review") and \
      d1["stages"]["rtl_design"]["status"] == "passed" and \
      d1["stages"]["functional_verification"]["status"] == "passed" and \
      d1["stages"]["logic_synthesis"]["status"] == "passed" and \
      d1["stages"]["physical_design"]["status"] == "blocked"

# --- Case 2: broken RTL, must recover ---
os.makedirs(os.path.join(WORK, "projects", "p_broken"), exist_ok=True)
r2 = orch.run_pipeline("p_broken", "4-bit up counter (broken input)", rtl_override=BROKEN_RTL)
d2 = summarize("CASE 2: broken RTL (expect recovery)", r2)
ok2 = d2["recovery_attempts"] >= 1 and \
      d2["stages"]["rtl_design"]["status"] == "passed" and \
      d2["stages"]["functional_verification"]["status"] == "passed" and \
      d2["stages"]["logic_synthesis"]["status"] == "passed"

print("\n=== RESULT ===")
print(f"  case1 (clean):     {'PASS' if ok1 else 'FAIL'}")
print(f"  case2 (recovered): {'PASS' if ok2 else 'FAIL'}")
print(f"  artifacts dir: {WORK}")
sys.exit(0 if (ok1 and ok2) else 1)
