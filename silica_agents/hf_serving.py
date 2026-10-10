"""
Hugging Face model-serving adapter.

Design goals (per Phase 4.4):
- Model and revision configurable via environment / config (no hardcode).
- Timeouts, retries with exponential backoff, rate-limit awareness.
- Structured response parsing (extract JSON from model output).
- Error handling + health checks.
- Usage, latency, and cost tracking.
- Fallback: when no HF_TOKEN / no network / model unavailable, degrade to
  a deterministic rule-based mode and RECORD that the fallback was used.
  Never silently pretend an LLM ran.
- Secrets in env var HF_TOKEN; never logged, never sent to frontend.
- Privacy: proprietary RTL is never sent to external inference unless
  SILICA_ALLOW_EXTERNAL_LLM=1 is explicitly set.

Uses HF Inference API (serverless) via stdlib urllib so it works in
Vercel serverless functions without extra pip dependencies.
"""
from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
HF_API_URL = "https://api-inference.huggingface.co/models/{model}"


class ModelCall:
    """Record of one model invocation (audit + usage tracking)."""
    def __init__(self, model: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                 latency_s: float = 0.0, status: str = "ok", error: Optional[str] = None,
                 fallback_used: bool = False):
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_s = round(latency_s, 3)
        self.status = status
        self.error = error
        self.fallback_used = fallback_used
        self.ts = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class HFServingAdapter:
    def __init__(self, model: Optional[str] = None, token: Optional[str] = None,
                 timeout_s: int = 60, max_retries: int = 3):
        self.model = model or os.environ.get("SILICA_LLM_MODEL", DEFAULT_MODEL)
        self.token = token or os.environ.get("HF_TOKEN", "")
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.external_allowed = os.environ.get("SILICA_ALLOW_EXTERNAL_LLM", "0") == "1"
        self.call_log: List[ModelCall] = []

    # -- privacy guard -----------------------------------------------------
    def _check_privacy(self, payload: str) -> Optional[str]:
        """Return error string if external call is not permitted."""
        if not self.external_allowed:
            return ("external LLM call prohibited by privacy policy; set "
                    "SILICA_ALLOW_EXTERNAL_LLM=1 to allow sending design data to "
                    "Hugging Face Inference API. Using deterministic fallback.")
        if not self.token:
            return "HF_TOKEN not set; cannot call HF Inference API. Using fallback."
        return None

    def health(self) -> Dict[str, Any]:
        return {
            "adapter": "hf-inference-api",
            "model": self.model,
            "token_configured": bool(self.token),
            "external_llm_allowed": self.external_allowed,
            "calls_recorded": len(self.call_log),
        }

    # -- core call ---------------------------------------------------------
    def complete(self, system_prompt: str, user_prompt: str,
                 max_new_tokens: int = 1024) -> Dict[str, Any]:
        """Return {text, model_call}. Never raises; records fallback on failure."""
        privacy_err = self._check_privacy(system_prompt + user_prompt)
        if privacy_err:
            mc = ModelCall(self.model, status="blocked_privacy", error=privacy_err, fallback_used=True)
            self.call_log.append(mc)
            return {"text": "", "model_call": mc, "fallback": True}

        url = HF_API_URL.format(model=self.model)
        body = json.dumps({
            "inputs": f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n",
            "parameters": {"max_new_tokens": max_new_tokens, "temperature": 0.2, "return_full_text": False},
        }).encode()
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

        t0 = time.time()
        last_err = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    raw = resp.read().decode()
                data = json.loads(raw)
                text = data[0]["generated_text"] if isinstance(data, list) else data.get("generated_text", "")
                mc = ModelCall(self.model, latency_s=time.time() - t0, status="ok")
                self.call_log.append(mc)
                return {"text": text, "model_call": mc, "fallback": False}
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}: {e.read().decode()[:200]}"
                if e.code in (429, 503):  # rate limit / overloaded
                    time.sleep(2 ** attempt)
                    continue
                break
            except Exception as e:  # network / timeout
                last_err = str(e)[:200]
                time.sleep(1 ** attempt)
                continue
        mc = ModelCall(self.model, latency_s=time.time() - t0, status="failed",
                       error=last_err, fallback_used=True)
        self.call_log.append(mc)
        return {"text": "", "model_call": mc, "fallback": True}

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Robustly extract the first JSON object from model text."""
        if not text:
            return None
        # try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # find first { ... last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                return None
        return None
