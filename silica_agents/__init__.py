"""
SILICA specialist semiconductor engineering agents.

Each agent has a strictly bounded scope, a typed input/output contract,
domain-specific retrieval/prompting, limited tool access, an independent
validation layer, and a full audit trail. LLMs reason and generate code;
EDA tools provide authoritative verification; deterministic software
enforces policy. An LLM never certifies its own output without evidence.
"""
from .contracts import AgentResult, AGENT_REGISTRY, validate_output
from .base import BaseAgent, AgentError, EscalationRequired
from .hf_serving import HFServingAdapter, ModelCall
from .sandbox import EDASandbox, SandboxViolation
from .specialists import (
    SpecificationAgent, RTLDesignAgent, FunctionalVerificationAgent,
    LogicSynthesisAgent, FailureDiagnosisAgent, PhysicalDesignAgent,
    TimingVerificationAgent, SignoffReportAgent, build_agent,
)
from .orchestrator import Orchestrator, RunState, StageState, PIPELINE

__all__ = [
    "AgentResult", "AGENT_REGISTRY", "validate_output",
    "BaseAgent", "AgentError", "EscalationRequired",
    "HFServingAdapter", "ModelCall",
    "EDASandbox", "SandboxViolation",
    "SpecificationAgent", "RTLDesignAgent", "FunctionalVerificationAgent",
    "LogicSynthesisAgent", "FailureDiagnosisAgent", "PhysicalDesignAgent",
    "TimingVerificationAgent", "SignoffReportAgent", "build_agent",
    "Orchestrator", "RunState", "StageState", "PIPELINE",
]
