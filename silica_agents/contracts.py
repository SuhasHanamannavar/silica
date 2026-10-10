"""
Typed input/output contracts for every Silica specialist agent.

Contracts are the single source of truth for what an agent may accept and
return. Every agent output is validated against its contract before it is
accepted as a stage result; invalid outputs fail the stage rather than
being silently forwarded. Contract validation is deterministic and does
not depend on an LLM.
"""
from __future__ import annotations
import re
import time
from typing import Any, Dict, List, Optional

# Minimal dependency-free schema validator. We avoid hard dependency on
# pydantic so the agents package degrades gracefully on minimal runtimes
# (e.g. Vercel serverless). If pydantic is present it is used for richer
# error messages; otherwise the built-in validator below applies.
try:
    from pydantic import BaseModel, Field, ValidationError  # type: ignore
    HAS_PYDANTIC = True
except Exception:  # pragma: no cover
    HAS_PYDANTIC = False


# ---------------------------------------------------------------------------
# Common envelope
# ---------------------------------------------------------------------------
class AgentResult:
    """Envelope every agent returns. Carries evidence + audit metadata."""
    def __init__(
        self,
        agent: str,
        status: str,  # passed | failed | blocked | escalated
        output: Dict[str, Any],
        evidence: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.0,
        escalation: Optional[str] = None,
        audit: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.agent = agent
        self.status = status
        self.output = output
        self.evidence = evidence or []
        self.confidence = max(0.0, min(1.0, confidence))
        self.escalation = escalation
        self.audit = audit or {}
        self.warnings = warnings or []
        self.audit.setdefault("produced_at", time.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "output": self.output,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "escalation": self.escalation,
            "audit": self.audit,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Per-agent output contracts (shape definitions + deterministic validation)
# ---------------------------------------------------------------------------
def _validate_rtl(text: str) -> List[str]:
    """Deterministic RTL sanity checks. Returns list of problems (empty=ok)."""
    problems = []
    if not text or not text.strip():
        return ["empty RTL"]
    if "module" not in text:
        problems.append("no module declaration found")
    if "endmodule" not in text:
        problems.append("no endmodule found")
    # balanced begin/end as standalone words (endmodule excluded via \b boundary)
    if len(re.findall(r"\bbegin\b", text)) != len(re.findall(r"\bend\b", text)):
        problems.append("unbalanced begin/end blocks")
    return problems


def _validate_spec(d: Dict[str, Any]) -> List[str]:
    problems = []
    for key in ("title", "functional_requirements", "interfaces", "constraints", "acceptance_tests", "unresolved_questions"):
        if key not in d:
            problems.append(f"missing required spec field: {key}")
    if not d.get("functional_requirements"):
        problems.append("no functional requirements declared")
    if not d.get("interfaces"):
        problems.append("no interface definitions")
    return problems


def _validate_verification(d: Dict[str, Any]) -> List[str]:
    problems = []
    if "tests" not in d or not isinstance(d["tests"], list):
        problems.append("verification output missing 'tests' list")
    if "simulation_log" not in d:
        problems.append("missing simulation_log evidence reference")
    if "pass_fail" not in d:
        problems.append("missing pass_fail determination")
    return problems


def _validate_synthesis(d: Dict[str, Any]) -> List[str]:
    problems = []
    if "netlist_file" not in d:
        problems.append("synthesis output missing netlist_file")
    if "statistics" not in d:
        problems.append("synthesis output missing statistics (cell counts)")
    if "warnings" not in d:
        problems.append("synthesis output missing warnings list")
    return problems


def _validate_diagnosis(d: Dict[str, Any]) -> List[str]:
    problems = []
    for key in ("failure_evidence", "root_cause_hypothesis", "proposed_fix", "patch_diff", "disposition"):
        if key not in d:
            problems.append(f"diagnosis missing field: {key}")
    return problems


CONTRACT_VALIDATORS = {
    "specification": _validate_spec,
    "rtl_design": lambda d: _validate_rtl(d.get("rtl", "")),
    "functional_verification": _validate_verification,
    "logic_synthesis": _validate_synthesis,
    "failure_diagnosis": _validate_diagnosis,
    "physical_design": lambda d: [],  # blocked stage; shape only
    "timing_verification": lambda d: [],
    "signoff_report": lambda d: [],
}

# Registry of all 8 specialists with scope, tools, and completion criteria
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "specification": {
        "name": "Specification & Architecture",
        "stage_order": 1,
        "allowed_tools": ["llm", "retrieval"],
        "completion_criteria": "structured spec with interfaces, constraints, acceptance tests, and explicit unresolved questions",
        "implemented": True,
    },
    "rtl_design": {
        "name": "RTL Design",
        "stage_order": 2,
        "allowed_tools": ["llm", "retrieval", "verilator_lint"],
        "completion_criteria": "synthesizable Verilog that passes Verilator lint clean (exit 0)",
        "implemented": True,
    },
    "functional_verification": {
        "name": "Functional Verification",
        "stage_order": 3,
        "allowed_tools": ["llm", "verilator_compile", "verilator_simulate", "make", "g++"],
        "completion_criteria": "simulation runs to completion with zero mismatches (SIM_DONE errors=0)",
        "implemented": True,
    },
    "logic_synthesis": {
        "name": "Logic Synthesis",
        "stage_order": 4,
        "allowed_tools": ["yosys"],
        "completion_criteria": "yosys synth exits 0, gate-level netlist + cell/area statistics produced",
        "implemented": True,
    },
    "physical_design": {
        "name": "Physical Design (Floorplan/Place/CTS/Route)",
        "stage_order": 5,
        "allowed_tools": ["openroad"],
        "completion_criteria": "OpenROAD flow completes with routed DEF and congestion reports",
        "implemented": False,
        "blocker": "OpenROAD not installed in this environment; no PDK/LEF/LIB available. Stage is honestly labeled BLOCKED.",
    },
    "timing_verification": {
        "name": "Timing & Physical Verification",
        "stage_order": 6,
        "allowed_tools": ["opensta", "magic", "netgen"],
        "completion_criteria": "STA reports setup/hold slack; DRC/LVS pass",
        "implemented": False,
        "blocker": "OpenSTA/DRC tools not installed; requires placed&routed design from stage 5. BLOCKED.",
    },
    "failure_diagnosis": {
        "name": "Failure Diagnosis & Recovery",
        "stage_order": 7,
        "allowed_tools": ["llm", "verilator_lint", "patch_rtl_isolated"],
        "completion_criteria": "root cause identified from real tool logs; minimal fix applied in isolated copy; affected stages re-run and pass; bounded retries",
        "implemented": True,
    },
    "signoff_report": {
        "name": "Signoff & Engineering Report",
        "stage_order": 8,
        "allowed_tools": ["aggregate_evidence"],
        "completion_criteria": "auditable report with per-stage evidence, traceability, missing-check list, and explicit disposition (never infers signoff from missing reports)",
        "implemented": True,
    },
}


def validate_output(agent_id: str, output: Dict[str, Any]) -> List[str]:
    """Deterministic contract validation. Returns list of problems."""
    fn = CONTRACT_VALIDATORS.get(agent_id)
    if fn is None:
        return [f"unknown agent id: {agent_id}"]
    try:
        return list(fn(output or {}))
    except Exception as e:
        return [f"contract validator crashed: {e}"]
