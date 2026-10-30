"""
Silica specialist engineering agents.

Each agent has: a defined scope, a structured input/output contract, limited tool
access, a deterministic validation layer, and an audit trail. LLMs (via the HF
Inference API adapter) are used only for reasoning/generation; authoritative
correctness is always established by real EDA tools (Verilator/Yosys) and
deterministic checks. An agent never certifies its own output.
"""
import json, os, re, subprocess, tempfile, time, traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Model-serving adapter (Hugging Face Inference API + deterministic fallback)
# ---------------------------------------------------------------------------
HF_MODEL = os.environ.get("SILICA_HF_MODEL", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

def call_model(prompt: str, timeout: int = 60) -> Dict[str, Any]:
    """Call HF Inference API if HF_TOKEN is set; otherwise deterministic fallback.
    Returns {text, model, latency_s, source, error?}."""
    t0 = time.time()
    if HF_TOKEN:
        try:
            import urllib.request
            url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
            data = json.dumps({"inputs": prompt, "parameters": {"max_new_tokens": 1024, "temperature": 0.2}}).encode()
            req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode())
            text = resp[0]["generated_text"] if isinstance(resp, list) else resp.get("generated_text", "")
            return {"text": text, "model": HF_MODEL, "latency_s": round(time.time()-t0,2), "source": "hf_inference_api"}
        except Exception as e:
            return {"text": "", "model": HF_MODEL, "latency_s": round(time.time()-t0,2), "source": "hf_inference_api", "error": str(e)}
    # Deterministic fallback: template-based RTL generation (no LLM, no hallucination)
    return {"text": _deterministic_rtl(prompt), "model": "silica-deterministic-v1", "latency_s": round(time.time()-t0,4), "source": "deterministic_fallback"}

def _deterministic_rtl(prompt: str) -> str:
    """Template generator for supported small circuits. Returns Verilog or ''."""
    p = prompt.lower()
    if "fsm" in p or "state machine" in p:
        return '''module fsm(input clk, input rst_n, input in, output reg out);
  reg [1:0] state; localparam S0=0,S1=1,S2=2;
  always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin state<=S0; out<=0; end
    else case(state)
      S0: begin out<=0; if(in) state<=S1; end
      S1: begin out<=1; if(in) state<=S2; else state<=S0; end
      S2: begin out<=0; state<=in?S2:S0; end
    endcase
  end
endmodule
'''
    if "fifo" in p:
        return '''module fifo #(parameter WIDTH=8, DEPTH=4)(input clk, input rst_n, input wr, input rd, input [WIDTH-1:0] din, output reg [WIDTH-1:0] dout, output full, output empty);
  reg [WIDTH-1:0] mem [0:DEPTH-1]; reg [$clog2(DEPTH):0] cnt; reg [$clog2(DEPTH)-1:0] wp,rp;
  assign full = (cnt==DEPTH); assign empty = (cnt==0);
  always @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin cnt<=0; wp<=0; rp<=0; end
    else begin
      if(wr && !full) begin mem[wp]<=din; wp<=wp+1; cnt<=cnt+1; end
      if(rd && !empty) begin dout<=mem[rp]; rp<=rp+1; cnt<=cnt-1; end
    end
  end
endmodule
'''
    # default: 4-bit up-counter (baseline)
    return '''module counter #(parameter WIDTH=4)(input clk, input rst_n, input en, output reg [WIDTH-1:0] count, output wire overflow);
  assign overflow = & count;
  always @(posedge clk or negedge rst_n) begin
    if(!rst_n) count <= 0; else if(en) count <= count + 1'b1;
  end
endmodule
'''

def extract_verilog(text: str) -> Optional[str]:
    """Extract the first module...endmodule block from model output."""
    m = re.search(r"(module\s+\w+.*?endmodule)", text, re.S | re.I)
    return m.group(1) if m else None

# ---------------------------------------------------------------------------
# Agent base: contract + audit trail + deterministic validation
# ---------------------------------------------------------------------------
@dataclass
class AuditEntry:
    agent: str; action: str; detail: str; ts: float = field(default_factory=time.time)

class Agent:
    name = "base"; role = "base agent"
    def __init__(self):
        self.audit: List[AuditEntry] = []
        self.model_used = None
    def log(self, action, detail=""):
        self.audit.append(AuditEntry(self.name, action, detail))
    def validate(self, output: Dict) -> Dict:
        """Deterministic validation layer. Subclasses override. Returns {ok, errors:[]}."""
        return {"ok": True, "errors": []}
    def run(self, inp: Dict) -> Dict:
        raise NotImplementedError

# ---------------------------------------------------------------------------
# Agent 2: RTL Design — generates synthesizable Verilog, validates with lint
# ---------------------------------------------------------------------------
class RTLDesignAgent(Agent):
    name = "rtl_design"; role = "RTL design and debugging"
    PROMPT = """You are a senior silicon RTL design engineer at Silica, an independent enterprise semiconductor engineering platform. Generate synthesizable Verilog-2001 for the following specification. Use only one module, synchronous design, active-low async reset, no $display in synthesis code. Output ONLY the Verilog code, no prose.\n\nSpec: %s\n\nVerilog:"""
    def run(self, inp: Dict) -> Dict:
        spec = inp.get("spec", "a 4-bit up-counter")
        self.log("spec_received", spec[:120])
        resp = call_model(self.PROMPT % spec)
        self.model_used = resp.get("model"); self.log("model_call", f"{resp.get('source')} {resp.get('latency_s')}s")
        rtl = extract_verilog(resp.get("text","")) or resp.get("text","").strip()
        self.log("rtl_generated", f"{len(rtl)} chars")
        # deterministic validation: must contain module/endmodule, no obvious latches
        v = self.validate_rtl(rtl)
        self.log("validation", json.dumps(v))
        return {"rtl": rtl, "model": self.model_used, "source": resp.get("source"), "validation": v, "audit": [asdict(a) for a in self.audit]}
    def validate_rtl(self, rtl: str) -> Dict:
        errs = []
        if not re.search(r"\bmodule\b", rtl, re.I): errs.append("no module declaration")
        if not re.search(r"\bendmodule\b", rtl, re.I): errs.append("no endmodule")
        if re.search(r"\balways\s+@\(\*\)", rtl) and "always @(posedge" not in rtl.replace("@(*)", ""):
            errs.append("combinational always block may infer latches (review)")
        return {"ok": len(errs)==0, "errors": errs}

# ---------------------------------------------------------------------------
# Agent 3: Functional Verification — testbench + Verilator simulation
# ---------------------------------------------------------------------------
class VerificationAgent(Agent):
    name = "functional_verif"; role = "functional verification"
    def run(self, inp: Dict) -> Dict:
        rtl = inp["rtl"]; work = inp["workdir"]
        top = inp.get("top", "counter")
        self.log("rtl_received", f"{len(rtl)} chars, top={top}")
        rtl_file = os.path.join(work, "design.v")
        with open(rtl_file,"w") as f: f.write(rtl)
        # lint
        lint = self._run(["verilator","--lint-only","-Wall","design.v"], work)
        self.log("lint", f"exit={lint['exit_code']}")
        if lint["exit_code"] != 0:
            return {"stage":"verification", "substage":"lint", "status":"failed", "log": lint["log"], "audit":[asdict(a) for a in self.audit]}
        # build + simulate (counter-style testbench; generic clock/reset driver)
        tb = self._gen_tb(top)
        with open(os.path.join(work,"tb.cpp"),"w") as f: f.write(tb)
        cc = self._run(["verilator","--cc","--exe","design.v","tb.cpp","-Mdir","obj_dir","--top-module",top], work)
        self.log("compile", f"exit={cc['exit_code']}")
        if cc["exit_code"]!=0: return {"stage":"verification","substage":"compile","status":"failed","log":cc["log"],"audit":[asdict(a) for a in self.audit]}
        mk = self._run(["make","-C","obj_dir","-f",f"V{top}.mk",f"V{top}"], work)
        self.log("make", f"exit={mk['exit_code']}")
        if mk["exit_code"]!=0: return {"stage":"verification","substage":"make","status":"failed","log":mk["log"],"audit":[asdict(a) for a in self.audit]}
        sim = self._run([f"./obj_dir/V{top}"], work)
        passed = sim["exit_code"]==0 and "SIM_DONE errors=0" in sim["log"]
        self.log("simulate", f"exit={sim['exit_code']} passed={passed}")
        return {"stage":"verification","substage":"simulate","status":"passed" if passed else "failed","log":sim["log"],"passed":passed,"audit":[asdict(a) for a in self.audit]}
    def _gen_tb(self, top):
        return f'''#include "V{top}.h"
#include "verilated.h"
int main(int argc,char**argv){{
  Verilated::commandArgs(argc,argv);
  V{top}* top=new V{top};
  top->rst_n=0; top->clk=0; top->en=1; int errs=0; unsigned exp=0; int rel=0;
  for(int c=0;c<48;c++){{
    if(c==4){{top->rst_n=1;rel=1;exp=1;}}
    top->clk=!top->clk; top->eval();
    if(top->clk==0 && rel && c>4){{
      if(top->count != exp){{ printf("FAIL c=%d got=%d exp=%d\\n",c,top->count,exp); errs++; }}
      exp=(exp+1)&0xF;
    }}
  }}
  top->final(); delete top;
  printf("SIM_DONE errors=%d\\n", errs); return errs?1:0;
}}'''
    def _run(self, cmd, cwd):
        try:
            p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
            return {"exit_code": p.returncode, "log": (p.stdout or "")+(p.stderr or "")}
        except Exception as e:
            return {"exit_code": -1, "log": str(e)}

# ---------------------------------------------------------------------------
# Agent 4: Logic Synthesis — Yosys + real statistics
# ---------------------------------------------------------------------------
class SynthesisAgent(Agent):
    name="logic_synthesis"; role="synthesis and physical implementation"
    def run(self, inp: Dict) -> Dict:
        rtl=inp["rtl"]; work=inp["workdir"]; top=inp.get("top","counter")
        rtl_file=os.path.join(work,"design.v")
        with open(rtl_file,"w") as f: f.write(rtl)
        netlist=os.path.join(work,"netlist.v"); jsyn=os.path.join(work,"synth.json")
        script=f"read_verilog design.v\nhierarchy -check -top {top}\nsynth -top {top}\nstat\nwrite_verilog {netlist}\nwrite_json {jsyn}\n"
        with open(os.path.join(work,"synth.ys"),"w") as f: f.write(script)
        r=self._run(["yosys","-s","synth.ys"], work)
        self.log("yosys", f"exit={r['exit_code']}")
        stats="\n".join(l for l in r["log"].splitlines() if "Number of" in l or "Chip area" in l)
        ok = r["exit_code"]==0 and os.path.isfile(netlist)
        return {"stage":"synthesis","status":"passed" if ok else "failed","log":r["log"],"stats":stats,
                "netlist": netlist if ok else None, "audit":[asdict(a) for a in self.audit]}
    def _run(self, cmd, cwd):
        try:
            p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=120)
            return {"exit_code":p.returncode,"log":(p.stdout or "")+(p.stderr or "")}
        except Exception as e: return {"exit_code":-1,"log":str(e)}

# ---------------------------------------------------------------------------
# Agent 7: Failure Diagnosis and Recovery (evidence-based, isolated retries)
# ---------------------------------------------------------------------------
class RecoveryAgent(Agent):
    name="failure_recovery"; role="failure diagnosis and recovery"
    def run(self, inp: Dict) -> Dict:
        rtl=inp["rtl"]; error_log=inp["error_log"]; max_attempts=inp.get("max_attempts",2)
        self.log("failure_captured", error_log[:200])
        fixed, actions = self.diagnose_and_fix(rtl, error_log)
        if fixed is None:
            self.log("escalate", "no safe automated correction; human intervention required")
            return {"recovered": False, "actions": [], "fixed_rtl": None, "disposition":"escalated_to_human", "audit":[asdict(a) for a in self.audit]}
        self.log("fix_applied", "; ".join(actions))
        return {"recovered": True, "actions": actions, "fixed_rtl": fixed, "disposition":"recovered", "audit":[asdict(a) for a in self.audit]}
    def diagnose_and_fix(self, rtl, error_log):
        actions=[]; lines=rtl.splitlines(keepends=True)
        # missing semicolon on assign lines (evidence: syntax error near line)
        for i,ln in enumerate(lines):
            s=ln.strip()
            if s.startswith("assign") and not s.endswith(";") and "//" not in s.split("assign")[0]:
                lines[i]=ln.rstrip("\n")+";\n"; actions.append(f"line {i+1}: inserted missing semicolon")
        cur="".join(lines)
        # undeclared variable with Verilator suggestion
        und=set(re.findall(r"Can't find definition of variable:\s*'(\w+)'", error_log))
        und|=set(re.findall(r"Undeclared signal:\s*'?(\w+)'?", error_log))
        sug=re.findall(r"Suggested alternative:\s*'(\w+)'", error_log)
        if und and sug:
            for sig,sg in zip(sorted(und), sug):
                after=re.sub(r"\b"+re.escape(sig)+r"\b", sg, cur)
                if after!=cur: cur=after; actions.append(f"renamed undeclared '{sig}' to Verilator-suggested '{sg}'")
        elif und:
            ins=[f"  wire [3:0] {s}; // recovery: declared for undeclared signal\n" for s in und]
            for a in ins: actions.append("declared missing wire")
            ls=cur.splitlines(keepends=True)
            for i,ln in enumerate(ls):
                if ln.strip().endswith(");"):
                    for j,x in enumerate(ins): ls.insert(i+1+j, x)
                    break
            cur="".join(ls)
        if not actions: return None, []
        return cur, actions

# ---------------------------------------------------------------------------
# Agent 8: Signoff and Engineering Report (aggregates evidence, never infers)
# ---------------------------------------------------------------------------
class ReportAgent(Agent):
    name="signoff_report"; role="signoff and engineering report"
    def run(self, inp: Dict) -> Dict:
        stages=inp.get("stages",[]); recovered=inp.get("recovered",0)
        passed=all(s.get("status")=="passed" for s in stages)
        missing=[]
        if not any(s.get("stage")=="verification" for s in stages): missing.append("functional verification")
        if not any(s.get("stage")=="synthesis" for s in stages): missing.append("logic synthesis")
        missing += ["floorplanning","placement","routing","timing signoff (STA)","DRC/LVS","GDSII streamout"]
        disposition = "passed_verification_and_synthesis" if passed and not missing[:2] else "incomplete"
        if missing: disposition += " — blocked/missing: " + ", ".join(missing)
        report = {"disposition": disposition, "stages": stages, "recovered_attempts": recovered,
                  "missing_signoff_checks": missing,
                  "signoff_note": "NOT fabrication-ready. Physical design, timing signoff, DRC/LVS, and GDSII were not performed.",
                  "audit_summary": f"{sum(len(s.get('audit',[])) for s in stages)} audit entries across agents"}
        self.log("report_generated", disposition)
        return {"report": report, "audit":[asdict(a) for a in self.audit]}
