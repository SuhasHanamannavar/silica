import json
import os
import time
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

class LLMBackend:
    """
    Multi-model serving backend with:
    - HF Inference API primary path
    - Local vLLM deployment path (for production)
    - Deterministic fallback (no LLM, no hallucination)
    - Per-task model routing
    - Structured output enforcement
    - Audit logging
    """
    
    MODEL_ROUTING = {
        "functional_spec": {
            "primary": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "fallback": "Qwen/Qwen2.5-Coder-14B-Instruct",
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        "tradeoff_analysis": {
            "primary": "meta-llama/Llama-3.1-70B-Instruct",
            "fallback": "mistralai/Mixtral-8x22B-Instruct-v0.1",
            "max_tokens": 8192,
            "temperature": 0.2,
        },
        "nfr_spec": {
            "primary": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "fallback": "Qwen/Qwen2.5-Coder-14B-Instruct",
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        "risk_assessment": {
            "primary": "meta-llama/Llama-3.1-70B-Instruct",
            "fallback": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "max_tokens": 4096,
            "temperature": 0.2,
        },
        "document_assembly": {
            "primary": "Qwen/Qwen2.5-Coder-14B-Instruct",
            "fallback": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
            "max_tokens": 8192,
            "temperature": 0.0,
        },
        "critique": {
            "primary": "meta-llama/Llama-3.1-70B-Instruct",
            "fallback": "mistralai/Mixtral-8x22B-Instruct-v0.1",
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "fast_calculation": {
            "primary": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
            "fallback": "deterministic",
            "max_tokens": 1024,
            "temperature": 0.0,
        },
    }
    
    def __init__(self, hf_token: str = None, use_local: bool = False, 
                 local_endpoint: str = "http://localhost:8000/v1"):
        self.hf_token = hf_token or os.environ.get("HF_TOKEN", "")
        self.use_local = use_local
        self.local_endpoint = local_endpoint
        self.allow_external = os.environ.get("SILICA_ALLOW_EXTERNAL_LLM", "0") == "1"
        self.audit_log: List[Dict[str, Any]] = []
    
    def call(self, task_type: str, prompt: str, 
             enforce_json: bool = True,
             max_retries: int = 2) -> Dict[str, Any]:
        """
        Call LLM for a specific task type with automatic routing and fallback.
        Returns: {text, model, latency_s, source, structured_output?, error?}
        """
        t0 = time.time()
        config = self.MODEL_ROUTING.get(task_type, self.MODEL_ROUTING["fast_calculation"])
        
        if enforce_json:
            prompt = self._wrap_for_json_output(prompt)
        
        models_to_try = [config["primary"], config["fallback"]]
        last_error = None
        
        for model in models_to_try:
            if model == "deterministic":
                result = self._deterministic_fallback(task_type, prompt)
                self._log_audit(task_type, model, time.time()-t0, "deterministic_fallback")
                return result
            
            try:
                if self.use_local:
                    text = self._call_local(model, prompt, config)
                elif self.allow_external and self.hf_token:
                    text = self._call_hf_api(model, prompt, config)
                else:
                    result = self._deterministic_fallback(task_type, prompt)
                    self._log_audit(task_type, "silica-deterministic-v1", 
                                   time.time()-t0, "deterministic_fallback")
                    return result
                
                output = {
                    "text": text,
                    "model": model,
                    "latency_s": round(time.time() - t0, 2),
                    "source": "local_vllm" if self.use_local else "hf_inference_api",
                }
                
                if enforce_json:
                    structured = self._extract_json(text)
                    if structured:
                        output["structured_output"] = structured
                    else:
                        last_error = "JSON extraction failed"
                        continue
                
                self._log_audit(task_type, model, time.time()-t0, "success")
                return output
                
            except Exception as e:
                last_error = str(e)
                continue
        
        # All models failed — use deterministic fallback
        result = self._deterministic_fallback(task_type, prompt)
        result["error"] = last_error
        result["fallback_reason"] = last_error
        self._log_audit(task_type, "silica-deterministic-v1", 
                       time.time()-t0, f"fallback_due_to: {last_error}")
        return result
    
    def _call_hf_api(self, model: str, prompt: str, config: Dict) -> str:
        url = f"https://api-inference.huggingface.co/models/{model}"
        data = json.dumps({
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": config["max_tokens"],
                "temperature": config["temperature"],
                "return_full_text": False,
                "do_sample": config["temperature"] > 0,
            }
        }).encode()
        
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json"
            }
        )
        
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode())
        
        if isinstance(resp, list):
            return resp[0].get("generated_text", "")
        return resp.get("generated_text", "")
    
    def _call_local(self, model: str, prompt: str, config: Dict) -> str:
        """Call local vLLM/Text Generation Inference endpoint."""
        url = f"{self.local_endpoint}/completions"
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
        }).encode()
        
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode())
        
        return resp.get("choices", [{}])[0].get("text", "")
    
    def _wrap_for_json_output(self, prompt: str) -> str:
        """Add JSON output enforcement to the prompt."""
        return prompt + """

IMPORTANT OUTPUT FORMAT:
Your ENTIRE response must be a single valid JSON object. No markdown, no explanation, no code fences.
The JSON must be parseable by Python's json.loads().
If you need to include text with quotes, escape them properly as \".
Start your response with '{' and end with '}'.
"""
    
    def _extract_json(self, text: str) -> Optional[Any]:
        """Extract and parse JSON from model output."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass
        
        start_obj = text.find('{')
        end_obj = text.rfind('}')
        if start_obj >= 0 and end_obj > start_obj:
            try:
                return json.loads(text[start_obj:end_obj+1])
            except Exception:
                pass

        start_arr = text.find('[')
        end_arr = text.rfind(']')
        if start_arr >= 0 and end_arr > start_arr:
            try:
                return json.loads(text[start_arr:end_arr+1])
            except Exception:
                pass
        
        return None
    
    def _deterministic_fallback(self, task_type: str, prompt: str) -> Dict[str, Any]:
        """Template-based deterministic output — no LLM, no hallucination."""
        try:
            from product_architect.product_architect_templates import get_deterministic_template
        except ImportError:
            from product_architect_templates import get_deterministic_template
            
        template = get_deterministic_template(task_type, prompt)
        return {
            "text": json.dumps(template) if isinstance(template, (dict, list)) else str(template),
            "structured_output": template if isinstance(template, (dict, list)) else None,
            "model": "silica-deterministic-v1",
            "latency_s": 0.001,
            "source": "deterministic_fallback",
        }
    
    def _log_audit(self, task_type: str, model: str, latency: float, status: str):
        self.audit_log.append({
            "task_type": task_type,
            "model": model,
            "latency_s": round(latency, 4),
            "status": status,
            "timestamp": time.time(),
        })
