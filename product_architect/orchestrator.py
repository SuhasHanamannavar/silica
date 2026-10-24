import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable

try:
    from .agents import (
        MarketAnalyzer,
        FunctionalSpecGenerator,
        NonFunctionalSpecGenerator,
        ArchitecturalTradeoffAnalyst,
        RooflineModeler,
        BlockDiagramArchitect,
        InterfaceSpecifier,
        RiskAssessor,
        DieCostModeler,
        DocumentAssembler,
    )
    from .multi_pass_engine import MultiPassEngine
    from .llm_backend import LLMBackend
    from .knowledge_base import KnowledgeBase
except ImportError:
    from agents import (
        MarketAnalyzer,
        FunctionalSpecGenerator,
        NonFunctionalSpecGenerator,
        ArchitecturalTradeoffAnalyst,
        RooflineModeler,
        BlockDiagramArchitect,
        InterfaceSpecifier,
        RiskAssessor,
        DieCostModeler,
        DocumentAssembler,
    )
    from multi_pass_engine import MultiPassEngine
    from llm_backend import LLMBackend
    from knowledge_base import KnowledgeBase

class ProductArchitectOrchestrator:
    """
    Orchestrates all 9 sub-agents into a complete specification pipeline.
    Manages dependencies between agents, checkpoints, and human review.
    """
    
    def __init__(self, llm_backend=None, knowledge_base=None):
        self.llm = llm_backend or LLMBackend()
        self.kb = knowledge_base or KnowledgeBase()
        
        # Initialize all agents
        self.market_analyzer = MarketAnalyzer(self.llm, self.kb)
        self.func_spec_gen = FunctionalSpecGenerator(self.llm, self.kb)
        self.nfr_spec_gen = NonFunctionalSpecGenerator(self.llm, self.kb)
        self.tradeoff_analyst = ArchitecturalTradeoffAnalyst(self.llm, self.kb)
        self.roofline_modeler = RooflineModeler(self.llm, self.kb)
        self.block_diagram = BlockDiagramArchitect()
        self.interface_specifier = InterfaceSpecifier(self.llm, self.kb)
        self.risk_assessor = RiskAssessor(self.llm, self.kb)
        self.die_cost_modeler = DieCostModeler()  # Deterministic
        self.document_assembler = DocumentAssembler(self.llm)
        self.multipass = MultiPassEngine(self.llm)
    
    def run_full_pipeline(self, user_inputs: Dict, 
                          use_multipass: bool = True,
                          on_progress: Optional[Callable[[int, int, str], None]] = None) -> Dict:
        """
        Run the complete specification pipeline.
        
        user_inputs = {
            "product_brief": str,
            "target_market": str,
            "key_workloads": List[str],
            "power_budget_w": float,
            "process_node": str,
            "competitors": List[str],
        }
        """
        pipeline_state = {
            "inputs": user_inputs,
            "stages": {},
            "audit_trail": [],
            "started_at": self._timestamp()
        }
        
        def _notify(stage_num: int, stage_name: str):
            msg = f"Stage {stage_num}/9: {stage_name}"
            print(f"  {msg}...")
            pipeline_state["audit_trail"].append({
                "stage": stage_num,
                "name": stage_name,
                "timestamp": self._timestamp()
            })
            if on_progress:
                try:
                    on_progress(stage_num, 9, stage_name)
                except Exception:
                    pass
        
        # Stage 1: Market Analysis
        _notify(1, "Market & Competitive Analysis")
        market = self.market_analyzer.run(user_inputs)
        pipeline_state["stages"]["market_analysis"] = market
        
        # Stage 2: Functional Specification (with multi-pass)
        _notify(2, "Functional Specification")
        if use_multipass:
            func = self.multipass.run(
                self.func_spec_gen, 
                {"inputs": user_inputs, "market_analysis": market}
            )
        else:
            func = self.func_spec_gen.run(user_inputs, market)
        pipeline_state["stages"]["functional_spec"] = func
        
        # Stage 3: Non-Functional Specification
        _notify(3, "Non-Functional Specification")
        if use_multipass:
            nfr = self.multipass.run(
                self.nfr_spec_gen,
                {"inputs": user_inputs, "functional_spec": func}
            )
        else:
            nfr = self.nfr_spec_gen.run(user_inputs, func)
        pipeline_state["stages"]["non_functional_spec"] = nfr
        
        # Stage 4: Tradeoff Analysis
        _notify(4, "Architectural Tradeoff Analysis")
        tradeoffs = self.tradeoff_analyst.run(user_inputs, func, nfr)
        pipeline_state["stages"]["tradeoff_analysis"] = tradeoffs
        
        # Stage 5: Roofline Analysis (deterministic + interpretation)
        _notify(5, "Roofline Performance Analysis")
        workloads = user_inputs.get("key_workloads", ["LLM training", "LLM inference"])
        roofline = self.roofline_modeler.run(func, workloads)
        pipeline_state["stages"]["roofline_analysis"] = roofline
        
        # Stage 6: Block Diagram Architecture
        _notify(6, "Block Diagram & Floorplan Partitioning")
        block_diag = self.block_diagram.run(func, nfr)
        pipeline_state["stages"]["block_diagram"] = block_diag
        
        # Stage 7: Interface Specification
        _notify(7, "Interface Specification (External & Internal)")
        interfaces = self.interface_specifier.run(func, nfr)
        pipeline_state["stages"]["interface_spec"] = interfaces
        
        # Stage 8: Risk Assessment
        _notify(8, "Systemic Risk Assessment & Register")
        risks = self.risk_assessor.run(func, nfr, tradeoffs)
        pipeline_state["stages"]["risk_register"] = risks
        
        # Stage 9: Die Cost Model (deterministic physics & economics)
        _notify(9, "Physical Die Cost & Yield Modeling")
        node = user_inputs.get("process_node", "TSMC 3nm")
        die_cost = self.die_cost_modeler.run(nfr, node)
        pipeline_state["stages"]["die_cost_model"] = die_cost
        
        # Assemble all documents
        print("  Assembling specification documents...")
        all_outputs = {**pipeline_state["stages"]}
        docs = self.document_assembler.run(all_outputs)
        pipeline_state["documents"] = docs
        
        pipeline_state["status"] = "draft_for_human_review"
        pipeline_state["spec_freeze_ready"] = False
        pipeline_state["completed_at"] = self._timestamp()
        
        return pipeline_state
    
    def apply_human_feedback(self, pipeline_state: Dict, 
                             feedback: Dict) -> Dict:
        """
        Apply human review feedback and update approval state.
        feedback = {
            "stage_name": {
                "approved": bool,
                "comments": str,
                "specific_changes": {...}
            }
        }
        """
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

    def freeze_specification(self, pipeline_state: Dict, signoff_lead: str = "Chief Architect") -> Dict:
        """Explicitly freeze the specification package."""
        pipeline_state["status"] = "SPEC_FROZEN"
        pipeline_state["spec_freeze_ready"] = True
        pipeline_state["frozen_at"] = self._timestamp()
        pipeline_state["signoff_lead"] = signoff_lead
        if "documents" in pipeline_state and "downstream_handoff" in pipeline_state["documents"]:
            pipeline_state["documents"]["downstream_handoff"]["spec_freeze_status"] = f"FROZEN — SIGNED OFF BY {signoff_lead.upper()}"
        return pipeline_state
    
    def _timestamp(self) -> str:
        from datetime import timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
