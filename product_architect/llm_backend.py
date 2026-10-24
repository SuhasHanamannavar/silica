"""
Zero-cost LLM backend: Groq primary (with multi-model routing), CPU-based/deterministic fallback.
"""
import json
import os
import re
import time
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

class LLMBackend:
    """
    LLM Backend for Silica Product Architect:
    - Primary: Groq API with task-based model routing
    - Fallback: Deterministic templates (100% reliable, zero hallucination)
    - Structured output extraction and audit logging
    """
    
    @staticmethod
    def _get_api_key() -> str:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            # Check local .env file
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GROQ_API_KEY="):
                                key = line.split("=", 1)[1].strip().strip("'\"")
                                os.environ["GROQ_API_KEY"] = key
                                break
                except Exception:
                    pass
        return key
    
    MODEL_ROUTING = {
        "functional_spec": {
            "provider": "groq",
            "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "openai/gpt-oss-20b"],
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        "tradeoff_analysis": {
            "provider": "groq",
            "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "openai/gpt-oss-20b"],
            "max_tokens": 8192,
            "temperature": 0.2,
        },
        "nfr_spec": {
            "provider": "groq",
            "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "openai/gpt-oss-20b"],
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        "risk_assessment": {
            "provider": "groq",
            "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "openai/gpt-oss-20b"],
            "max_tokens": 4096,
            "temperature": 0.2,
        },
        "critique": {
            "provider": "groq",
            "models": ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "openai/gpt-oss-20b"],
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "interface_spec": {
            "provider": "groq",
            "models": ["openai/gpt-oss-20b", "llama-3.1-8b-instant", "openai/gpt-oss-120b"],
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        "document_assembly": {
            "provider": "groq",
            "models": ["openai/gpt-oss-20b", "llama-3.1-8b-instant", "openai/gpt-oss-120b"],
            "max_tokens": 8192,
            "temperature": 0.0,
        },
        "interpretation": {
            "provider": "groq",
            "models": ["openai/gpt-oss-20b", "llama-3.1-8b-instant"],
            "max_tokens": 2048,
            "temperature": 0.2,
        },
        "fast_calculation": {
            "provider": "groq",
            "models": ["openai/gpt-oss-20b", "llama-3.1-8b-instant"],
            "max_tokens": 1024,
            "temperature": 0.0,
        }
    }
    
    def __init__(self, groq_key: Optional[str] = None):
        self.groq_key = groq_key or self._get_api_key()
        self.audit_log: List[Dict[str, Any]] = []
    
    def call(self, task_type: str, prompt: str, enforce_json: bool = True) -> Dict[str, Any]:
        t0 = time.time()
        config = self.MODEL_ROUTING.get(task_type, self.MODEL_ROUTING["interpretation"])
        
        if enforce_json:
            prompt = prompt + "\n\nIMPORTANT: Output ONLY valid JSON. No markdown fences, no explanation. Start with '{' or '['."
        
        last_error = None
        
        if self.groq_key and config.get("provider") == "groq":
            candidate_models = config.get("models", ["openai/gpt-oss-120b", "openai/gpt-oss-20b"])
            for model_name in candidate_models:
                try:
                    text = self._call_groq(model_name, prompt, config)
                    latency = round(time.time() - t0, 3)
                    output: Dict[str, Any] = {
                        "text": text,
                        "model": model_name,
                        "provider": "groq",
                        "latency_s": latency,
                        "source": "groq_api"
                    }
                    if enforce_json:
                        structured = self._extract_json(text)
                        if structured is not None:
                            output["structured_output"] = structured
                        else:
                            output["json_extraction_failed"] = True
                            output["raw_text_sample"] = text[:500]
                    self._log(task_type, f"groq/{model_name}", latency, "success")
                    return output
                except Exception as e:
                    last_error = str(e)
                    continue
        
        # Fallback to deterministic template
        from product_architect.templates import get_deterministic_template
        fallback_res = get_deterministic_template(task_type, prompt)
        fallback_latency = round(time.time() - t0, 4)
        if isinstance(fallback_res, dict) and "structured_output" in fallback_res:
            res_dict = fallback_res
        else:
            res_dict = {
                "text": json.dumps(fallback_res) if isinstance(fallback_res, (dict, list)) else str(fallback_res),
                "structured_output": fallback_res,
                "model": "silica-deterministic-v1",
                "provider": "deterministic",
                "latency_s": fallback_latency,
                "source": "deterministic_fallback"
            }
        if last_error:
            res_dict["fallback_reason"] = last_error
        self._log(task_type, "deterministic_fallback", fallback_latency, f"fallback: {str(last_error)[:100]}")
        return res_dict
    
    def _deterministic_fallback(self, task_type: str, prompt: str = "") -> Dict[str, Any]:
        """Direct deterministic fallback helper."""
        from product_architect.templates import get_deterministic_template
        tmpl = get_deterministic_template(task_type, prompt)
        return {
            "text": json.dumps(tmpl) if isinstance(tmpl, (dict, list)) else str(tmpl),
            "structured_output": tmpl,
            "model": "silica-deterministic-v1",
            "provider": "deterministic",
            "latency_s": 0.001,
            "source": "deterministic_fallback"
        }
    
    def _call_groq(self, model: str, prompt: str, config: Dict) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.get("max_tokens", 4096),
            "temperature": config.get("temperature", 0.1),
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Silica/1.0"
            }
        )
        
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
            res_json = json.loads(body)
            return res_json["choices"][0]["message"]["content"]
    
    def _extract_json(self, text: str) -> Optional[Any]:
        """Robust JSON extraction from model output."""
        text = text.strip()
        # Direct
        try:
            return json.loads(text)
        except Exception:
            pass
        
        # Code fences
        m = re.search(r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        
        # Object scan
        start_obj = text.find('{')
        end_obj = text.rfind('}')
        if start_obj >= 0 and end_obj > start_obj:
            try:
                return json.loads(text[start_obj:end_obj+1])
            except Exception:
                pass
                
        # Array scan
        start_arr = text.find('[')
        end_arr = text.rfind(']')
        if start_arr >= 0 and end_arr > start_arr:
            try:
                return json.loads(text[start_arr:end_arr+1])
            except Exception:
                pass
                
        return None
    
    def _log(self, task: str, model: str, latency: float, status: str):
        self.audit_log.append({
            "task": task,
            "model": model,
            "latency_s": latency,
            "status": status,
            "ts": time.time()
        })
