"""
Base class for all Silica specialist agents.

Enforces: tool-permission allowlist, confidence/escalation policy, audit
trail (model version, prompt version, retrieved refs, tool calls, inputs,
outputs, validation results), and deterministic contract validation before
a result is accepted.
"""
from __future__ import annotations
import time
from typing import Any, Dict, Optional

from .contracts import AgentResult, AGENT_REGISTRY, validate_output
from .prompts import AGENT_PROMPTS, PROMPT_VERSION
from .hf_serving import HFServingAdapter
from .sandbox import EDASandbox


class AgentError(Exception):
    pass


class EscalationRequired(AgentError):
    """Raised when an agent cannot proceed safely without human approval."""


class BaseAgent:
    agent_id: str = ""

    def __init__(self, hf: Optional[HFServingAdapter] = None,
                 sandbox: Optional[EDASandbox] = None,
                 config: Optional[Dict[str, Any]] = None):
        self.hf = hf or HFServingAdapter()
        self.sandbox = sandbox
        self.config = config or {}
        self.audit: Dict[str, Any] = {
            "agent_id": self.agent_id,
            "prompt_version": PROMPT_VERSION,
            "model": self.hf.model,
            "tool_calls": [],
            "llm_calls": [],
            "validation": None,
            "started_at": time.time(),
        }
        self.reg = AGENT_REGISTRY.get(self.agent_id, {})

    @property
    def system_prompt(self) -> str:
        return AGENT_PROMPTS.get(self.agent_id, "")

    def _allow_tool(self, tool: str) -> bool:
        allowed = self.reg.get("allowed_tools", [])
        return tool in allowed

    def _llm(self, user_prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """Call LLM; record in audit. Returns {text, fallback, model_call}."""
        if not self._allow_tool("llm"):
            return {"text": "", "fallback": True,
                    "model_call": {"status": "blocked", "error": "llm not in allowed_tools for this agent"}}
        res = self.hf.complete(self.system_prompt, user_prompt, max_tokens)
        self.audit["llm_calls"].append(res["model_call"].to_dict())
        return res

    def _tool(self, tool: str, argv, **kw) -> Dict[str, Any]:
        if not self._allow_tool(tool):
            raise AgentError(f"tool {tool} not permitted for agent {self.agent_id}")
        assert self.sandbox is not None, "sandbox required for tool execution"
        rec = self.sandbox.run(list(argv), **kw)
        rec["tool"] = tool
        self.audit["tool_calls"].append(rec)
        return rec

    def _validate(self, output: Dict[str, Any]) -> list:
        problems = validate_output(self.agent_id, output)
        self.audit["validation"] = {"problems": problems, "ok": not problems}
        return problems

    def _wrap(self, status: str, output: Dict[str, Any], confidence: float = 0.0,
              evidence=None, escalation: Optional[str] = None,
              warnings=None) -> AgentResult:
        self.audit["finished_at"] = time.time()
        self.audit["duration_s"] = round(self.audit["finished_at"] - self.audit["started_at"], 2)
        return AgentResult(
            agent=self.agent_id, status=status, output=output,
            evidence=evidence or [], confidence=confidence,
            escalation=escalation, audit=self.audit, warnings=warnings or [],
        )

    def run(self, inputs: Dict[str, Any]) -> AgentResult:
        raise NotImplementedError
