#!/usr/bin/env python3
"""
Silica specialist-agent benchmark & regression suite (Phase 6).
Every case executes REAL EDA tools (Verilator + Yosys). No simulated results.
Cases: known-answer (clean counter), failure-recovery (broken RTL), parameter
variation (WIDTH=8), invalid-input rejection, and blocked-stage honesty.
Run:  python3 eval/benchmark.py   (exit 0 = all pass)
"""
import json, os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from silica_agents import Orchestrator

WORK = tempfile.mkdtemp(prefix="silica_bench_")
ORCH = Orchestrator(os.path.join(WORK, "projects"))

def counter_rtl(width=4, broken=False):
    sig = "cnt" if broken else "count"
    semi = "" if broken else ";"
    return f"""module counter #(parameter WIDTH={width}) (
  input  wire             clk,
  input  wire             rst_n,
  input  wire             en,
  output reg  [WIDTH-1:0] count,
  output wire             overflow
);
  assign overflow = & {sig}{semi}
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n)    count <= {{WIDTH{{1'b0}}}};
    else if (en)   count <= count + 1'b1;
  end
endmodule
"""

def run_case(name, rtl, pid):
    os.makedirs(os.path.join(WORK, "projects", pid), exist_ok=True)
    r = ORCH.run_pipeline(pid, name, rtl_override=rtl).to_dict()
    return r

results = []

# Case 1: clean 4-bit counter — full vertical slice must pass
r = run_case("clean counter w4", counter_rtl(4), "c1")
ok = (r["stages"]["rtl_design"]["status"] == "passed" and
      r["stages"]["functional_verification"]["status"] == "passed" and
      r["stages"]["logic_synthesis"]["status"] == "passed")
results.append(("clean_counter_w4", ok, r["status"]))

# Case 2: broken RTL — must recover within bounded retries and pass
r = run_case("broken counter (recover)", counter_rtl(4, broken=True), "c2")
ok = (r["recovery_attempts"] >= 1 and
      r["stages"]["rtl_design"]["status"] == "passed" and
      r["stages"]["functional_verification"]["status"] == "passed" and
      r["stages"]["logic_synthesis"]["status"] == "passed")
results.append(("broken_counter_recovered", ok, f"recovery={r['recovery_attempts']}"))

# Case 3: WIDTH=8 parameterized — must pass (regression on width)
r = run_case("clean counter w8", counter_rtl(8), "c3")
ok = (r["stages"]["functional_verification"]["status"] == "passed" and
      r["stages"]["logic_synthesis"]["status"] == "passed")
results.append(("clean_counter_w8", ok, r["status"]))

# Case 4: invalid empty RTL — must NOT pass (no false positive)
r = run_case("invalid empty rtl", "// empty, no module", "c4")
ok = r["stages"]["rtl_design"]["status"] in ("failed", "blocked")
results.append(("invalid_rtl_rejected", ok, r["stages"]["rtl_design"]["status"]))

# Case 5: physical & timing stages must be honestly BLOCKED, never passed
r = run_case("blocked honesty", counter_rtl(4), "c5")
ok = (r["stages"]["physical_design"]["status"] == "blocked" and
      r["stages"]["timing_verification"]["status"] in ("blocked", "pending"))
results.append(("physical_timing_blocked_honest", ok,
                f"phys={r['stages']['physical_design']['status']} timing={r['stages']['timing_verification']['status']}"))

# Case 6: signoff must NOT claim complete when physical/timing blocked
r = run_case("signoff honesty", counter_rtl(4), "c6")
ok = r["status"] != "passed" and "incomplete" in r["status"]
results.append(("signoff_not_falsely_complete", ok, r["status"]))

print("=" * 60)
print(f"{'CASE':38s} {'RESULT':6s} DETAIL")
print("=" * 60)
allpass = True
for name, ok, detail in results:
    print(f"{name:38s} {'PASS' if ok else 'FAIL':6s} {detail}")
    allpass = allpass and ok
print("=" * 60)
print(f"OVERALL: {'ALL PASS' if allpass else 'FAILURES PRESENT'}  (workdir: {WORK})")
sys.exit(0 if allpass else 1)
