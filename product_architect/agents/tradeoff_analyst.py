import json
from typing import Dict, Any

class ArchitecturalTradeoffAnalyst:
    """
    Analyzes key architectural decisions with multi-dimensional scoring.
    This is where the AI demonstrates "architect-level judgment."
    """
    
    PROMPT_TEMPLATE = """You are the CHIEF GPU ARCHITECT at NVIDIA.
You have the final say on architectural decisions. Your analysis must be BALANCED and DATA-DRIVEN.

{context}

FUNCTIONAL SPEC:
{functional_spec}

NON-FUNCTIONAL SPEC:
{nfr_spec}

For EACH of these critical decisions, provide a DETAILED analysis with NUMERIC scores.

DECISION 1: MONOLITHIC vs CHIPLET DESIGN
- Current die area estimate: {die_area} mm²
- Reticle limit: 858 mm²

DECISION 2: PRECISION FORMAT STRATEGY
- Target workloads: {workloads}
- Should we add NVFP4? FP4?

DECISION 3: L2 CACHE SIZING
- Options: 96MB, 192MB, 384MB
- Analyze against target workloads

DECISION 4: HBM GENERATION SELECTION
- Options: HBM3e, HBM4
- Consider bandwidth, capacity, cost, timeline

DECISION 5: SM COUNT vs CLOCK FREQUENCY
- More SMs at lower clock vs fewer SMs at higher clock
- PPA tradeoffs

For EACH decision, output this JSON structure:
{{
  "decision_id": "monolithic_vs_chiplet",
  "options_analyzed": [
    {{
      "option_name": "Monolithic single die",
      "scores": {{
        "performance": 1-10,
        "power_efficiency": 1-10,
        "area_cost": 1-10,
        "engineering_complexity": 1-10,
        "time_to_market": 1-10,
        "programmability": 1-10,
        "yield_risk": 1-10
      }},
      "quantitative_impact": {{
        "performance_change_percent": NUMBER,
        "power_change_percent": NUMBER,
        "area_change_percent": NUMBER,
        "engineering_months": NUMBER,
        "yield_estimate_percent": NUMBER
      }},
      "pros": ["list"],
      "cons": ["list"]
    }},
    {{
      "option_name": "Chiplet: 2 dies on CoWoS",
      "scores": {{...same dimensions...}},
      "quantitative_impact": {{...}},
      "pros": ["list"],
      "cons": ["list"]
    }}
  ],
  "recommendation": "Option name",
  "rationale": "Detailed explanation of why this option is optimal",
  "key_assumptions": ["list of assumptions"],
  "sensitivity_analysis": "What would change the recommendation?"
}}

Then output a "decisions_summary" array with all 5 decisions.
"""
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, inputs: Dict, functional_spec: Dict, nfr_spec: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            "GPU architecture tradeoff monolithic chiplet HBM cache design",
            categories=["nvidia_architecture", "hbm_specs", "cost_models", "process_node_data"]
        )
        
        die_area = nfr_spec.get("area_budget", {}).get("total_die_area_mm2", 820)
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            functional_spec=json.dumps(functional_spec, indent=2)[:3000],
            nfr_spec=json.dumps(nfr_spec, indent=2)[:2000],
            die_area=die_area,
            workloads=", ".join(inputs.get("key_workloads", ["LLM", "Diffusion"])),
        )
        
        result = self.llm.call("tradeoff_analysis", prompt, enforce_json=True)
        out = result.get("structured_output")
        if not isinstance(out, dict) or not out:
            out = self.llm._deterministic_fallback("tradeoff_analysis", prompt).get("structured_output", {})
        return out

TradeoffAnalyst = ArchitecturalTradeoffAnalyst
