from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.index import _ORCH, _ORCH_OK, _ORCH_ERR, _RUNS_CACHE

class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, data: any):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif isinstance(data, str):
            self.wfile.write(data.encode("utf-8"))

    def do_OPTIONS(self):
        self._send(204, "")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body or b"{}")
        except Exception:
            payload = {}

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
            if _ORCH_OK and _ORCH:
                pipeline_result = _ORCH.run(inputs, use_multipass=use_multipass)
            else:
                from product_architect.orchestrator import ProductArchitectOrchestrator
                orch = ProductArchitectOrchestrator()
                pipeline_result = orch.run(inputs, use_multipass=use_multipass)
            pipeline_result["id"] = rid
            _RUNS_CACHE[rid] = pipeline_result
            return self._send(200, pipeline_result)
        except Exception as e:
            # Deterministic synthesis fallback so client never receives 500/502
            try:
                from product_architect.orchestrator import ProductArchitectOrchestrator
                orch = ProductArchitectOrchestrator()
                pipeline_result = orch.run(inputs, use_multipass=False)
                pipeline_result["id"] = rid
                _RUNS_CACHE[rid] = pipeline_result
                return self._send(200, pipeline_result)
            except Exception as e2:
                return self._send(500, {"error": f"Synthesis pipeline error: {str(e2)}"})
