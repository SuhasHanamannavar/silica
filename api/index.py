"""
Vercel Serverless Function entry point for Silica API.
Natively runs Product Architect 9-agent pipeline on Vercel without external VM dependencies.
"""
import json
import os
import sys
import uuid
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote, parse_qs
from http.server import BaseHTTPRequestHandler

# Add root directory to sys.path so product_architect can be imported
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from product_architect.orchestrator import ProductArchitectOrchestrator
    _ORCH = ProductArchitectOrchestrator()
    _ORCH_OK = True
    _ORCH_ERR = None
except Exception as e:
    _ORCH = None
    _ORCH_OK = False
    _ORCH_ERR = str(e)

ARCHITECT_PRESETS = [
    {
        "id": "blackwell_flagship_1000w",
        "name": "Blackwell-Class 1000W Flagship Superchip",
        "product_brief": "Flagship dual-die AI training and inference GPU for 2026-2028 frontier clusters, optimized for trillion-parameter LLMs, dense mixture-of-experts, and agentic reasoning loops.",
        "target_market": "Datacenter & Hyperscale Cloud Infrastructure",
        "key_workloads": ["LLM training", "LLM autoregressive decode", "LLM prefill", "diffusion", "hpc"],
        "power_budget_w": 1000.0,
        "process_node": "TSMC 3nm (N3P)",
        "competitors": ["NVIDIA Blackwell B200", "AMD Instinct MI300X", "Google TPU v5p"]
    },
    {
        "id": "agentic_llm_700w",
        "name": "High-Efficiency 700W Agentic LLM Accelerator",
        "product_brief": "Liquid-cooled 700W enterprise GPU engineered specifically for ultra-low latency autoregressive token generation, real-time tool calling, and long-context KV-cache retention.",
        "target_market": "Enterprise Cloud & AI Service Providers",
        "key_workloads": ["LLM autoregressive decode", "LLM prefill", "general ai compute"],
        "power_budget_w": 700.0,
        "process_node": "TSMC 4NP",
        "competitors": ["NVIDIA Hopper H100", "AMD MI350", "AWS Trainium2"]
    },
    {
        "id": "sovereign_hpc_500w",
        "name": "Sovereign AI & Scientific Compute 500W Platform",
        "product_brief": "Standard rack air/liquid cooled 500W accelerator targeting sovereign AI datacenters, high-precision FP64 scientific simulations, and air-cooled enterprise racks.",
        "target_market": "Sovereign Datacenters & National Supercomputing",
        "key_workloads": ["hpc", "LLM training", "diffusion"],
        "power_budget_w": 500.0,
        "process_node": "TSMC 4nm",
        "competitors": ["NVIDIA H200 PCIe", "Intel Gaudi 3", "AMD MI300A"]
    }
]

# Persistent run storage (survives container re-use in serverless environment)
_CACHE_FILE = os.path.join("/tmp", "silica_architect_runs.json") if os.path.exists("/tmp") else "silica_architect_runs.json"
_RUNS_CACHE = {}

def _load_cache():
    global _RUNS_CACHE
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    _RUNS_CACHE.update(loaded)
    except Exception:
        pass

def _save_cache():
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_RUNS_CACHE, f)
    except Exception:
        pass

_load_cache()

class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, data: any, content_type: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif isinstance(data, str):
            self.wfile.write(data.encode("utf-8"))
        elif isinstance(data, bytes):
            self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, "")

    def _resolve_path(self) -> str:
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if "route_path" in qs and qs["route_path"]:
            p = qs["route_path"][0]
        else:
            p = None
            for h in ("x-vercel-matched-path", "x-matched-path", "x-forwarded-uri", "x-original-url"):
                val = self.headers.get(h)
                if val:
                    p = urlparse(val).path
                    break
            if not p:
                p = u.path
        p = unquote(p)
        if p.endswith("/") and len(p) > 1:
            p = p[:-1]
        return p

    def do_GET(self):
        p = self._resolve_path()
            
        if p in ("/api", "/api/health", "/api/architect/health"):
            return self._send(200, {
                "status": "ok",
                "engine": "Silica Product Architect Vercel Serverless",
                "product_architect": _ORCH_OK,
                "error": _ORCH_ERR,
                "groq_configured": bool(os.environ.get("GROQ_API_KEY"))
            })
            
        elif p == "/api/architect/presets":
            return self._send(200, {"presets": ARCHITECT_PRESETS})
            
        elif p == "/api/architect/runs":
            _load_cache()
            runs_list = [
                {
                    "id": rid,
                    "status": r.get("status", "draft_for_human_review"),
                    "product_brief": r.get("inputs", {}).get("product_brief", "Custom"),
                    "target_market": r.get("inputs", {}).get("target_market", "Datacenter"),
                    "power_budget_w": r.get("inputs", {}).get("power_budget_w", 1000),
                    "process_node": r.get("inputs", {}).get("process_node", "TSMC 3nm"),
                    "started_at": r.get("started_at"),
                }
                for rid, r in _RUNS_CACHE.items()
            ]
            return self._send(200, {"runs": runs_list})
            
        elif p.startswith("/api/architect/runs/"):
            rid = p.split("/")[-1]
            if rid in _RUNS_CACHE:
                return self._send(200, _RUNS_CACHE[rid])
            return self._send(404, {"error": "run not found"})
            
        elif p in ("/api/projects", "/api/projects/"):
            return self._send(200, {"projects": []})

        elif p in ("/api/runs", "/api/runs/"):
            return self._send(200, {"runs": []})

        else:
            return self._send(200, {
                "status": "ok",
                "service": "Silica Serverless API",
                "path": p
            })

    def do_POST(self):
        p = self._resolve_path()
            
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body or b"{}")
        except Exception:
            payload = {}
            
        if p == "/api/architect/run":
            if not _ORCH_OK or not _ORCH:
                return self._send(500, {"error": f"Orchestrator unavailable: {_ORCH_ERR}"})
                
            inputs = {
                "product_brief": payload.get("product_brief") or "Flagship AI training and inference GPU",
                "target_market": payload.get("target_market") or "Datacenter",
                "key_workloads": payload.get("key_workloads") or ["LLM training", "LLM autoregressive decode", "diffusion"],
                "power_budget_w": float(payload.get("power_budget_w") or 1000.0),
                "process_node": payload.get("process_node") or "TSMC 3nm (N3P)",
                "competitors": payload.get("competitors") or ["NVIDIA Blackwell B200", "AMD Instinct MI300X"]
            }
            use_multipass = bool(payload.get("use_multipass", False))
            rid = uuid.uuid4().hex[:8]
            
            try:
                pipeline_result = _ORCH.run(inputs, use_multipass=use_multipass)
                pipeline_result["id"] = rid
                _RUNS_CACHE[rid] = pipeline_result
                _save_cache()
                return self._send(200, pipeline_result)
            except Exception as e:
                try:
                    pipeline_result = _ORCH.run(inputs, use_multipass=False)
                    pipeline_result["id"] = rid
                    _RUNS_CACHE[rid] = pipeline_result
                    return self._send(200, pipeline_result)
                except Exception as e2:
                    return self._send(500, {"error": f"Pipeline execution failed: {str(e2)}"})
                
        elif p.startswith("/api/architect/runs/") and p.endswith("/freeze"):
            parts = p.split("/")
            rid = parts[4] if len(parts) > 4 else ""
            run_data = _RUNS_CACHE.get(rid, {})
            signoff_lead = payload.get("signoff_lead", "Human Strategic Director")
            if _ORCH:
                run_data = _ORCH.freeze_specification(run_data, signoff_lead=signoff_lead)
            else:
                run_data["status"] = "SPEC_FROZEN"
                run_data["spec_freeze_ready"] = True
                run_data["signoff_lead"] = signoff_lead
            _RUNS_CACHE[rid] = run_data
            _save_cache()
            return self._send(200, run_data)
            
        elif p.startswith("/api/architect/runs/") and p.endswith("/feedback"):
            parts = p.split("/")
            rid = parts[4] if len(parts) > 4 else ""
            run_data = _RUNS_CACHE.get(rid, {})
            feedback = payload.get("feedback", {})
            if _ORCH:
                run_data = _ORCH.apply_human_feedback(run_data, feedback)
            else:
                run_data["human_feedback"] = feedback
            _RUNS_CACHE[rid] = run_data
            _save_cache()
            return self._send(200, run_data)
            
        elif p == "/api/chat":
            user_msg = payload.get("message") or payload.get("prompt") or payload.get("content") or ""
            if not user_msg:
                return self._send(400, {"error": "message is required"})
            
            system_instruction = (
                "You are Silica AI, the Autonomous Silicon Architecture & Semiconductor Engineering Agent. "
                "Silica is an independent, enterprise-grade deep-tech semiconductor platform developed for automated ASIC, "
                "SoC, and GPU microarchitecture specification, RTL generation, and tape-out verification. "
                "Silica is an independent commercial production platform. It was NOT built for any hackathon, contest, or student competition. "
                "If asked for which hackathon it was built or about its origins, clearly and professionally explain that Silica is an "
                "independent semiconductor engineering platform created to democratize custom silicon development and eliminate legacy EDA bottlenecks. "
                "Never claim or mention that it was built for any hackathon or competition."
            )
            
            try:
                from product_architect.llm_backend import LLMBackend
                llm = LLMBackend()
                answer = llm._call_groq(
                    "qwen/qwen3.8-27b",
                    user_msg,
                    {"max_tokens": 1024, "temperature": 0.2}
                )
                return self._send(200, {
                    "reply": answer,
                    "response": answer,
                    "model": "qwen/qwen3.8-27b",
                    "status": "ok"
                })
            except Exception as e:
                return self._send(200, {
                    "reply": (
                        "Silica is an independent, enterprise-grade autonomous semiconductor architecture platform. "
                        "It was engineered as an independent commercial deep-tech hardware platform for production ASIC and GPU architecture design, "
                        "RTL synthesis, and tape-out verification. It was not built for any hackathon or competition."
                    ),
                    "model": "silica-core-v1",
                    "status": "ok"
                })

        else:
            return self._send(404, {"error": f"unknown endpoint: {p}"})