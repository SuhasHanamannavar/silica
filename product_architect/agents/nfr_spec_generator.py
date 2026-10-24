import json
from typing import Dict, Any

class NonFunctionalSpecGenerator:
    """
    Generates all the hard constraints: power, area, thermal, reliability, cost.
    """
    
    PROMPT_TEMPLATE = """You are a PRINCIPAL NVIDIA SYSTEM ARCHITECT.
You define the QUANTIFIED CONSTRAINTS that every downstream engineer must hit.
These numbers become CONTRACTS — if they're wrong, the chip fails.

{context}

PRODUCT VISION: {product_brief}
TARGET MARKET: {target_market}
POWER BUDGET: {power_budget}W
PROCESS NODE: {process_node}

FUNCTIONAL SPEC INPUT:
{functional_spec}

Generate the COMPLETE NON-FUNCTIONAL SPECIFICATION as JSON:
{{
  "performance_constraints": {{
    "clock_frequencies": {{
      "base_clock_mhz": NUMBER,
      "boost_clock_mhz": NUMBER,
      "memory_clock_mhz": NUMBER,
      "nvlink_clock_mhz": NUMBER,
      "pcie_clock_mhz": NUMBER
    }},
    "latency_targets": {{
      "hbm_read_latency_ns": NUMBER,
      "l2_hit_latency_ns": NUMBER,
      "l1_hit_latency_ns": NUMBER,
      "nvlink_latency_ns": NUMBER,
      "pcie_latency_ns": NUMBER,
      "warp_scheduling_latency_cycles": NUMBER
    }},
    "throughput_targets": {{
      "llm_training_tokens_per_sec": NUMBER,
      "llm_inference_tokens_per_sec": NUMBER,
      "llm_prefill_ms": NUMBER,
      "llm_decode_ms_per_token": NUMBER
    }}
  }},
  "power_budget": {{
    "total_tdp_watts": {power_budget},
    "allocation": {{
      "compute_sm_array": {{"percent": 45, "watts": NUMBER}},
      "memory_phy_controller": {{"percent": 22, "watts": NUMBER}},
      "l2_cache": {{"percent": 12, "watts": NUMBER}},
      "noc_interconnect": {{"percent": 10, "watts": NUMBER}},
      "nvlink_pcie_phys": {{"percent": 8, "watts": NUMBER}},
      "clock_power_mgmt": {{"percent": 3, "watts": NUMBER}}
    }},
    "idle_power_watts": NUMBER,
    "power_efficiency_target_tflops_per_watt": NUMBER,
    "dvfs_support": true,
    "operating_points": [
      {{"voltage_v": 0.75, "clock_mhz": NUMBER}},
      {{"voltage_v": 0.85, "clock_mhz": NUMBER}},
      {{"voltage_v": 0.95, "clock_mhz": NUMBER}}
    ],
    "power_gating_supported": true,
    "clock_gating_coverage_percent": 85
  }},
  "area_budget": {{
    "total_die_area_mm2": NUMBER,
    "reticle_limit_check": "WITHIN / EXCEEDS",
    "chiplet_required": true/false,
    "chiplet_count_if_required": NUMBER,
    "allocation": {{
      "sm_array": {{"percent": 40, "mm2": NUMBER}},
      "l2_cache": {{"percent": 20, "mm2": NUMBER}},
      "memory_controllers_phy": {{"percent": 15, "mm2": NUMBER}},
      "noc": {{"percent": 10, "mm2": NUMBER}},
      "nvlink_pcie": {{"percent": 10, "mm2": NUMBER}},
      "other": {{"percent": 5, "mm2": NUMBER}}
    }},
    "package_type": "SXM / CoWoS-L / PCIe",
    "package_dimensions_mm": "NUMBER x NUMBER",
    "bump_count": NUMBER,
    "bump_pitch_um": NUMBER
  }},
  "thermal_specification": {{
    "max_junction_temp_c": 105,
    "operating_temp_range_c": "0 to 85",
    "thermal_resistance_theta_jc_c_per_w": NUMBER,
    "cooling_solution": "Liquid cold plate / Air heatsink",
    "airflow_requirement_cfm": NUMBER,
    "max_power_density_w_per_mm2": NUMBER
  }},
  "reliability_availability": {{
    "fit_rate_target": NUMBER,
    "mtbf_hours": NUMBER,
    "service_life_years": 5,
    "ecc_schemes": {{
      "hbm": "Double-chipkill",
      "l2": "SEC-DED inline",
      "l1": "Parity",
      "registers": "Parity"
    }},
    "ras_features": ["error_containment", "fault_isolation", "page_retirement"]
  }},
  "cost_targets": {{
    "die_cost_usd": NUMBER,
    "package_cost_usd": NUMBER,
    "hbm_cost_usd": NUMBER,
    "total_bom_usd": NUMBER,
    "nre_mask_cost_usd": NUMBER,
    "asp_target_usd": NUMBER,
    "gross_margin_target_percent": 70
  }},
  "physical_constraints": {{
    "voltage_rails": [
      {{"name": "VDD_CORE", "voltage_v": 0.85, "tolerance_percent": 5, "max_current_a": NUMBER}},
      {{"name": "VDD_MEM", "voltage_v": 1.1, "tolerance_percent": 5, "max_current_a": NUMBER}}
    ],
    "power_sequencing_requirements": "VDD_MEM first, then VDD_CORE, delay 200us",
    "emc_requirements": "FCC Class A, CISPR 32",
    "mechanical_form_factor": "SXM5 / PCIe Gen6 FHFL"
  }}
}}

IMPORTANT:
- All percentages must sum to 100%
- All watts = total_tdp × percent / 100
- All mm2 = total_area × percent / 100
- Numbers must be CONSISTENT with the functional spec
- Be REALISTIC for a modern high-end GPU at {process_node}
"""
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, inputs: Dict, functional_spec: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            f"GPU power area thermal cost budget allocation {inputs.get('process_node', '')}",
            categories=["power_models", "area_models", "cost_models", "process_node_data"]
        )
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            product_brief=inputs.get("product_brief", "AI GPU"),
            target_market=inputs.get("target_market", "Datacenter"),
            power_budget=inputs.get("power_budget_w", 700),
            process_node=inputs.get("process_node", "TSMC 3nm"),
            functional_spec=json.dumps(functional_spec, indent=2)[:4000],
        )
        
        result = self.llm.call("nfr_spec", prompt, enforce_json=True)
        spec = result.get("structured_output", {})
        if not isinstance(spec, dict) or not spec:
            spec = self.llm._deterministic_fallback("nfr_spec", prompt).get("structured_output", {})
        
        # Deterministic budget validation
        spec = self._validate_budgets(spec, inputs)
        return spec
    
    def _validate_budgets(self, spec: Dict, inputs: Dict = None) -> Dict:
        """Ensure budgets sum correctly and adhere to physical limits."""
        try:
            power = spec.get("power_budget", {})
            total_w = power.get("total_tdp_watts") or (inputs.get("power_budget_w", 700) if inputs else 700)
            power["total_tdp_watts"] = total_w
            alloc = power.get("allocation", {})
            
            # Fix wattages based on percentages
            pct_sum = 0
            for key, val in alloc.items():
                pct = val.get("percent", 0)
                pct_sum += pct
                val["watts"] = round(total_w * pct / 100, 1)
            
            area = spec.get("area_budget", {})
            total_area = area.get("total_die_area_mm2", 820)
            area_alloc = area.get("allocation", {})
            
            area_pct_sum = 0
            for key, val in area_alloc.items():
                pct = val.get("percent", 0)
                area_pct_sum += pct
                val["mm2"] = round(total_area * pct / 100, 1)
            
            # Reticle limit check (858 mm² limit)
            area["reticle_limit_check"] = "WITHIN" if total_area <= 858 else "EXCEEDS"
            area["chiplet_required"] = total_area > 800  # Conservative margin for yield
            if area["chiplet_required"]:
                area["chiplet_count_if_required"] = 2
            
            spec["_budget_validation"] = {
                "power_percent_sum": pct_sum,
                "area_percent_sum": area_pct_sum,
                "budgets_consistent": abs(pct_sum - 100) < 1 and abs(area_pct_sum - 100) < 1,
            }
        except Exception as e:
            spec["_budget_validation"] = {"error": str(e)}
        
        return spec
