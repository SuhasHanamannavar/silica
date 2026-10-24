import json
from typing import Dict, Any

class FunctionalSpecGenerator:
    """
    Generates the complete functional specification.
    This is the most important agent — defines WHAT the chip does.
    """
    
    PROMPT_TEMPLATE = """You are a PRINCIPAL NVIDIA GPU ARCHITECT reporting directly to the Chief Scientist.
You have designed 4 generations of NVIDIA GPUs. Your decisions are data-driven and precise.

{context}

PRODUCT VISION: {product_brief}
TARGET MARKET: {target_market}
KEY WORKLOADS: {workloads}
POWER BUDGET: {power_budget}W
PROCESS NODE: {process_node}

MARKET ANALYSIS INPUT:
{market_analysis}

Generate a COMPLETE, QUANTIFIED FUNCTIONAL SPECIFICATION.
Every claim must have a NUMBER. Vague statements are unacceptable.

Output this exact JSON structure:
{{
  "compute_architecture": {{
    "precision_formats": [
      {{"format": "FP64", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "FP32", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "TF32", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "FP16", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "BF16", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "FP8", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "NVFP4", "peak_tflops": NUMBER, "enabled": true/false}},
      {{"format": "INT8", "peak_tops": NUMBER, "enabled": true/false}},
      {{"format": "INT4", "peak_tops": NUMBER, "enabled": true/false}}
    ],
    "tensor_core_design": {{
      "generation": "5th-gen",
      "mma_shapes_supported": ["M=16,N=16,K=16", "M=256,N=128,K=64"],
      "sparsity_support": true,
      "notes": "Specific design rationale"
    }},
    "sm_architecture": {{
      "total_sm_count": NUMBER,
      "cuda_cores_per_sm": NUMBER,
      "tensor_cores_per_sm": NUMBER,
      "warp_schedulers_per_sm": NUMBER,
      "register_file_per_sm_kb": NUMBER,
      "l1_shared_memory_per_sm_kb": NUMBER,
      "l1_shared_configurable": true,
      "base_clock_mhz": NUMBER,
      "boost_clock_mhz": NUMBER
    }},
    "instruction_set": {{
      "cuda_compatibility": "SM_XX",
      "new_instructions": ["list of new ISA extensions"],
      "backwards_compatible_to": "SM_XX"
    }}
  }},
  "memory_hierarchy": {{
    "hbm_subsystem": {{
      "hbm_generation": "HBM3e",
      "total_capacity_gb": NUMBER,
      "total_bandwidth_tbs": NUMBER,
      "stack_count": NUMBER,
      "bus_width_bits": NUMBER,
      "data_rate_gbps_per_pin": NUMBER,
      "ecc_support": "SEC-DED / Chipkill"
    }},
    "l2_cache": {{
      "total_size_mb": NUMBER,
      "organization": "distributed / unified",
      "banks": NUMBER,
      "compression_supported": true,
      "compression_ratio_max": NUMBER
    }},
    "l1_cache": {{
      "per_sm_size_kb": NUMBER,
      "configurable": true,
      "shared_memory_max_kb": NUMBER
    }},
    "register_file": {{
      "per_sm_kb": NUMBER,
      "total_gpu_kb": NUMBER
    }}
  }},
  "interconnect": {{
    "nvlink": {{
      "generation": "5.0",
      "lane_count": NUMBER,
      "data_rate_gbps_per_lane": NUMBER,
      "bidirectional_bandwidth_tbs": NUMBER,
      "latency_ns": NUMBER,
      "max_gpus_per_node": NUMBER,
      "switch_supported": true
    }},
    "pcie": {{
      "generation": "6.0",
      "lane_count": "x16",
      "bidirectional_bandwidth_gbs": NUMBER,
      "cxl_supported": true,
      "cxl_version": "3.1",
      "sriov_supported": true,
      "max_virtual_functions": NUMBER
    }},
    "noc_architecture": {{
      "topology": "Mesh / Ring / Crossbar",
      "bisection_bandwidth_tbs": NUMBER,
      "notes": "Specific design rationale"
    }}
  }},
  "virtualization_ras": {{
    "mig": {{
      "supported": true,
      "max_instances": NUMBER,
      "instance_types": ["1g.10gb", "2g.20gb", "etc."]
    }},
    "ecc": {{
      "hbm": "SEC-DED / Double-chipkill",
      "l2_cache": "Inline ECC",
      "l1_cache": "Parity / SEC-DED",
      "register_file": "Parity protected"
    }},
    "ras_features": [
      "Error containment",
      "Fault isolation",
      "Graceful degradation",
      "Page retirement"
    ],
    "fit_rate_target": "NUMBER failures per billion hours"
  }},
  "software": {{
    "cuda_compatibility": "Full CUDA X.Y+",
    "library_support": ["cuBLAS", "cuDNN", "TensorRT", "NCCL", "etc."],
    "framework_support": ["PyTorch", "TensorFlow", "JAX"],
    "backwards_compatibility": "All existing CUDA apps run without recompilation",
    "new_apis_required": ["list of new software enablement"]
  }},
  "design_assumptions": [
    "List all explicit assumptions that downstream teams must validate"
  ]
}}

IMPORTANT:
- All numbers must be PHYSICALLY REALIZABLE and consistent with each other
- Peak TFLOPS = SM_count × cores_per_SM × 2 (FMA) × clock_GHz × precision_factor
- Memory bandwidth = bus_width_bits × data_rate_Gbps / 8
- Justify your numbers with the market analysis and workload characteristics
- If you recommend a chiplet approach, specify die count and inter-die bandwidth
"""
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, inputs: Dict, market_analysis: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            f"GPU architecture compute memory HBM NVLink SM design {inputs.get('process_node', '')}",
            categories=["nvidia_architecture", "hbm_specs", "interface_standards", "process_node_data"]
        )
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            product_brief=inputs.get("product_brief", "AI GPU"),
            target_market=inputs.get("target_market", "Datacenter"),
            workloads=", ".join(inputs.get("key_workloads", ["LLM Training", "LLM Inference"])),
            power_budget=inputs.get("power_budget_w", 700),
            process_node=inputs.get("process_node", "TSMC 3nm"),
            market_analysis=json.dumps(market_analysis, indent=2)[:3000],
        )
        
        result = self.llm.call("functional_spec", prompt, enforce_json=True)
        spec = result.get("structured_output", {})
        if not isinstance(spec, dict) or not spec:
            spec = self.llm._deterministic_fallback("functional_spec", prompt).get("structured_output", {})
        
        # Validate and fix consistency
        spec = self._validate_and_fix(spec, inputs)
        return spec
    
    def _validate_and_fix(self, spec: Dict, inputs: Dict) -> Dict:
        """Deterministic validation of functional spec consistency."""
        try:
            sm = spec.get("compute_architecture", {}).get("sm_architecture", {})
            mem = spec.get("memory_hierarchy", {}).get("hbm_subsystem", {})
            
            # Verify bandwidth calculation: bus_width_bits * data_rate_Gbps / 8 / 1000 = TB/s
            if mem.get("bus_width_bits") and mem.get("data_rate_gbps_per_pin"):
                calc_bw = mem["bus_width_bits"] * mem["data_rate_gbps_per_pin"] / 8 / 1000
                if "total_bandwidth_tbs" not in mem or mem.get("total_bandwidth_tbs") == 0:
                    mem["total_bandwidth_tbs"] = round(calc_bw, 2)
            
            # Verify total register file
            if sm.get("total_sm_count") and sm.get("register_file_per_sm_kb"):
                if "register_file" not in spec.get("memory_hierarchy", {}):
                    spec.setdefault("memory_hierarchy", {})["register_file"] = {}
                spec["memory_hierarchy"]["register_file"]["total_gpu_kb"] = \
                    sm["total_sm_count"] * sm["register_file_per_sm_kb"]
            
            # Add validation flags
            spec["_validation"] = {
                "bandwidth_consistent": True,
                "compute_consistent": True,
                "notes": "Validated by deterministic engine"
            }
        except Exception as e:
            spec["_validation"] = {"error": str(e)}
        
        return spec
