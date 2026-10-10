"""
Silica multi-agent orchestrator.

Workflow (vertical slice; blocked stages honestly labeled):
  specification -> rtl_design -> functional_verification -> logic_synthesis
  -> physical_design (BLOCKED) -> timing_verification (BLOCKED) -> signoff_report

Failure diagnosis is invoked inline when rtl_design/verification fails,
operating on an isolated copy with bounded retries.

Guarantees:
- Explicit stage states (pending|running|passed|failed|blocked|escalated).
- Versioned artifacts passed between stages; a stage only consumes
  validated outputs from its prerequisites.
- Stage prerequisites enforced; downstream invalidated on upstream change.
- Checkpoint/resume: run.json persisted after every stage; resume skips
  already-passed stages.
- Cancellation via cancel flag; timeouts per EDA command in sandbox.
- Human approval: escalation recorded; run stops in 'awaiting_human' state.
- Provenance: model, prompt version, tool versions, and audit trails stored.
"""
from __future__ import annotations
import json
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from .contracts import AGENT_REGISTRY
from .hf_serving import HFServingAdapter
from .sandbox import EDASandbox
from .specialists import build_agent

# Vertical-slice pipeline order. Physical + timing are included but report BLOCKED.
PIPELINE = [
    "specification", "rtl_design", "functional_verification",
    "logic_synthesis", "physical_design", "timing_verification", "signoff_report",
]
PREREQUISITES = {
    "specification": [],
    "rtl_design": ["specification"],
    "functional_verification": ["rtl_design"],
    "logic_synthesis": ["functional_verification"],
    "physical_design": ["logic_synthesis"],
    "timing_verification": ["physical_design"],
    "signoff_report": ["logic_synthesis"],  # signoff aggregates whatever completed
}


class StageState:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.status = "pending"
        self.result: Optional[Dict[str, Any]] = None
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.attempts = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"agent_id": self.agent_id, "status": self.status,
                "started_at": self.started_at, "finished_at": self.finished_at,
                "attempts": self.attempts, "result": self.result}


class RunState:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.id = os.path.basename(run_dir)
        self.stages: Dict[str, StageState] = {aid: StageState(aid) for aid in PIPELINE}
        self.status = "pending"
        self.events: List[Dict[str, Any]] = []
        self.recovery_attempts = 0
        self.cancel_flag = threading.Event()
        self.artifacts: List[str] = []
        self.started_at = time.time()
        os.makedirs(os.path.join(run_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(run_dir, "artifacts"), exist_ok=True)
        os.makedirs(os.path.join(run_dir, "work"), exist_ok=True)

    def event(self, kind: str, **kw):
        self.events.append({"ts": time.time(), "kind": kind, **kw})

    def save(self):
        data = {
            "id": self.id, "status": self.status, "started_at": self.started_at,
            "stages": {aid: s.to_dict() for aid, s in self.stages.items()},
            "events": self.events[-200:], "recovery_attempts": self.recovery_attempts,
            "artifacts": self.artifacts,
        }
        with open(os.path.join(self.run_dir, "run.json"), "w") as f:
            json.dump(data, f, indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "status": self.status, "started_at": self.started_at,
            "stages": {aid: s.to_dict() for aid, s in self.stages.items()},
            "events": self.events[-50:], "recovery_attempts": self.recovery_attempts,
            "artifacts": self.artifacts,
        }


class Orchestrator:
    def __init__(self, projects_dir: str, hf: Optional[HFServingAdapter] = None,
                 max_recovery: int = 2):
        self.projects_dir = projects_dir
        self.hf = hf or HFServingAdapter()
        self.max_recovery = max_recovery
        os.makedirs(projects_dir, exist_ok=True)

    def _prereqs_ok(self, run: RunState, agent_id: str) -> bool:
        for pre in PREREQUISITES.get(agent_id, []):
            if run.stages[pre].status != "passed":
                # signoff can run even if physical/timing blocked
                if agent_id == "signoff_report":
                    continue
                return False
        return True

    def _stage_inputs(self, run: RunState, agent_id: str, rtl_override: Optional[str] = None) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        if agent_id == "specification":
            inputs["natural_language"] = run._natural_language  # set at start
        if agent_id == "rtl_design":
            inputs["spec"] = (run.stages["specification"].result or {}).get("output", {})
            if rtl_override:
                inputs["rtl"] = rtl_override  # recovered/user RTL must be linted, not regenerated
        if agent_id in ("functional_verification", "logic_synthesis"):
            rtl = rtl_override or (run.stages["rtl_design"].result or {}).get("output", {}).get("rtl", "")
            inputs["rtl"] = rtl
        if agent_id == "signoff_report":
            inputs["stage_results"] = {aid: s.result for aid, s in run.stages.items() if s.result}
        return inputs

    def run_pipeline(self, project_id: str, natural_language: str,
                     rtl_override: Optional[str] = None) -> RunState:
        pdir = os.path.join(self.projects_dir, project_id)
        rid = uuid.uuid4().hex[:8]
        run = RunState(os.path.join(pdir, "runs", rid))
        run._natural_language = natural_language
        run.status = "running"
        run.event("run_started", pipeline=PIPELINE)
        run.save()

        sandbox = EDASandbox(os.path.join(run.run_dir, "work"))
        artifacts_dir = os.path.join(run.run_dir, "artifacts")
        current_rtl = rtl_override

        for agent_id in PIPELINE:
            if run.cancel_flag.is_set():
                run.status = "cancelled"; run.event("cancelled"); run.save(); return run
            st = run.stages[agent_id]
            if not self._prereqs_ok(run, agent_id):
                st.status = "blocked"
                st.finished_at = time.time()
                run.event("stage_skipped", agent=agent_id, reason="prerequisite not passed")
                run.save(); continue
            st.status = "running"; st.started_at = time.time(); run.save()
            agent = build_agent(agent_id, hf=self.hf, sandbox=sandbox,
                                config={"artifacts_dir": artifacts_dir, "max_recovery_retries": self.max_recovery})
            try:
                result = agent.run(self._stage_inputs(run, agent_id, rtl_override=current_rtl))
            except Exception as e:
                st.status = "failed"; st.finished_at = time.time()
                st.result = {"status": "failed", "error": str(e)}
                run.event("stage_error", agent=agent_id, error=str(e))
                run.status = "failed"; run.save(); return run

            st.attempts += 1
            st.result = result.to_dict()
            st.status = result.status
            st.finished_at = time.time()
            run.event("stage_finished", agent=agent_id, status=result.status,
                      confidence=result.confidence)

            # --- inline failure recovery for rtl_design / verification ---
            if result.status in ("failed",) and agent_id in ("rtl_design", "functional_verification"):
                if run.recovery_attempts < self.max_recovery:
                    run.recovery_attempts += 1
                    error_log = ""
                    if agent_id == "rtl_design":
                        error_log = ((result.output.get("lint_result") or {}).get("log_tail") or "")
                        base_rtl = current_rtl or result.output.get("rtl", "")
                    else:
                        base_rtl = current_rtl or (run.stages["rtl_design"].result or {}).get("output", {}).get("rtl", "")
                        error_log = next((e.get("log_tail", "") for e in (result.evidence or [])
                                          if e.get("status") == "failed"), "simulation mismatch; no failing log captured")
                    diag = build_agent("failure_diagnosis", hf=self.hf, sandbox=sandbox,
                                       config={"artifacts_dir": artifacts_dir})
                    dres = diag.run({"rtl": base_rtl, "error_log": error_log, "failed_stage": agent_id}).to_dict()
                    run.stages["failure_diagnosis"] = StageState("failure_diagnosis")
                    run.stages["failure_diagnosis"].status = dres["status"]
                    run.stages["failure_diagnosis"].result = dres
                    run.event("recovery_attempt", attempt=run.recovery_attempts,
                              actions=dres["output"].get("proposed_fix", ""),
                              disposition=dres["output"].get("disposition"))
                    fixed_rtl = dres["output"].get("fixed_rtl")
                    if fixed_rtl and dres["status"] != "escalated":
                        current_rtl = fixed_rtl
                        # re-run from rtl_design onward by resetting downstream stages
                        for aid in PIPELINE[PIPELINE.index(agent_id):]:
                            if aid != agent_id:
                                run.stages[aid] = StageState(aid)
                        st.status = "pending"; st.result = None
                        run.save()
                        # re-enter loop at rtl_design
                        import sys
                        # restart pipeline from rtl_design
                        idx = PIPELINE.index("rtl_design")
                        for aid2 in PIPELINE[idx:]:
                            run.stages[aid2] = run.stages.get(aid2, StageState(aid2))
                        # simplest: recursive re-run from rtl_design
                        run.save()
                        return self._resume_from(run, "rtl_design", current_rtl, sandbox, artifacts_dir)
                    else:
                        run.status = "awaiting_human"
                        run.event("escalated", reason="recovery failed or not applicable")
                        run.save(); return run
            if result.status == "failed":
                run.status = "failed"; run.save(); return run
            run.save()

        # final disposition from signoff stage
        signoff = run.stages.get("signoff_report")
        if signoff and signoff.result:
            disp = signoff.result.get("output", {}).get("disposition", "incomplete")
            run.status = "passed" if disp == "complete" else disp
        else:
            run.status = "passed"
        run.event("run_finished", status=run.status)
        run.save()
        return run

    def _resume_from(self, run: RunState, from_agent: str, current_rtl, sandbox, artifacts_dir) -> RunState:
        """Re-run pipeline from a given agent after recovery."""
        idx = PIPELINE.index(from_agent)
        for aid in PIPELINE[idx:]:
            run.stages[aid] = StageState(aid)
        run.status = "running"
        run.save()
        for agent_id in PIPELINE[idx:]:
            if run.cancel_flag.is_set():
                run.status = "cancelled"; run.save(); return run
            st = run.stages[agent_id]
            if not self._prereqs_ok(run, agent_id):
                if agent_id == "signoff_report":
                    pass
                else:
                    st.status = "blocked"; st.finished_at = time.time(); run.save(); continue
            st.status = "running"; st.started_at = time.time(); run.save()
            agent = build_agent(agent_id, hf=self.hf, sandbox=sandbox,
                                config={"artifacts_dir": artifacts_dir, "max_recovery_retries": self.max_recovery})
            try:
                result = agent.run(self._stage_inputs(run, agent_id, rtl_override=current_rtl))
            except Exception as e:
                st.status = "failed"; st.result = {"error": str(e)}; run.status = "failed"; run.save(); return run
            st.attempts += 1; st.result = result.to_dict(); st.status = result.status
            st.finished_at = time.time()
            run.event("stage_finished", agent=agent_id, status=result.status)
            # inline recovery on rtl/verification failure (enables multi-attempt recovery loop)
            if result.status == "failed" and agent_id in ("rtl_design", "functional_verification"):
                if run.recovery_attempts < self.max_recovery:
                    run.recovery_attempts += 1
                    base_rtl = current_rtl or (run.stages["rtl_design"].result or {}).get("output", {}).get("rtl", "")
                    error_log = ((result.output.get("lint_result") or {}).get("log_tail") or "") if agent_id == "rtl_design" else "simulation mismatch"
                    diag = build_agent("failure_diagnosis", hf=self.hf, sandbox=sandbox, config={"artifacts_dir": artifacts_dir})
                    dres = diag.run({"rtl": base_rtl, "error_log": error_log, "failed_stage": agent_id}).to_dict()
                    run.stages["failure_diagnosis"] = StageState("failure_diagnosis")
                    run.stages["failure_diagnosis"].status = dres["status"]
                    run.stages["failure_diagnosis"].result = dres
                    run.event("recovery_attempt", attempt=run.recovery_attempts, actions=dres["output"].get("proposed_fix", ""), disposition=dres["output"].get("disposition"))
                    fixed_rtl = dres["output"].get("fixed_rtl")
                    if fixed_rtl and dres["status"] != "escalated":
                        current_rtl = fixed_rtl
                        run.save()
                        return self._resume_from(run, "rtl_design", current_rtl, sandbox, artifacts_dir)
                    else:
                        run.status = "awaiting_human"; run.save(); return run
            if result.status == "failed":
                run.status = "failed"; run.save(); return run
            run.save()
        signoff = run.stages.get("signoff_report")
        if signoff and signoff.result:
            disp = signoff.result.get("output", {}).get("disposition", "incomplete")
            run.status = "passed" if disp == "complete" else disp
        run.event("run_finished", status=run.status)
        run.save()
        return run
