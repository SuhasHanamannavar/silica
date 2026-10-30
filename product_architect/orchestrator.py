import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List

from product_architect.llm_backend import LLMBackend
from product_architect.knowledge_base import KnowledgeBase
from product_architect.validators import SpecValidator
from product_architect.multipass import MultiPassEngine
from product_architect.agents.functional_spec import FunctionalSpecAgent
from product_architect.agents.nfr_spec import NFRSpecAgent
from product_architect.agents.tradeoff_analyst import TradeoffAnalyst
from product_architect.agents.roofline_modeler import RooflineModeler
from product_architect.agents.block_diagram import BlockDiagramArchitect
from product_architect.agents.interface_specifier import InterfaceSpecifier
from product_architect.agents.risk_assessor import RiskAssessor
from product_architect.agents.die_cost_modeler import DieCostModeler
from product_architect.agents.document_assembler import DocumentAssembler
from product_architect.agents.market_analyzer import MarketAnalyzer

class ProductArchitectOrchestrator:
    """
    NVIDIA-Caliber Orchestrator for Silica Product Architect.
    Executes the 9 specialist architecture agents in sequence, manages
    deterministic validation gates, multi-pass critique loops, and human sign-off gates.
    """
    
    def __init__(self, llm_backend: Optional[LLMBackend] = None, knowledge_base: Optional[KnowledgeBase] = None):
        self.llm = llm_backend or LLMBackend()
        self.kb = knowledge_base or KnowledgeBase()
        self.validator = SpecValidator()
        self.multipass = MultiPassEngine(self.llm)
        
        # Initialize all 9 specialist agents
        self.market_analyzer = MarketAnalyzer(self.llm, self.kb)
        self.func_agent = FunctionalSpecAgent(self.llm, self.kb, self.validator)
        self.nfr_agent = NFRSpecAgent(self.llm, self.kb, self.validator)
        self.tradeoff_agent = TradeoffAnalyst(self.llm, self.kb)
        self.roofline_modeler = RooflineModeler(self.validator, self.llm)
        self.block_diagram = BlockDiagramArchitect()
        self.iface_agent = InterfaceSpecifier(self.llm, self.kb, self.validator)
        self.risk_agent = RiskAssessor(self.llm, self.kb)
        self.cost_modeler = DieCostModeler(self.validator)
        self.doc_assembler = DocumentAssembler(self.llm)
        
        # Backwards compatibility aliases
        self.func_spec_gen = self.func_agent
        self.nfr_spec_gen = self.nfr_agent
        self.tradeoff_analyst = self.tradeoff_agent
        self.interface_specifier = self.iface_agent
        self.risk_assessor = self.risk_agent
        self.die_cost_modeler = self.cost_modeler
        self.document_assembler = self.doc_assembler
    
    def run(self, user_inputs: Dict[str, Any], use_multipass: bool = True) -> Dict[str, Any]:
        """
        Run the complete architecture specification pipeline.
        
        user_inputs = {
            "product_brief": str,
            "target_market": str,
            "key_workloads": List[str],
            "power_budget_w": float,
            "process_node": str,
            "competitors": List[str],
        }
        """
        return self.run_full_pipeline(user_inputs, use_multipass=use_multipass)
    
    def run_full_pipeline(self, user_inputs: Dict[str, Any], 
                          use_multipass: bool = True,
                          on_progress: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
        pipeline = {
            "inputs": user_inputs,
            "stages": {},
            "audit_trail": [],
            "started_at": self._timestamp()
        }
        
        def _record_audit(stage_num: int, stage_name: str, res: Any, duration_s: float, default_model: str = "deterministic"):
            model = default_model
            provider = "local"
            if isinstance(res, dict):
                model = res.get("model_used") or default_model
                provider = res.get("provider") or ("groq" if "qwen" in str(model) or "llama" in str(model) or "gpt" in str(model) else "deterministic")
            pipeline["audit_trail"].append({
                "stage": stage_num,
                "name": stage_name,
                "model_used": model,
                "provider": provider,
                "latency_s": round(duration_s, 2),
                "timestamp": self._timestamp()
            })
            if on_progress:
                try:
                    on_progress(stage_num, 9, stage_name)
                except Exception:
                    pass

        # Stage 1: Market & Competitive Analysis
        t0 = time.time()
        print(f"  Stage 1/9: Market & Competitive Analysis...")
        market_result = self.market_analyzer.run(user_inputs)
        pipeline["stages"]["market_analysis"] = market_result
        _record_audit(1, "Market & Competitive Analysis", market_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 2: Functional Specification
        t0 = time.time()
        print(f"  Stage 2/9: Functional Specification...")
        if use_multipass:
            func_result = self.multipass.refine_spec(
                self.func_agent, {"inputs": user_inputs, "market_analysis": market_result}
            )
        else:
            func_result = self.func_agent.run(user_inputs, market_analysis=market_result)
        
        func_spec = func_result.get("spec", func_result) if isinstance(func_result, dict) else func_result
        stage_func = dict(func_result) if isinstance(func_result, dict) else {}
        stage_func["spec"] = func_spec
        if isinstance(func_spec, dict):
            for k, v in func_spec.items():
                if k not in stage_func:
                    stage_func[k] = v
        pipeline["stages"]["functional_spec"] = stage_func
        _record_audit(2, "Functional Specification", func_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 3: Non-Functional Specification
        t0 = time.time()
        print(f"  Stage 3/9: Non-Functional Specification...")
        if use_multipass:
            nfr_result = self.multipass.refine_spec(
                self.nfr_agent, {"inputs": user_inputs, "func_spec": func_spec}
            )
        else:
            nfr_result = self.nfr_agent.run(user_inputs, func_spec=func_spec)
            
        nfr_spec = nfr_result.get("spec", nfr_result) if isinstance(nfr_result, dict) else nfr_result
        stage_nfr = dict(nfr_result) if isinstance(nfr_result, dict) else {}
        stage_nfr["spec"] = nfr_spec
        if isinstance(nfr_spec, dict):
            for k, v in nfr_spec.items():
                if k not in stage_nfr:
                    stage_nfr[k] = v
        pipeline["stages"]["non_functional_spec"] = stage_nfr
        _record_audit(3, "Non-Functional Specification", nfr_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 4: Architectural Tradeoffs
        t0 = time.time()
        print(f"  Stage 4/9: Architectural Tradeoffs...")
        tradeoff_result = self.tradeoff_agent.run(user_inputs, func_spec, nfr_spec)
        pipeline["stages"]["tradeoff_analysis"] = tradeoff_result
        _record_audit(4, "Architectural Tradeoffs", tradeoff_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 5: Roofline Performance Analysis
        t0 = time.time()
        print(f"  Stage 5/9: Roofline Performance Analysis...")
        workloads = user_inputs.get("key_workloads", ["LLM training 70B+", "LLM autoregressive decode", "diffusion models"])
        roofline_result = self.roofline_modeler.run(func_spec, workloads)
        pipeline["stages"]["roofline_analysis"] = roofline_result
        _record_audit(5, "Roofline Performance Analysis", roofline_result, time.time() - t0, "deterministic-roofline-physics")
        
        # Stage 6: Block Diagram Architecture
        t0 = time.time()
        print(f"  Stage 6/9: Block Diagram Architecture...")
        block_result = self.block_diagram.run(func_spec, nfr_spec)
        pipeline["stages"]["block_diagram"] = block_result
        _record_audit(6, "Block Diagram Architecture", block_result, time.time() - t0, "deterministic-die-partitioner")
        
        # Stage 7: Interface Specification
        t0 = time.time()
        print(f"  Stage 7/9: Interface Specification...")
        iface_result = self.iface_agent.run(func_spec, nfr_spec)
        pipeline["stages"]["interface_spec"] = iface_result
        _record_audit(7, "Interface Specification", iface_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 8: Risk Assessment
        t0 = time.time()
        print(f"  Stage 8/9: Systemic Risk Assessment...")
        risk_result = self.risk_agent.run(func_spec, nfr_spec, tradeoff_result)
        pipeline["stages"]["risk_register"] = risk_result
        _record_audit(8, "Systemic Risk Assessment", risk_result, time.time() - t0, "qwen/qwen3.8-27b")
        
        # Stage 9: Die Cost Modeling
        t0 = time.time()
        print(f"  Stage 9/9: Die Cost & Yield Modeling...")
        cost_result = self.cost_modeler.run(nfr_spec, user_inputs.get("process_node", "TSMC 4nm"))
        pipeline["stages"]["die_cost_model"] = cost_result
        _record_audit(9, "Die Cost & Yield Modeling", cost_result, time.time() - t0, "murphy-yield-model-300mm")
        
        # Assemble Documents
        print("  Assembling specification documents...")
        docs = self.doc_assembler.run(pipeline["stages"])
        pipeline["documents"] = docs
        
        pipeline["status"] = "draft_for_human_review"
        pipeline["spec_freeze_ready"] = False
        pipeline["completed_at"] = self._timestamp()
        
        return pipeline
    
    def apply_human_feedback(self, pipeline_state: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Apply human strategic review feedback and update signoff state."""
        pipeline_state["human_feedback"] = feedback
        all_approved = all(
            f.get("approved", False) 
            for f in feedback.values()
            if isinstance(f, dict)
        )
        if all_approved and feedback:
            pipeline_state["status"] = "SPEC_FROZEN"
            pipeline_state["spec_freeze_ready"] = True
            pipeline_state["frozen_at"] = self._timestamp()
            if "documents" in pipeline_state and "downstream_handoff" in pipeline_state["documents"]:
                pipeline_state["documents"]["downstream_handoff"]["spec_freeze_status"] = "FROZEN — APPROVED FOR RTL SIGN-OFF"
        return pipeline_state

    def freeze_specification(self, pipeline_state: Dict[str, Any], signoff_lead: str = "Chief Architect") -> Dict[str, Any]:
        """Explicitly freeze the specification package."""
        pipeline_state["status"] = "SPEC_FROZEN"
        pipeline_state["spec_freeze_ready"] = True
        pipeline_state["frozen_at"] = self._timestamp()
        pipeline_state["signoff_lead"] = signoff_lead
        if "documents" in pipeline_state and "downstream_handoff" in pipeline_state["documents"]:
            pipeline_state["documents"]["downstream_handoff"]["spec_freeze_status"] = f"FROZEN — SIGNED OFF BY {signoff_lead.upper()}"
        return pipeline_state
    
    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")