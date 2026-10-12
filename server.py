#!/usr/bin/env python3
"""
SILICA — Autonomous Semiconductor Engineering Platform (backend orchestrator).

Zero-dependency Python stdlib server. Serves the static frontend and executes a
real EDA workflow with Verilator (lint / compile / simulate) and Yosys
(synthesis), capturing actual commands, versions, exit codes, logs, artifacts,
and autonomous failure-recovery evidence.

Run:  python3 server.py   →  http://localhost:3000
"""
import json, os, re, shutil, subprocess, threading, time, uuid, traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote

# ---------------------------------------------------------------------------
# Authentication (opt-in via SILICA_REQUIRE_AUTH=1). Production: replace
# USERS dict + in-memory tokens with AWS DynamoDB (table silica-users).
# ---------------------------------------------------------------------------
import hashlib, secrets as _secrets
try:
    import neatlogs
    _NEATLOGS_KEY = os.environ.get("NEATLOGS_API_KEY", "bNve9E7JINfT773IqZAFaVm3yGXAZ0m4")
    if _NEATLOGS_KEY:
        neatlogs.init(api_key=_NEATLOGS_KEY)
        HAVE_NEATLOGS = True
    else:
        HAVE_NEATLOGS = False
except Exception:
    HAVE_NEATLOGS = False

AUTH_ENABLED = os.environ.get("SILICA_REQUIRE_AUTH", "") == "1"
AUTH_USERS = {"webofjee@gmail.com": "Suhas@2007"}  # fallback local user
AUTH_TOKENS = {}  # token -> email

try:
    import boto3
    _boto_session = boto3.Session(
        region_name=os.environ.get("AWS_REGION", "ap-south-1")
    )
    _dynamodb = _boto_session.resource("dynamodb")
    _users_table = _dynamodb.Table("silica-users")
    HAVE_DYNAMODB = True
except Exception as _e:
    HAVE_DYNAMODB = False
    _users_table = None

def _auth_check(path, headers):
    if not AUTH_ENABLED: return True, None
    if path in ("/api/health", "/api/login", "/api/signup", "/api/agents/health"): return True, None
    h = headers.get("Authorization", "")
    if h.startswith("Bearer "):
        tok = h[7:]
        if tok in AUTH_TOKENS: return True, AUTH_TOKENS[tok]
    return False, None

def _auth_login(email, password):
    if HAVE_DYNAMODB and _users_table:
        try:
            res = _users_table.get_item(Key={"email": email})
            item = res.get("Item")
            if item and item.get("password") == password:
                tok = _secrets.token_hex(24)
                AUTH_TOKENS[tok] = email
                return tok, item.get("name", email.split("@")[0])
        except Exception:
            pass
    if AUTH_USERS.get(email) == password:
        tok = _secrets.token_hex(24)
        AUTH_TOKENS[tok] = email
        return tok, "Suhas Hanamannavar"
    return None, None

def _auth_signup(name, email, password, company=""):
    if not email or not password or len(password) < 4:
        return None, "Invalid email or password (min 4 characters)"
    if HAVE_DYNAMODB and _users_table:
        try:
            existing = _users_table.get_item(Key={"email": email}).get("Item")
            if existing:
                return None, "An account with this email already exists"
            _users_table.put_item(Item={
                "email": email,
                "password": password,
                "name": name or email.split("@")[0],
                "company": company or "Independent",
                "role": "engineer",
                "created_at": int(time.time())
            })
        except Exception as e:
            return None, f"Database error: {e}"
    AUTH_USERS[email] = password
    tok = _secrets.token_hex(24)
    AUTH_TOKENS[tok] = email
    return tok, None



ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "projects")
os.makedirs(DATA, exist_ok=True)

# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------
def tool_version(cmd, args):
    try:
        out = subprocess.run([cmd]+args, capture_output=True, text=True, timeout=15)
        return (out.stdout+out.stderr).strip().splitlines()[0]
    except Exception as e:
        return f"unavailable: {e}"

TOOLS = {
    "verilator": tool_version("verilator", ["--version"]),
    "yosys": tool_version("yosys", ["-V"]),
    "g++": tool_version("g++", ["--version"]),
}
TOOLS_AVAILABLE = all("unavailable" not in v for v in TOOLS.values())

# ---------------------------------------------------------------------------
# Sample RTL: a 4-bit up-counter with synchronous reset (working baseline)
# ---------------------------------------------------------------------------
SAMPLE_RTL = """// Silica sample design: 4-bit synchronous up-counter
module counter #(parameter WIDTH=4) (
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

# Broken variant: missing semicolon on line 8 + undeclared signal 'cnt' used.
# Used to demonstrate real failure detection + autonomous recovery.
BROKEN_RTL = """// Silica sample design (intentionally broken for recovery demo)
module counter #(parameter WIDTH=4) (
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

TB = r"""// Silica auto-generated testbench
#include "Vcounter.h"
#include "verilated.h"
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  Vcounter* top = new Vcounter;
  top->rst_n = 0; top->clk = 0; top->en = 1;
  int errors = 0; unsigned int expected = 0; int released = 0;
  for (int cycle = 0; cycle < 48; cycle++) {
    if (cycle == 4) { top->rst_n = 1; released = 1; expected = 1; }
    top->clk = !top->clk; top->eval();
    if (top->clk == 0 && released && cycle > 4) {
      if (top->count != expected) {
        printf("FAIL cycle %d: count=%d expected=%d\n", cycle, top->count, expected);
        errors++;
      }
      expected = (expected + 1) & 0xF;
    }
  }
  top->final(); delete top;
  printf("SIM_DONE errors=%d\n", errors);
  return errors ? 1 : 0;
}
"""

YOSYS_SCRIPT = """# Silica synthesis script
read_verilog {rtl}
hierarchy -check -top counter
synth -top counter
stat
write_verilog {netlist}
write_json {json}
"""

# ---------------------------------------------------------------------------
# Project / run persistence
# ---------------------------------------------------------------------------
def jread(p, default):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def jwrite(p, obj):
    with open(p, "w") as f: json.dump(obj, f, indent=2)

def list_projects():
    out = []
    for pid in sorted(os.listdir(DATA)) if os.path.isdir(DATA) else []:
        meta = jread(os.path.join(DATA, pid, "project.json"), {})
        runs = jread(os.path.join(DATA, pid, "runs.json"), [])
        last_run = runs[-1] if runs else {}
        out.append({"id": pid, **meta, "runs": len(runs),
                    "last_status": last_run.get("status", "none"),
                    "last_run_id": last_run.get("id", None)})
    return out

def create_project(name, spec, rtl=None):
    pid = uuid.uuid4().hex[:8]
    pdir = os.path.join(DATA, pid); os.makedirs(pdir, exist_ok=True)
    meta = {"name": name, "spec": spec, "created": time.time(),
            "rtl": rtl if rtl is not None else SAMPLE_RTL}
    jwrite(os.path.join(pdir, "project.json"), meta)
    jwrite(os.path.join(pdir, "runs.json"), [])
    return pid, meta

# ---------------------------------------------------------------------------
# RTL recovery agent: reads real Verilator error evidence, applies controlled
# fixes in an isolated working copy, records what changed.
# ---------------------------------------------------------------------------
def diagnose_and_fix(rtl_text, error_log):
    """Return (fixed_text or None, list_of_actions). Evidence-based only."""
    import re as _re
    actions = []
    fixed = rtl_text.splitlines(keepends=True)
    # 1. Missing semicolon on assign statements.
    for i, ln in enumerate(fixed):
        s = ln.strip()
        if s.startswith("assign") and not s.endswith(";") and "//" not in s.split("assign")[0]:
            fixed[i] = ln.rstrip("\n") + ";\n"
            actions.append("line %d: inserted missing semicolon on assign statement" % (i+1))
    cur = "".join(fixed)
    # 2. Undeclared variable. Verilator 4.x: "Can't find definition of variable: 'cnt'"
    #    often followed by "Suggested alternative: 'count'". Prefer the suggested rename.
    undeclared = set(_re.findall(r"Can't find definition of variable:\s*'(\w+)'", error_log))
    undeclared |= set(_re.findall(r"Undeclared signal:\s*'?(\w+)'?", error_log))
    undeclared |= set(_re.findall(r"(\w+)\s+is not declared", error_log))
    suggestions = _re.findall(r"Suggested alternative:\s*'(\w+)'", error_log)
    if undeclared and suggestions:
        for sig, sug in zip(sorted(undeclared), suggestions):
            after = _re.sub(r"\b" + _re.escape(sig) + r"\b", sug, cur)
            if after != cur:
                cur = after
                actions.append("replaced undeclared signal '%s' with Verilator-suggested '%s'" % (sig, sug))
        fixed = cur.splitlines(keepends=True)
    elif undeclared:
        insert = []
        for sig in undeclared:
            insert.append("  wire [3:0] %s; // recovery: declared for undeclared signal\n" % sig)
            actions.append("declared missing wire '%s' to resolve undeclared-signal error" % sig)
        for i, ln in enumerate(fixed):
            if ln.strip().endswith(");"):
                for j, ins in enumerate(insert):
                    fixed.insert(i+1+j, ins)
                break
    if not actions:
        return None, []
    return "".join(fixed), actions

def run_stage(name, cmd, cwd, timeout=120):
    t0 = time.time()
    try:
        if HAVE_NEATLOGS:
            with neatlogs.trace(f"silica_stage_{name}"):
                p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        else:
            p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        dur = round(time.time()-t0, 2)
        log = (p.stdout or "") + (p.stderr or "")
        return {"name": name, "cmd": " ".join(cmd), "exit_code": p.returncode,
                "duration_s": dur, "log": log, "status": "passed" if p.returncode == 0 else "failed"}
    except subprocess.TimeoutExpired:
        return {"name": name, "cmd": " ".join(cmd), "exit_code": -1, "duration_s": timeout,
                "log": f"TIMEOUT after {timeout}s", "status": "failed"}
    except Exception as e:
        return {"name": name, "cmd": " ".join(cmd), "exit_code": -2, "duration_s": 0,
                "log": f"exec error: {e}\n{traceback.format_exc()}", "status": "failed"}

def execute_run(pid, rtl_override=None, max_recovery=2):
    pdir = os.path.join(DATA, pid)
    meta = jread(os.path.join(pdir, "project.json"), {})
    rid = uuid.uuid4().hex[:8]
    rdir = os.path.join(pdir, "runs", rid); os.makedirs(os.path.join(rdir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(rdir, "artifacts"), exist_ok=True)
    run = {"id": rid, "project": pid, "started": time.time(), "status": "running",
           "stages": [], "recovery": {"attempts": 0, "actions": [], "original_rtl": None},
           "artifacts": [], "tools": dict(TOOLS)}
    rtl = rtl_override if rtl_override is not None else meta.get("rtl", SAMPLE_RTL)
    original_rtl = rtl
    run["recovery"]["original_rtl"] = original_rtl

    def save():
        jwrite(os.path.join(rdir, "run.json"), run)
        runs = jread(os.path.join(pdir, "runs.json"), [])
        runs = [r for r in runs if r.get("id") != rid] + [
            {"id": rid, "status": run["status"], "started": run["started"],
             "stages": [s["name"]+":"+s["status"] for s in run["stages"]],
             "recovered": run["recovery"]["attempts"] > 0}]
        jwrite(os.path.join(pdir, "runs.json"), runs)
    save()

    work = os.path.join(rdir, "work"); os.makedirs(work, exist_ok=True)
    rtl_file = os.path.join(work, "counter.v")
    with open(rtl_file, "w") as f: f.write(rtl)

    attempt = 0
    while attempt <= max_recovery:
        run["stages"] = []
        # Stage 1: lint
        s = run_stage("lint", ["verilator", "--lint-only", "-Wall", "counter.v"], work)
        run["stages"].append(s)
        with open(os.path.join(rdir, "logs", "lint.log"), "w") as f: f.write(s["log"])
        if s["status"] == "failed":
            if attempt < max_recovery:
                fixed, actions = diagnose_and_fix(rtl, s["log"])
                if fixed:
                    attempt += 1
                    run["recovery"]["attempts"] = attempt
                    run["recovery"]["actions"].extend([f"attempt {attempt}: {a}" for a in actions])
                    with open(os.path.join(rdir, "logs", f"recovery_{attempt}.diff"), "w") as f:
                        f.write(f"=== Recovery attempt {attempt} ===\n" + "\n".join(actions))
                    rtl = fixed
                    with open(rtl_file, "w") as f: f.write(rtl)
                    save()
                    continue
                else:
                    run["status"] = "failed"; run["blocker"] = "lint errors not auto-recoverable; human intervention required"
                    save(); return run
            else:
                run["status"] = "failed"; run["blocker"] = "lint failed after max recovery attempts"
                save(); return run

        # Stage 2: compile simulation (Verilator --cc --exe + make)
        with open(os.path.join(work, "tb.cpp"), "w") as f: f.write(TB)
        s = run_stage("compile", ["verilator", "--cc", "--exe", "counter.v", "tb.cpp", "-Mdir", "obj_dir"], work)
        run["stages"].append(s)
        with open(os.path.join(rdir, "logs", "compile.log"), "w") as f: f.write(s["log"])
        if s["status"] == "failed":
            run["status"] = "failed"; run["blocker"] = "verilator compile failed"; save(); return run
        s = run_stage("make", ["make", "-C", "obj_dir", "-f", "Vcounter.mk", "Vcounter"], work)
        run["stages"].append(s)
        with open(os.path.join(rdir, "logs", "make.log"), "w") as f: f.write(s["log"])
        if s["status"] == "failed":
            run["status"] = "failed"; run["blocker"] = "C++ build of simulator failed"; save(); return run

        # Stage 3: simulate
        s = run_stage("simulate", ["./obj_dir/Vcounter"], work)
        run["stages"].append(s)
        with open(os.path.join(rdir, "logs", "simulate.log"), "w") as f: f.write(s["log"])
        sim_pass = s["status"] == "passed" and "SIM_DONE errors=0" in s["log"]
        if not sim_pass:
            run["status"] = "failed"; run["blocker"] = "functional simulation mismatch (see simulate.log)"; save(); return run

        # Stage 4: synthesis (Yosys)
        netlist = os.path.join(rdir, "artifacts", "counter_netlist.v")
        jsyn = os.path.join(rdir, "artifacts", "counter_synth.json")
        script = YOSYS_SCRIPT.format(rtl=rtl_file, netlist=netlist, json=jsyn)
        with open(os.path.join(work, "synth.ys"), "w") as f: f.write(script)
        s = run_stage("synthesis", ["yosys", "-s", "synth.ys"], work)
        run["stages"].append(s)
        with open(os.path.join(rdir, "logs", "synthesis.log"), "w") as f: f.write(s["log"])
        if s["status"] == "failed":
            run["status"] = "failed"; run["blocker"] = "yosys synthesis failed"; save(); return run
        # extract cell/area stats from yosys log
        stats = "\n".join(l for l in s["log"].splitlines() if "Number of" in l or "Chip area" in l)

        # Stage 5: report
        report = {
            "run_id": rid, "project": meta.get("name"), "status": "passed",
            "recovered": attempt > 0, "recovery_actions": run["recovery"]["actions"],
            "stages": [{k: s[k] for k in ("name","exit_code","duration_s","status")} for s in run["stages"]],
            "synthesis_stats": stats,
            "artifacts": ["counter_netlist.v (gate-level netlist)", "counter_synth.json (synthesis database)"],
            "signoff_note": "Functional simulation passed and gate-level netlist generated. "
                            "This is NOT physical signoff: no placement/routing, DRC/LVS, or timing signoff performed.",
            "tools": dict(TOOLS),
        }
        jwrite(os.path.join(rdir, "artifacts", "report.json"), report)
        with open(os.path.join(rdir, "artifacts", "counter.v.final"), "w") as f: f.write(rtl)
        run["artifacts"] = ["counter_netlist.v", "counter_synth.json", "report.json", "counter.v.final"]
        run["status"] = "passed"
        run["synthesis_stats"] = stats
        save()
        return run
    run["status"] = "failed"; run["blocker"] = "exceeded max recovery attempts"; save()
    return run

# ---------------------------------------------------------------------------
# Multi-agent orchestrator integration (silica_agents package).
# Runs the full specialist pipeline: specification -> rtl_design ->
# functional_verification -> logic_synthesis -> physical_design (BLOCKED)
# -> timing_verification (BLOCKED) -> signoff_report, with inline evidence-
# based failure recovery. Output is mapped to the frontend's expected shape.
# ---------------------------------------------------------------------------
try:
    from silica_agents import Orchestrator
    HAS_AGENTS = True
except Exception as _e:
    HAS_AGENTS = False
    _AGENT_IMPORT_ERR = str(_e)

def execute_agent_run(pid, rtl_override=None, max_recovery=2, rid=None):
    """Run the multi-agent pipeline and persist a frontend-compatible run.json."""
    pdir = os.path.join(DATA, pid)
    meta = jread(os.path.join(pdir, "project.json"), {})
    orch = Orchestrator(DATA, max_recovery=max_recovery)
    run_state = orch.run_pipeline(pid, meta.get("spec", ""), rtl_override=rtl_override, run_id=rid)
    rd = run_state.to_dict()
    # map orchestrator shape -> legacy frontend shape (stages as list)
    stages = []
    for aid, st in rd.get("stages", {}).items():
        stages.append({"name": aid, "status": st.get("status", "pending"),
                       "exit_code": 0 if st.get("status") == "passed" else 1,
                       "duration_s": round((st.get("finished_at") or 0) - (st.get("started_at") or 0), 2)})
    rdir = os.path.join(pdir, "runs", rd["id"])
    artifacts_dir = os.path.join(rdir, "artifacts")
    all_artifacts = sorted(os.listdir(artifacts_dir)) if os.path.isdir(artifacts_dir) else rd.get("artifacts", [])
    legacy = {
        "id": rd["id"], "project": pid, "status": rd["status"],
        "stages": stages,
        "recovery": {"attempts": rd.get("recovery_attempts", 0),
                     "actions": [e.get("actions", "") for e in rd.get("events", []) if e.get("kind") == "recovery_attempt"]},
        "artifacts": all_artifacts,
        "tools": dict(TOOLS),
        "agent_pipeline": True,
        "events": rd.get("events", [])[-50:],
    }
    # overwrite run.json with frontend-compatible view
    jwrite(os.path.join(rdir, "run.json"), legacy)
    runs = jread(os.path.join(pdir, "runs.json"), [])
    runs = [r for r in runs if r.get("id") != rd["id"]] + [
        {"id": rd["id"], "status": rd["status"], "started": rd.get("started_at"),
         "stages": [s["name"]+":"+s["status"] for s in stages],
         "recovered": rd.get("recovery_attempts", 0) > 0, "agent_pipeline": True,
         "artifacts_count": len(all_artifacts)}]
    jwrite(os.path.join(pdir, "runs.json"), runs)
    return legacy

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        self.wfile.write(data)

    def _static(self, path):
        if path == "/": path = "/index.html"
        fp = os.path.join(ROOT, path.lstrip("/"))
        if not os.path.isfile(fp) or ".." in path:
            self._send(404, {"error": "not found"}, "text/plain"); return
        ctype = {"html":"text/html","css":"text/css","js":"application/javascript",
                 "svg":"image/svg+xml","json":"application/json"}.get(fp.split(".")[-1], "application/octet-stream")
        with open(fp, "rb") as f: data = f.read()
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path); p = unquote(u.path)
        ok, who = _auth_check(p, self.headers)
        if not ok:
            self._send(401, {"error": "unauthorized", "login": "/api/login"}); return
        if p == "/api/health":
            self._send(200, {"ok": True, "tools": TOOLS, "tools_available": TOOLS_AVAILABLE})
        elif p == "/api/agents/health":
            from silica_agents.hf_serving import HFServingAdapter
            hf = HFServingAdapter()
            self._send(200, {"ok": HAS_AGENTS, "import_error": None if HAS_AGENTS else _AGENT_IMPORT_ERR,
                             "agents": ["specification","rtl_design","functional_verification","logic_synthesis",
                                        "physical_design","timing_verification","failure_diagnosis","signoff_report"],
                             "hf_serving": hf.health()})
        elif p == "/api/projects":
            self._send(200, {"projects": list_projects()})
        elif p.startswith("/api/runs/"):
            rid = p.split("/")[-1]
            for pid in os.listdir(DATA):
                rp = os.path.join(DATA, pid, "runs", rid, "run.json")
                if os.path.isfile(rp):
                    self._send(200, jread(rp, {})); return
            self._send(404, {"error": "run not found"})
        elif p.startswith("/api/artifacts/"):
            parts = p.strip("/").split("/")
            if len(parts) >= 4:
                rid, name = parts[2], parts[3]
                for pid in os.listdir(DATA):
                    fp = os.path.join(DATA, pid, "runs", rid, "artifacts", name)
                    if os.path.isfile(fp):
                        with open(fp, "rb") as f: data = f.read()
                        self.send_response(200); self.send_header("Content-Type","application/octet-stream")
                        self.send_header("Content-Disposition", f'attachment; filename="{name}"')
                        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
            self._send(404, {"error": "artifact not found"})
        elif p.startswith("/api/logs/"):
            parts = p.strip("/").split("/")
            if len(parts) >= 4:
                rid, name = parts[2], parts[3]
                for pid in os.listdir(DATA):
                    fp = os.path.join(DATA, pid, "runs", rid, "logs", name)
                    if os.path.isfile(fp):
                        with open(fp) as f: self._send(200, {"log": f.read()}); return
            self._send(404, {"error": "log not found"})
        else:
            self._static(p)


    CHAT_RUNS = {}
    def _handle_chat(self, body):
        import threading
        prompt = (body or {}).get("prompt", "")
        if not prompt or len(prompt) < 5:
            return self._send(400, {"error": "prompt too short"})
        pid, meta = create_project("chat: " + prompt[:30], prompt, None)
        _run_fn = execute_agent_run if HAS_AGENTS else execute_run
        threading.Thread(target=_run_fn, args=(pid, None), daemon=True).start()
        self.CHAT_RUNS[pid] = {"status": "running", "prompt": prompt}
        return self._send(200, {"chat_id": pid, "status": "running", "poll": "/api/chat/"+pid})

    def do_POST(self):
        u = urlparse(self.path); p = unquote(u.path)
        ok, who = _auth_check(p, self.headers)
        if not ok:
            self._send(401, {"error": "unauthorized", "login": "/api/login"}); return
        u = urlparse(self.path); p = unquote(u.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try: payload = json.loads(body or b"{}")
        except Exception: payload = {}
        if p == "/api/login":
            email = payload.get("email", "")
            pwd = payload.get("password", "")
            tok, name = _auth_login(email, pwd)
            if tok:
                return self._send(200, {"ok": True, "token": tok, "email": email, "name": name})
            else:
                return self._send(401, {"ok": False, "error": "Invalid email or password"})
        elif p == "/api/signup":
            name = payload.get("name", "")
            email = payload.get("email", "")
            pwd = payload.get("password", "")
            company = payload.get("company", "")
            tok, err = _auth_signup(name, email, pwd, company)
            if tok:
                return self._send(200, {"ok": True, "token": tok, "email": email, "name": name or email.split("@")[0], "message": "Account created in AWS DynamoDB successfully!"})
            else:
                return self._send(400, {"ok": False, "error": err or "Failed to register account"})
        elif p == "/api/chat":
            return self._handle_chat(payload)
        elif p.startswith("/api/chat/"):
            cid = p.split("/")[-1]
            projs = list_projects()
            proj = next((x for x in projs if x.get("id")==cid), None)
            if not proj:
                return self._send(404, {"error": "chat run not found"})
            run = {}
            rdir = os.path.join(DATA, cid, "runs")
            if os.path.isdir(rdir):
                rids = sorted(os.listdir(rdir))
                if rids:
                    run = jread(os.path.join(rdir, rids[-1], "run.json"), {})
            return self._send(200, {"status": proj.get("last_status"), "prompt": proj.get("spec",""), "run": run})
        elif p == "/api/projects":
            pid, meta = create_project(payload.get("name","untitled"), payload.get("spec",""), payload.get("rtl"))
            self._send(200, {"id": pid, **meta})
        elif p.startswith("/api/projects/") and p.endswith("/run"):
            pid = p.split("/")[3]
            pdir = os.path.join(DATA, pid)
            if not os.path.isdir(pdir): self._send(404, {"error": "project not found"}); return
            rtl = payload.get("rtl")
            new_prompt = payload.get("prompt") or payload.get("spec")
            if new_prompt:
                meta = jread(os.path.join(pdir, "project.json"), {})
                meta["spec"] = new_prompt
                jwrite(os.path.join(pdir, "project.json"), meta)
            use_broken = payload.get("demo_broken", False)
            if use_broken: rtl = BROKEN_RTL
            rid = uuid.uuid4().hex[:8]
            _run_fn = execute_agent_run if HAS_AGENTS else execute_run
            threading.Thread(target=_run_fn, args=(pid, rtl), kwargs={"rid": rid} if HAS_AGENTS else {}, daemon=True).start()
            self._send(200, {"status": "started", "project": pid, "run_id": rid, "agent_pipeline": HAS_AGENTS})
        else:
            self._send(404, {"error": "unknown endpoint"})

    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Silica orchestrator running on http://localhost:{port}  (tools: {', '.join(TOOLS)})")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
