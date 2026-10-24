"""
Agent 1: Functional Specification Generator.
Generates compute architecture, memory hierarchy, interconnect, and instruction set specs.
Passes all outputs through SpecValidator for deterministic correctness.
"""
import json
from typing import Dict, Any, Optional
from product_architect.validators import SpecValidator
from product_architect.llm_backend import LLMBackend
from product_architect.knowledge_base import KnowledgeBase
from product_architect.templates import get_functional_spec_template

PROMPT = """You are a Principal NVIDIA GPU Architect. Generate a COMPLETE, QUANTIFIED functional specification.
Every claim must have a NUMBER. Be realistic for {process_node}.

Domain Knowledge Context:
{context}

Product Brief: {product_brief}
Target Market: {target_market}
Target Workloads: {workloads}
Power Budget: {power_budget}W
Process Node: {process_node}

Output this EXACT JSON structure:
{{
  "compute_architecture": {{
    "precision_formats": [
      {{"format": "FP64", "peak_tflops": 90.0, "enabled": true}},
      {{"format": "FP32", "peak_tflops": 180.0, "enabled": true}},
      {{"format": "TF32", "peak_tflops": 900.0, "enabled": true}},
      {{"format": "FP16", "peak_tflops": 1800.0, "enabled": true}},
      {{"format": "BF16", "peak_tflops": 1800.0, "enabled": true}},
      {{"format": "FP8", "peak_tflops": 3600.0, "enabled": true}},
      {{"format": "NVFP4", "peak_tflops": 7200.0, "enabled": true}},
      {{"format": "INT8", "peak_tops": 3600.0, "enabled": true}},
      {{"format": "INT4", "peak_tops": 7200.0, "enabled": true}}
    ],
    "tensor_core_design": {{
      "generation": "5th-gen Tensor Core",
      "mma_shapes_supported": ["M=16,N=16,K=16", "M=256,N=128,K=64"],
      "sparsity_support": true,
      "design_rationale": "Microscaling format NVFP4 with 2:4 structured sparsity gives 2x throughput boost."
    }},
    "sm_architecture": {{
      "total_sm_count": 148,
      "cuda_cores_per_sm": 128,
      "tensor_cores_per_sm": 4,
      "warp_schedulers_per_sm": 4,
      "register_file_per_sm_kb": 256,
      "l1_shared_memory_per_sm_kb": 256,
      "l1_shared_configurable": true,
      "base_clock_mhz": 1800,
      "boost_clock_mhz": 2100
    }},
    "instruction_set": {{
      "cuda_compatibility": "SM_100",
      "new_instructions": [
        "MMA.SP.NVFP4: Micro-scaled 4-bit tensor matrix multiply-accumulate",
        "ASYNC.COPY.TMA2: 2nd-gen Tensor Memory Accelerator with multicast reduction",
        "WARP.GROUP.BARRIER: Sub-millicycle collective sync across warp groups"
      ],
      "backwards_compatible_to": "SM_90"
    }}
  }},
  "memory_hierarchy": {{
    "hbm_subsystem": {{
      "hbm_generation": "HBM3e",
      "total_capacity_gb": 192,
      "total_bandwidth_tbs": 8.0,
      "stack_count": 8,
      "bus_width_bits": 8192,
      "data_rate_gbps_per_pin": 7.8125,
      "ecc_scheme": "SEC-DED / Double-chipkill"
    }},
    "l2_cache": {{
      "total_size_mb": 192,
      "organization": "distributed crossbar",
      "banks": 96,
      "compression_supported": true,
      "compression_ratio_max": 2.2
    }},
    "register_file": {{
      "per_sm_kb": 256,
      "total_gpu_kb": 37888
    }}
  }},
  "interconnect": {{
    "nvlink": {{
      "generation": "5.0",
      "lane_count": 18,
      "data_rate_gbps_per_lane": 100,
      "bidirectional_bandwidth_tbs": 1.8,
      "latency_ns": 45,
      "max_gpus_per_node": 8,
      "switch_supported": true
    }},
    "pcie": {{
      "generation": "6.0",
      "lane_count": "x16",
      "bidirectional_bandwidth_gbs": 128.0,
      "cxl_supported": true,
      "cxl_version": "3.1",
      "sriov_supported": true,
      "max_virtual_functions": 32
    }},
    "noc_architecture": {{
      "topology": "distributed crossbar",
      "notes": "Low-latency multi-terabyte crossbar linking dual die partitions."
    }}
  }},
  "virtualization_ras": {{
    "mig": {{"supported": true, "max_instances": 8}},
    "ecc": {{
      "hbm": "Double-chipkill",
      "l2_cache": "Inline ECC SEC-DED",
      "l1_cache": "Parity protected",
      "register_file": "Parity protected"
    }},
    "ras_features": ["error_containment", "fault_isolation", "page_retirement"],
    "fit_rate_target": "< 2000 FIT"
  }},
  "software": {{
    "cuda_compatibility": "Full CUDA 12.x+",
    "library_support": ["cuBLAS", "cuDNN", "TensorRT", "NCCL", "cuFFT"],
    "framework_support": ["PyTorch", "TensorFlow", "JAX", "DeepSpeed"],
    "backwards_compatibility": "All existing CUDA apps run without recompilation",
    "new_apis_required": ["cudaNVFP4Microscaling", "cudaTMA2Reduction"]
  }},
  "design_assumptions": [
    "TSMC 4NP dual-die CoWoS-L packaging with NVLink-C2C interconnect",
    "HBM3e 24GB 12-high stacks"
  ],
  "architecture_rationale": "Optimized for dense matrix math and low-intensity autoregressive decode with large 192MB L2 cache and 8.0 TB/s HBM3e bandwidth."
}}
"""

class FunctionalSpecAgent:
    def __init__(self, llm: LLMBackend, kb: KnowledgeBase, validator: SpecValidator):
        self.llm = llm
        self.kb = kb
        self.validator = validator
    
    def run(self, inputs: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            f"GPU architecture compute memory HBM NVLink SM {inputs.get('process_node', 'TSMC 4nm')}",
            categories=["nvidia_architecture", "hbm_specs", "interface_standards", "process_node_data"]
        )
        
        prompt = PROMPT.format(
            context=context,
            product_brief=inputs.get("product_brief", "AI GPU"),
            target_market=inputs.get("target_market", "Datacenter"),
            workloads=", ".join(inputs.get("key_workloads", ["LLM training", "LLM inference"])),
            power_budget=inputs.get("power_budget_w", 1000),
            process_node=inputs.get("process_node", "TSMC 4nm"),
        )
        
        result = self.llm.call("functional_spec", prompt, enforce_json=True)
        spec = result.get("structured_output", {})
        
        if not isinstance(spec, dict) or not spec or "compute_architecture" not in spec:
            spec = get_functional_spec_template(inputs)
        
        # First-principles physical scaling based on user inputs
        pwr = float(inputs.get("power_budget_w", 1000) or 1000)
        node_str = str(inputs.get("process_node", "TSMC 3nm")).lower()
        is_3nm = "3nm" in node_str or "n3" in node_str or "2nm" in node_str
        brief_lower = inputs.get("product_brief", "").lower()
        is_blackwell = "blackwell" in brief_lower or "successor to hopper" in brief_lower or pwr >= 950
        
        sm = spec.setdefault("compute_architecture", {}).setdefault("sm_architecture", {})
        hbm = spec.setdefault("memory_hierarchy", {}).setdefault("hbm_subsystem", {})
        l2 = spec.setdefault("memory_hierarchy", {}).setdefault("l2_cache", {})
        nv = spec.setdefault("interconnect", {}).setdefault("nvlink", {})
        
        if is_blackwell:
            sm["total_sm_count"] = 148
            sm["boost_clock_mhz"] = 2100
            hbm["hbm_generation"] = "HBM3e"
            hbm["total_capacity_gb"] = 192
            hbm["stack_count"] = 8
            hbm["bus_width_bits"] = 8192
            hbm["data_rate_gbps_per_pin"] = 7.8125
            hbm["total_bandwidth_tbs"] = 8.0
            l2["total_size_mb"] = 192
            nv["generation"] = "5.0"
            nv["lane_count"] = 18
            nv["bidirectional_bandwidth_tbs"] = 1.8
        elif pwr >= 600:
            sm["total_sm_count"] = 108
            sm["boost_clock_mhz"] = 2000
            hbm["hbm_generation"] = "HBM3e"
            hbm["total_capacity_gb"] = 144
            hbm["stack_count"] = 6
            hbm["bus_width_bits"] = 6144
            hbm["data_rate_gbps_per_pin"] = 7.8125
            hbm["total_bandwidth_tbs"] = 6.0
            l2["total_size_mb"] = 128
            nv["generation"] = "5.0"
            nv["lane_count"] = 14
            nv["bidirectional_bandwidth_tbs"] = 1.4
        elif pwr >= 400:
            sm["total_sm_count"] = 72
            sm["boost_clock_mhz"] = 1900
            hbm["hbm_generation"] = "HBM3"
            hbm["total_capacity_gb"] = 96
            hbm["stack_count"] = 4
            hbm["bus_width_bits"] = 4096
            hbm["data_rate_gbps_per_pin"] = 6.4
            hbm["total_bandwidth_tbs"] = 3.28
            l2["total_size_mb"] = 64
            nv["generation"] = "4.0"
            nv["lane_count"] = 10
            nv["bidirectional_bandwidth_tbs"] = 1.0
        else:
            calc_sm = max(32, int(round((pwr * 0.52) / (3.2 if is_3nm else 3.8) / 4) * 4))
            sm["total_sm_count"] = calc_sm
            sm["boost_clock_mhz"] = 1800
            hbm["hbm_generation"] = "HBM3"
            hbm["total_capacity_gb"] = 48
            hbm["stack_count"] = 2
            hbm["bus_width_bits"] = 2048
            hbm["data_rate_gbps_per_pin"] = 6.4
            hbm["total_bandwidth_tbs"] = 1.64
            l2["total_size_mb"] = 48
            nv["generation"] = "4.0"
            nv["lane_count"] = 8
            nv["bidirectional_bandwidth_tbs"] = 0.8

        # Calculate exact precision formats from physical SM count and boost clock
        sm_count = sm.get("total_sm_count", 144)
        boost_mhz = sm.get("boost_clock_mhz", 2100)
        cuda_cores = sm_count * 128
        fp32_tf = round(cuda_cores * 2 * (boost_mhz / 1000) / 1000, 1)
        fp64_tf = round(fp32_tf * 0.5, 1)
        tf32_tf = round(fp32_tf * 5.0, 1)
        bf16_tf = round(fp32_tf * 10.0, 1)
        fp16_tf = bf16_tf
        fp8_tf = round(bf16_tf * 2.0, 1)
        nvfp4_tf = round(fp8_tf * 2.0, 1)
        
        spec["compute_architecture"]["precision_formats"] = [
            {"format": "FP64", "peak_tflops": fp64_tf, "enabled": True},
            {"format": "FP32", "peak_tflops": fp32_tf, "enabled": True},
            {"format": "TF32", "peak_tflops": tf32_tf, "enabled": True},
            {"format": "FP16", "peak_tflops": fp16_tf, "enabled": True},
            {"format": "BF16", "peak_tflops": bf16_tf, "enabled": True},
            {"format": "FP8", "peak_tflops": fp8_tf, "enabled": True},
            {"format": "NVFP4", "peak_tflops": nvfp4_tf, "enabled": True},
            {"format": "INT8", "peak_tops": fp8_tf, "enabled": True},
            {"format": "INT4", "peak_tops": nvfp4_tf, "enabled": True}
        ]
        
        # Deterministic validator pass
        spec, validation = self.validator.validate_functional_spec(spec)
        
        return {
            "spec": spec,
            "validation": validation.summary(),
            "model_used": result.get("model", "deterministic"),
            "provider": result.get("provider", "deterministic"),
            "latency_s": result.get("latency_s", 0),
        }
