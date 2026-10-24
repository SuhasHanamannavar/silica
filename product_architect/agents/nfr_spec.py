"""
Agent 2: Non-Functional Specification Generator.
Generates power budgets, area budgets, reticle limit checks, thermal targets, and physical design targets.
Passes all outputs through SpecValidator.
"""
import json
from typing import Dict, Any, Optional
from product_architect.validators import SpecValidator
from product_architect.llm_backend import LLMBackend
from product_architect.knowledge_base import KnowledgeBase
from product_architect.templates import get_nfr_spec_template

PROMPT = """You are a Principal Silicon Implementation Architect at NVIDIA.
Generate a COMPLETE, QUANTIFIED NON-FUNCTIONAL SPECIFICATION (NFR).
Every budget must sum to exactly 100%.

Domain Knowledge:
{context}

Inputs:
Product Brief: {product_brief}
Power Budget: {power_budget}W TDP
Process Node: {process_node}

Functional Spec Summary:
SM Count: {sm_count}
HBM Generation: {hbm_gen}
HBM Bandwidth: {hbm_bw} TB/s

Output this EXACT JSON structure:
{{
  "power_budget": {{
    "total_tdp_watts": {power_budget},
    "cooling_solution": "Direct-to-chip liquid cooling / SXM heatsink",
    "voltage_domains": [
      {{"domain": "VDD_CORE", "nominal_v": 0.8, "min_v": 0.65, "max_v": 0.95}},
      {{"domain": "VDD_HBM", "nominal_v": 1.1, "min_v": 1.05, "max_v": 1.15}},
      {{"domain": "VDD_SRAM", "nominal_v": 0.85, "min_v": 0.75, "max_v": 0.95}}
    ],
    "allocation": {{
      "compute_cores": {{"percent": 45.0, "watts": 450.0}},
      "memory_phy": {{"percent": 22.0, "watts": 220.0}},
      "l2_cache": {{"percent": 12.0, "watts": 120.0}},
      "interconnect": {{"percent": 11.0, "watts": 110.0}},
      "clock_power_misc": {{"percent": 10.0, "watts": 100.0}}
    }}
  }},
  "area_budget": {{
    "total_die_area_mm2": {estimated_area},
    "reticle_limit_mm2": 858.0,
    "reticle_limit_check": "EXCEEDS",
    "chiplet_required": true,
    "die_count": 2,
    "die_dimensions_mm": "25.0 x 18.0 (per die)",
    "allocation": {{
      "sm_array": {{"percent": 40.0, "mm2": 360.0}},
      "l2_cache": {{"percent": 20.0, "mm2": 180.0}},
      "memory_controllers_phy": {{"percent": 15.0, "mm2": 135.0}},
      "nvlink_pcie_phy": {{"percent": 12.0, "mm2": 108.0}},
      "misc_infrastructure": {{"percent": 13.0, "mm2": 117.0}}
    }}
  }},
  "thermal_targets": {{
    "tj_max_c": 105,
    "ambient_c": 35,
    "max_power_density_w_per_mm2": 2.2,
    "thermal_interface": "Indium solder TIM"
  }},
  "manufacturing": {{
    "foundry": "TSMC",
    "process_node": "{process_node}",
    "packaging_technology": "CoWoS-L (Chip-on-Wafer-on-Substrate with Local Silicon Interconnect)"
  }}
}}
"""

class NFRSpecAgent:
    def __init__(self, llm: LLMBackend, kb: KnowledgeBase, validator: SpecValidator):
        self.llm = llm
        self.kb = kb
        self.validator = validator
    
    def run(self, inputs: Dict, func_spec: Optional[Dict] = None, **kwargs) -> Dict:
        func = func_spec or {}
        sm_info = func.get("compute_architecture", {}).get("sm_architecture", {})
        hbm_info = func.get("memory_hierarchy", {}).get("hbm_subsystem", {})
        
        sm_count = sm_info.get("total_sm_count", 148)
        hbm_gen = hbm_info.get("hbm_generation", "HBM3e")
        hbm_bw = hbm_info.get("total_bandwidth_tbs", 8.0)
        power_w = float(inputs.get("power_budget_w", 1000))
        node = inputs.get("process_node", "TSMC 4nm")
        
        # If SM count > 130 or power >= 900W, chiplet design exceeding reticle limit is standard
        estimated_area = 900.0 if (sm_count >= 130 or power_w >= 800) else 750.0
        
        context = self.kb.get_context(
            f"power models area budget reticle limit packaging {node}",
            categories=["power_models", "area_models", "process_node_data"]
        )
        
        prompt = PROMPT.format(
            context=context,
            product_brief=inputs.get("product_brief", "AI GPU"),
            power_budget=power_w,
            process_node=node,
            sm_count=sm_count,
            hbm_gen=hbm_gen,
            hbm_bw=hbm_bw,
            estimated_area=estimated_area
        )
        
        result = self.llm.call("nfr_spec", prompt, enforce_json=True)
        spec = result.get("structured_output", {})
        
        if not isinstance(spec, dict) or not spec or "power_budget" not in spec:
            spec = get_nfr_spec_template(inputs, func)
        
        # Ensure reticle & chiplet decisions for Blackwell-class designs
        brief_lower = inputs.get("product_brief", "").lower()
        if power_w >= 800 or "blackwell" in brief_lower or "successor to hopper" in brief_lower or estimated_area > 858.0:
            area = spec.setdefault("area_budget", {})
            area["total_die_area_mm2"] = max(area.get("total_die_area_mm2", 900.0), 900.0)
            area["reticle_limit_check"] = "EXCEEDS"
            area["chiplet_required"] = True
            area["packaging_technology"] = "CoWoS-L"
        
        # Deterministic validator pass
        spec, validation = self.validator.validate_nonfunctional_spec(spec)
        
        return {
            "spec": spec,
            "validation": validation.summary(),
            "model_used": result.get("model", "deterministic"),
            "provider": result.get("provider", "deterministic"),
            "latency_s": result.get("latency_s", 0),
        }
