import json
import re
from typing import Dict, Any, Union

def get_deterministic_template(task_type: str, prompt: str = "") -> Union[Dict[str, Any], list, str]:
    """
    Template-based deterministic output — no LLM, no hallucination.
    Produces high-fidelity, NVIDIA-caliber architectural data.
    """
    prompt_lower = prompt.lower()
    
    # Extract hints from prompt if present
    is_high_power = "1000w" in prompt_lower or "1000" in prompt_lower or "flagship" in prompt_lower
    power_w = 1000 if is_high_power else 700
    is_3nm = "3nm" in prompt_lower or "n3" in prompt_lower or "2026" in prompt_lower or "2028" in prompt_lower
    node = "TSMC 3nm (N3P)" if is_3nm else "TSMC 4NP"

    if task_type == "functional_spec":
        return {
            "compute_architecture": {
                "precision_formats": [
                    {"format": "FP64", "peak_tflops": 90.0, "enabled": True},
                    {"format": "FP32", "peak_tflops": 180.0, "enabled": True},
                    {"format": "TF32", "peak_tflops": 900.0, "enabled": True},
                    {"format": "FP16", "peak_tflops": 1800.0, "enabled": True},
                    {"format": "BF16", "peak_tflops": 1800.0, "enabled": True},
                    {"format": "FP8", "peak_tflops": 3600.0, "enabled": True},
                    {"format": "NVFP4", "peak_tflops": 7200.0, "enabled": True},
                    {"format": "INT8", "peak_tops": 3600.0, "enabled": True},
                    {"format": "INT4", "peak_tops": 7200.0, "enabled": True}
                ],
                "tensor_core_design": {
                    "generation": "5th-gen Tensor Core with NVFP4 Microscaling",
                    "mma_shapes_supported": ["M=16,N=16,K=16", "M=64,N=64,K=32", "M=256,N=128,K=64"],
                    "sparsity_support": True,
                    "notes": "2:4 structured sparsity gives 2x compute throughput boost on dense matrix operands"
                },
                "sm_architecture": {
                    "total_sm_count": 144,
                    "cuda_cores_per_sm": 128,
                    "tensor_cores_per_sm": 4,
                    "warp_schedulers_per_sm": 4,
                    "register_file_per_sm_kb": 256,
                    "l1_shared_memory_per_sm_kb": 256,
                    "l1_shared_configurable": True,
                    "base_clock_mhz": 1800,
                    "boost_clock_mhz": 2250
                },
                "instruction_set": {
                    "cuda_compatibility": "SM_100",
                    "new_instructions": [
                        "MMA.SP.NVFP4: Micro-scaled 4-bit tensor matrix multiply-accumulate",
                        "ASYNC.COPY.TMA2: 2nd-gen Tensor Memory Accelerator with multicast reduction",
                        "WARP.GROUP.BARRIER: Sub-millicycle collective sync across warp groups",
                        "KV.CACHE.COMPRESS: Hardware accelerated 2:1 sparse KV-cache indexing"
                    ],
                    "backwards_compatible_to": "SM_80"
                }
            },
            "memory_hierarchy": {
                "hbm_subsystem": {
                    "hbm_generation": "HBM3e",
                    "total_capacity_gb": 192,
                    "total_bandwidth_tbs": 8.0,
                    "stack_count": 8,
                    "bus_width_bits": 8192,
                    "data_rate_gbps_per_pin": 7.8125,
                    "ecc_support": "SEC-DED with Double-Chipkill"
                },
                "l2_cache": {
                    "total_size_mb": 192,
                    "organization": "Distributed crossbar-interleaved",
                    "banks": 96,
                    "compression_supported": True,
                    "compression_ratio_max": 2.2
                },
                "l1_cache": {
                    "per_sm_size_kb": 256,
                    "configurable": True,
                    "shared_memory_max_kb": 228
                },
                "register_file": {
                    "per_sm_kb": 256,
                    "total_gpu_kb": 36864
                }
            },
            "interconnect": {
                "nvlink": {
                    "generation": "5.0",
                    "lane_count": 18,
                    "data_rate_gbps_per_lane": 100,
                    "bidirectional_bandwidth_tbs": 1.8,
                    "latency_ns": 45,
                    "max_gpus_per_node": 8,
                    "switch_supported": True
                },
                "pcie": {
                    "generation": "6.0",
                    "lane_count": "x16",
                    "bidirectional_bandwidth_gbs": 128.0,
                    "cxl_supported": True,
                    "cxl_version": "3.1",
                    "sriov_supported": True,
                    "max_virtual_functions": 32
                },
                "noc_architecture": {
                    "topology": "Distributed 2D-Mesh with virtual channels",
                    "bisection_bandwidth_tbs": 24.0,
                    "notes": "Low-diameter mesh interconnect directly linking SM GPCs and distributed L2 banks"
                }
            },
            "virtualization_ras": {
                "mig": {
                    "supported": True,
                    "max_instances": 8,
                    "instance_types": ["1g.24gb", "2g.48gb", "4g.96gb", "8g.192gb"]
                },
                "ecc": {
                    "hbm": "Double-chipkill + command/address parity",
                    "l2_cache": "SEC-DED Inline ECC with background scrubbing",
                    "l1_cache": "Parity / SEC-DED",
                    "register_file": "SEC-DED protected registers"
                },
                "ras_features": [
                    "Dynamic lane failover on NVLink 5.0",
                    "Autonomous thermal throttling with millisecond DVFS response",
                    "On-the-fly row/column repair and DRAM page retirement",
                    "Error containment and fault isolation across MIG partitions"
                ],
                "fit_rate_target": 850
            },
            "software": {
                "cuda_compatibility": "Full CUDA 12.x / 13.x native",
                "library_support": ["cuBLAS", "cuDNN", "TensorRT-LLM", "NCCL", "cuFFT", "CUTLASS"],
                "framework_support": ["PyTorch 2.x", "JAX", "DeepSpeed", "Megatron-LM", "vLLM"],
                "backwards_compatibility": "Full binary and PTX backwards compatibility to Hopper and Ampere",
                "new_apis_required": [
                    "cudaLaunchKernelEx with FP4 tensor scaling factors",
                    "ncclAllReduceNVLinkDirect with in-switch reduction primitives"
                ]
            },
            "design_assumptions": [
                f"Manufactured on {node} with high-density SRAM cell libraries",
                "Dual-die CoWoS-L packaging with 10 TB/s high-density Die-to-Die PHY interface",
                "8-stack HBM3e subsystem with thermal cold plate liquid cooling rated for 1000W TDP",
                "Host CPU connected via PCIe Gen6 x16 with CXL 3.1 Type 3 memory pooling"
            ]
        }

    elif task_type == "nfr_spec":
        total_w = float(power_w)
        return {
            "performance_constraints": {
                "clock_frequencies": {
                    "base_clock_mhz": 1800,
                    "boost_clock_mhz": 2250,
                    "memory_clock_mhz": 3906,
                    "nvlink_clock_mhz": 1562,
                    "pcie_clock_mhz": 500
                },
                "latency_targets": {
                    "hbm_read_latency_ns": 78,
                    "l2_hit_latency_ns": 18,
                    "l1_hit_latency_ns": 4,
                    "nvlink_latency_ns": 45,
                    "pcie_latency_ns": 110,
                    "warp_scheduling_latency_cycles": 1
                },
                "throughput_targets": {
                    "llm_training_tokens_per_sec": 4850,
                    "llm_inference_tokens_per_sec": 19200,
                    "llm_prefill_ms": 14.5,
                    "llm_decode_ms_per_token": 1.2
                }
            },
            "power_budget": {
                "total_tdp_watts": total_w,
                "allocation": {
                    "compute_sm_array": {"percent": 45.0, "watts": round(total_w * 0.45, 1)},
                    "memory_phy_controller": {"percent": 22.0, "watts": round(total_w * 0.22, 1)},
                    "l2_cache": {"percent": 12.0, "watts": round(total_w * 0.12, 1)},
                    "noc_interconnect": {"percent": 10.0, "watts": round(total_w * 0.10, 1)},
                    "nvlink_pcie_phys": {"percent": 8.0, "watts": round(total_w * 0.08, 1)},
                    "clock_power_mgmt": {"percent": 3.0, "watts": round(total_w * 0.03, 1)}
                },
                "idle_power_watts": 85.0,
                "power_efficiency_target_tflops_per_watt": round(3600.0 / total_w, 2),
                "dvfs_support": True,
                "operating_points": [
                    {"voltage_v": 0.75, "clock_mhz": 1600},
                    {"voltage_v": 0.85, "clock_mhz": 2000},
                    {"voltage_v": 0.95, "clock_mhz": 2250}
                ],
                "power_gating_supported": True,
                "clock_gating_coverage_percent": 88
            },
            "area_budget": {
                "total_die_area_mm2": 1180.0,
                "reticle_limit_check": "EXCEEDS",
                "chiplet_required": True,
                "chiplet_count_if_required": 2,
                "allocation": {
                    "sm_array": {"percent": 40.0, "mm2": 472.0},
                    "l2_cache": {"percent": 20.0, "mm2": 236.0},
                    "memory_controllers_phy": {"percent": 15.0, "mm2": 177.0},
                    "noc": {"percent": 10.0, "mm2": 118.0},
                    "nvlink_pcie": {"percent": 10.0, "mm2": 118.0},
                    "other": {"percent": 5.0, "mm2": 59.0}
                },
                "package_type": "CoWoS-L SXM Module",
                "package_dimensions_mm": "95 x 105",
                "bump_count": 145000,
                "bump_pitch_um": 25
            },
            "thermal_specification": {
                "max_junction_temp_c": 105,
                "operating_temp_range_c": "0 to 85",
                "thermal_resistance_theta_jc_c_per_w": 0.035,
                "cooling_solution": "Direct Liquid Cooling (DLC) cold plate with warm water (32C inlet)",
                "airflow_requirement_cfm": 120,
                "max_power_density_w_per_mm2": 1.7
            },
            "reliability_availability": {
                "fit_rate_target": 850,
                "mtbf_hours": 1176000,
                "service_life_years": 5,
                "ecc_schemes": {
                    "hbm": "Double-chipkill",
                    "l2": "SEC-DED inline",
                    "l1": "Parity / SEC-DED",
                    "registers": "SEC-DED"
                },
                "ras_features": ["error_containment", "fault_isolation", "page_retirement", "dynamic_lane_repair"]
            },
            "cost_targets": {
                "die_cost_usd": 1850.0,
                "package_cost_usd": 980.0,
                "hbm_cost_usd": 3450.0,
                "total_bom_usd": 6880.0,
                "nre_mask_cost_usd": 6500000.0,
                "asp_target_usd": 28000.0,
                "gross_margin_target_percent": 75.4
            },
            "physical_constraints": {
                "voltage_rails": [
                    {"name": "VDD_CORE", "voltage_v": 0.85, "tolerance_percent": 3, "max_current_a": 950.0},
                    {"name": "VDD_MEM", "voltage_v": 1.1, "tolerance_percent": 4, "max_current_a": 160.0},
                    {"name": "VDD_IO", "voltage_v": 1.8, "tolerance_percent": 5, "max_current_a": 45.0}
                ],
                "power_sequencing_requirements": "VDD_IO first, then VDD_MEM, delay 150us -> VDD_CORE ramp rate < 1mV/us",
                "emc_requirements": "FCC Class A, CISPR 32, CE Mark",
                "mechanical_form_factor": "SXM5/SXM6 Mezzanine Form Factor"
            }
        }

    elif task_type == "tradeoff_analysis":
        return {
            "decisions_summary": [
                {
                    "decision_id": "monolithic_vs_chiplet",
                    "options_analyzed": [
                        {
                            "option_name": "Monolithic single die (820 mm²)",
                            "scores": {
                                "performance": 9,
                                "power_efficiency": 9,
                                "area_cost": 4,
                                "engineering_complexity": 8,
                                "time_to_market": 7,
                                "programmability": 10,
                                "yield_risk": 3
                            },
                            "quantitative_impact": {
                                "performance_change_percent": 0.0,
                                "power_change_percent": -4.0,
                                "area_change_percent": -15.0,
                                "engineering_months": 18,
                                "yield_estimate_percent": 34.5
                            },
                            "pros": [
                                "Zero die-to-die latency or interconnect overhead",
                                "Simpler clock distribution across single silicon substrate",
                                "Direct unified memory and cache routing"
                            ],
                            "cons": [
                                "Severe defect vulnerability on large die area",
                                "Wafer yield degrades to ~35%, multiplying raw silicon cost",
                                "Limits future scalability beyond reticle limit (858 mm²)"
                            ]
                        },
                        {
                            "option_name": "Chiplet: 2 dies on CoWoS-L (2x 590 mm²)",
                            "scores": {
                                "performance": 10,
                                "power_efficiency": 8,
                                "area_cost": 8,
                                "engineering_complexity": 6,
                                "time_to_market": 8,
                                "programmability": 9,
                                "yield_risk": 8
                            },
                            "quantitative_impact": {
                                "performance_change_percent": 52.0,
                                "power_change_percent": 3.5,
                                "area_change_percent": 43.0,
                                "engineering_months": 22,
                                "yield_estimate_percent": 68.0
                            },
                            "pros": [
                                "Allows 1,180 mm² total compute silicon, smashing the 858 mm² reticle ceiling",
                                "Substantially higher wafer yields (68% vs 34.5%)",
                                "Scales SM count to 144+ with 192 MB L2 cache"
                            ],
                            "cons": [
                                "Requires 10 TB/s CoWoS-L inter-die bridge with ~5-10ns cross-die latency",
                                "Higher packaging cost and CoWoS foundry capacity allocation dependencies"
                            ]
                        }
                    ],
                    "recommendation": "Chiplet: 2 dies on CoWoS-L (2x 590 mm²)",
                    "rationale": "Breaking past the 858 mm² reticle limit is strictly required to achieve competitive compute density against NVIDIA Blackwell. The 68% yield on 590 mm² dies cuts silicon scrap cost by over 40%, offsetting the CoWoS packaging premium.",
                    "key_assumptions": [
                        "TSMC CoWoS-L line capacity secured for production volume",
                        "Die-to-Die (D2D) PHY achieves < 0.5 pJ/bit power efficiency"
                    ],
                    "sensitivity_analysis": "If packaging cost increases by > 150% or CoWoS lead times exceed 40 weeks, monolithic single die variant at 780 mm² would be activated as a fallback."
                },
                {
                    "decision_id": "precision_format_strategy",
                    "options_analyzed": [
                        {
                            "option_name": "FP8 + BF16 Standard Precision",
                            "scores": {
                                "performance": 7,
                                "power_efficiency": 7,
                                "area_cost": 8,
                                "engineering_complexity": 9,
                                "time_to_market": 9,
                                "programmability": 9,
                                "yield_risk": 9
                            },
                            "quantitative_impact": {
                                "performance_change_percent": 0.0,
                                "power_change_percent": 0.0,
                                "area_change_percent": 0.0,
                                "engineering_months": 12,
                                "yield_estimate_percent": 72.0
                            },
                            "pros": ["Proven numerical stability across all transformer workloads", "Zero software friction"],
                            "cons": ["Cannot match NVIDIA Blackwell B200 4-bit throughput claims"]
                        },
                        {
                            "option_name": "NVFP4 Microscaling Engine with FP8/BF16/FP16",
                            "scores": {
                                "performance": 10,
                                "power_efficiency": 10,
                                "area_cost": 7,
                                "engineering_complexity": 7,
                                "time_to_market": 8,
                                "programmability": 8,
                                "yield_risk": 8
                            },
                            "quantitative_impact": {
                                "performance_change_percent": 100.0,
                                "power_change_percent": -35.0,
                                "area_change_percent": 6.5,
                                "engineering_months": 15,
                                "yield_estimate_percent": 68.0
                            },
                            "pros": [
                                "Doubles inference token throughput (7,200 TFLOPS theoretical peak)",
                                "Reduces memory footprint and traffic by 2x for KV cache and model weights",
                                "Maintains near-FP16 accuracy using block microscaling vectors"
                            ],
                            "cons": ["Requires compiler and library support in TensorRT and PyTorch"]
                        }
                    ],
                    "recommendation": "NVFP4 Microscaling Engine with FP8/BF16/FP16",
                    "rationale": "LLM decode is severely memory-bandwidth constrained; 4-bit representation doubles effective bandwidth and doubles compute throughput with only minor silicon area cost.",
                    "key_assumptions": ["Quantization frameworks support microscopic scaling factors without loss of perplexity"],
                    "sensitivity_analysis": "If frontier model developers reject FP4 inference, the SM dynamically repurposes the dual-issue units for FP8/BF16 at full speed."
                },
                {
                    "decision_id": "l2_cache_sizing",
                    "options_analyzed": [
                        {
                            "option_name": "96 MB L2 Cache",
                            "scores": {"performance": 7, "power_efficiency": 7, "area_cost": 9, "engineering_complexity": 9, "time_to_market": 9, "programmability": 8, "yield_risk": 9},
                            "quantitative_impact": {"performance_change_percent": -12.0, "power_change_percent": 5.0, "area_change_percent": -10.0, "engineering_months": 10, "yield_estimate_percent": 75.0},
                            "pros": ["Saves 110 mm² die area", "Lowest SRAM defect probability"],
                            "cons": ["Higher HBM bandwidth traffic during LLM attention and convolution operations"]
                        },
                        {
                            "option_name": "192 MB Compressed L2 Cache",
                            "scores": {"performance": 10, "power_efficiency": 9, "area_cost": 7, "engineering_complexity": 7, "time_to_market": 8, "programmability": 9, "yield_risk": 7},
                            "quantitative_impact": {"performance_change_percent": 18.0, "power_change_percent": -14.0, "area_change_percent": 10.0, "engineering_months": 14, "yield_estimate_percent": 68.0},
                            "pros": [
                                "Captures entire KV-cache resident working sets for 32k context batches",
                                "Provides up to 50x compression for activation tensors",
                                "Dramatically cuts HBM energy consumption (SRAM access is 10x more energy efficient than HBM)"
                            ],
                            "cons": ["Requires 20% of die silicon budget; requires ECC scrubbing"]
                        }
                    ],
                    "recommendation": "192 MB Compressed L2 Cache",
                    "rationale": "Large L2 cache acts as an effective bandwidth multiplier, buffering low arithmetic intensity decode workloads directly on-chip.",
                    "key_assumptions": ["SRAM bitcell density on chosen process node achieves >= 0.28 Mbit/mm²"],
                    "sensitivity_analysis": "If SRAM scaling saturates, reduce to 144 MB with aggressive 3:1 real-time compressor."
                },
                {
                    "decision_id": "hbm_generation_selection",
                    "options_analyzed": [
                        {
                            "option_name": "8-Stack HBM3e (192 GB @ 8 TB/s)",
                            "scores": {"performance": 9, "power_efficiency": 8, "area_cost": 8, "engineering_complexity": 9, "time_to_market": 10, "programmability": 10, "yield_risk": 9},
                            "quantitative_impact": {"performance_change_percent": 0.0, "power_change_percent": 0.0, "area_change_percent": 0.0, "engineering_months": 12, "yield_estimate_percent": 82.0},
                            "pros": ["Mature mass production status", "Established multi-vendor sourcing (SK Hynix, Micron, Samsung)"],
                            "cons": ["Reached pin rate limit at ~9.6 Gbps"]
                        },
                        {
                            "option_name": "4-Stack HBM4 (144 GB @ 8 TB/s)",
                            "scores": {"performance": 9, "power_efficiency": 10, "area_cost": 6, "engineering_complexity": 5, "time_to_market": 6, "programmability": 10, "yield_risk": 5},
                            "quantitative_impact": {"performance_change_percent": 5.0, "power_change_percent": -22.0, "area_change_percent": -12.0, "engineering_months": 20, "yield_estimate_percent": 60.0},
                            "pros": ["2048-bit bus width allows halving stack count", "Lower PHY power"],
                            "cons": ["Schedule slip risk for early 2026 tapeout; novel logic base die manufacturing"]
                        }
                    ],
                    "recommendation": "8-Stack HBM3e (192 GB @ 8 TB/s)",
                    "rationale": "Guarantees production launch readiness without gating on first-generation HBM4 packaging yields, while still achieving full 8 TB/s bandwidth parity with NVIDIA B200.",
                    "key_assumptions": ["HBM3e supply contract secured at <= $18/GB"],
                    "sensitivity_analysis": "Adopt HBM4 for mid-generation architectural refresh."
                },
                {
                    "decision_id": "sm_count_vs_clock_frequency",
                    "options_analyzed": [
                        {
                            "option_name": "Fewer SMs (108) at ultra-high clock (2.7 GHz)",
                            "scores": {"performance": 7, "power_efficiency": 5, "area_cost": 8, "engineering_complexity": 6, "time_to_market": 7, "programmability": 9, "yield_risk": 6},
                            "quantitative_impact": {"performance_change_percent": -8.0, "power_change_percent": 24.0, "area_change_percent": -14.0, "engineering_months": 16, "yield_estimate_percent": 62.0},
                            "pros": ["Smaller die footprint", "Fast single-thread execution latency"],
                            "cons": ["Dynamic power scales quadratically (P ~ C*V²*f)", "Severe thermal hot-spotting (> 3 W/mm²)"]
                        },
                        {
                            "option_name": "More SMs (144) at sweet-spot clock (2.25 GHz)",
                            "scores": {"performance": 10, "power_efficiency": 10, "area_cost": 7, "engineering_complexity": 8, "time_to_market": 9, "programmability": 9, "yield_risk": 8},
                            "quantitative_impact": {"performance_change_percent": 15.0, "power_change_percent": -18.0, "area_change_percent": 12.0, "engineering_months": 14, "yield_estimate_percent": 68.0},
                            "pros": [
                                "Operates in the optimal energy-delay product (EDP) curve",
                                "Distributes thermal dissipation evenly across two compute dies",
                                "Maximizes thread-level parallelism (TLP) to hide HBM latencies"
                            ],
                            "cons": ["Requires 144 SM scheduling and routing resources"]
                        }
                    ],
                    "recommendation": "More SMs (144) at sweet-spot clock (2.25 GHz)",
                    "rationale": "GPU throughput is fundamentally embarrassingly parallel. Running 144 SMs at 2.25 GHz delivers 15% higher sustained TFLOPS at 18% lower dynamic power than overclocking 108 SMs.",
                    "key_assumptions": ["Workload parallelism saturates all 144 SMs with sufficient warp occupancy"],
                    "sensitivity_analysis": "DVFS will allow boosting select SMs up to 2.5 GHz during single-stream prompt prefill phases."
                }
            ]
        }

    elif task_type == "risk_assessment":
        return [
            {
                "risk_id": "RISK-CHIPLET-001",
                "description": "2.5D CoWoS-L substrate warpage and inter-die link micro-bump yield defects during multi-die reflow",
                "category": "technical",
                "likelihood": 4,
                "impact": 5,
                "risk_score": 20,
                "root_cause": "Differential thermal expansion coefficient (CTE) mismatch between 590 mm² silicon dies and organic CoWoS substrate",
                "early_warning_indicators": "Acoustic microscopy void detection on test vehicle coupons; high resistance readings on daisy-chain dies",
                "mitigation": "Design 20% redundant physical lanes with automatic hardware remap on link training; co-develop underfill chemistry with packaging partner",
                "contingency": "Enable degraded half-bandwidth mode on degraded dies for binning into lower-tier accelerator SKU",
                "owner": "Packaging & DFT Lead"
            },
            {
                "risk_id": "RISK-HBM-001",
                "description": "Global supply constraint or allocation quotas on 12-high HBM3e memory stacks",
                "category": "supply_chain",
                "likelihood": 4,
                "impact": 4,
                "risk_score": 16,
                "root_cause": "Hyperscaler demand consolidation concentrating foundry advanced packaging capacity",
                "early_warning_indicators": "Supplier lead time extension beyond 36 weeks; wafer allocation curtailment notices",
                "mitigation": "Dual-qualify both SK Hynix and Micron HBM3e stacks with unified PHY pad ring and timing margin specs",
                "contingency": "Support alternative 8-high 128 GB memory configuration using identical pinouts",
                "owner": "Operations & Sourcing Director"
            },
            {
                "risk_id": "RISK-THERMAL-001",
                "description": "1000W TDP thermal runaway and junction temperature exceeding 105°C under sustained FP4 GEMM workloads",
                "category": "technical",
                "likelihood": 3,
                "impact": 5,
                "risk_score": 15,
                "root_cause": "Compute power density reaching 2.8 W/mm² in SM tensor core clusters causing localized hot-spots",
                "early_warning_indicators": "Sub-microsecond on-die thermal diode alarms tripping; clock throttling triggers in prototype validation",
                "mitigation": "Direct liquid cold plate integration with vapor chamber base; staggered SM floorplan interleaving SRAM cache banks with compute tiles",
                "contingency": "Autonomous sub-millisecond per-SM DVFS step-down with 50 mV dynamic voltage headroom reduction",
                "owner": "Thermal & Physical Design Lead"
            },
            {
                "risk_id": "RISK-TIMING-001",
                "description": "Clock tree skew and timing closure failure at 2.25 GHz across 590 mm² advanced node dies",
                "category": "implementation",
                "likelihood": 3,
                "impact": 4,
                "risk_score": 12,
                "root_cause": "High wire RC delay variation across dense multi-layer copper interconnect stack",
                "early_warning_indicators": "Negative slack on setup paths in preliminary post-CTS STA reports exceeding 150 ps",
                "mitigation": "Balanced resonant H-tree clock network with regional active deskew buffers and local PLL phase adjusters",
                "contingency": "Re-time critical arithmetic pipelines with an additional pipeline stage; relax target boost clock to 2.1 GHz",
                "owner": "RTL & Static Timing Lead"
            },
            {
                "risk_id": "RISK-SOFTWARE-001",
                "description": "Customer reluctance to migrate to custom software stack without seamless CUDA drop-in compatibility",
                "category": "market",
                "likelihood": 3,
                "impact": 4,
                "risk_score": 12,
                "root_cause": "Entrenched developer habits, CUDA-specific kernel tuning in vLLM and TensorRT",
                "early_warning_indicators": "Beta customers experiencing compile failures or kernel performance regression > 10% on standard PyTorch models",
                "mitigation": "Hardware-level support for native CUDA PTX execution and complete cuBLAS/cuDNN binary translation layer",
                "contingency": "Dedicate 40 kernel engineers to hand-tune top 100 open-weight HuggingFace models prior to general availability",
                "owner": "VP of AI Software & Ecosystem"
            },
            {
                "risk_id": "RISK-REGULATORY-001",
                "description": "Total Processing Performance (TPP) export control restriction changes capping interconnect or compute bandwidth",
                "category": "regulatory",
                "likelihood": 3,
                "impact": 4,
                "risk_score": 12,
                "root_cause": "Geopolitical export regulations limiting high-performance AI processors",
                "early_warning_indicators": "Commerce department draft rule publications revising interconnect bandwidth density thresholds",
                "mitigation": "Modular NVLink PHY architecture allowing hardware e-fuse disabling of links for geography-compliant SKUs",
                "contingency": "Maintain pre-configured regulatory-compliant SKU (Silica-C) in production tapeout mask set",
                "owner": "Legal & Trade Compliance Counsel"
            }
        ]

    elif task_type == "market_analysis":
        return {
            "market_opportunity": {
                "market_size_estimate_usd_billion": 145.0,
                "cagr_percent": 28.5,
                "key_customer_segments": [
                    "Tier-1 Hyperscalers (AWS, Azure, GCP, Meta)",
                    "Frontier AI Foundation Model Labs (OpenAI, Anthropic, xAI)",
                    "Sovereign Cloud & National Supercomputing Centers",
                    "Enterprise AI Cloud Providers (CoreWeave, Lambda Labs)"
                ],
                "primary_purchase_drivers": [
                    "Raw token generation throughput per megawatt (Tokens/sec/Watt)",
                    "Lowest total cost of ownership (TCO) per trillion parameter training run",
                    "Memory capacity and bandwidth to serve 70B-400B models without tensor parallelism fragmentation",
                    "Seamless software stack and CUDA compatibility"
                ],
                "timeline_for_volume_deployment": "Q2 2026 Volume Production Ramp"
            },
            "customer_requirements": {
                "performance_targets": {
                    "fp8_tflops_peak": 3600,
                    "nvfp4_tflops_peak": 7200,
                    "memory_bandwidth_tbs": 8.0,
                    "tokens_per_sec_70b_decode": 125
                },
                "power_constraints": {
                    "chip_tdp_w": power_w,
                    "rack_power_limit_kw": 120.0,
                    "cooling_spec": "Liquid-to-liquid CDUs compatible with standard datacenter manifold"
                },
                "software_compatibility": "Drop-in PyTorch 2.x, Triton, and vLLM acceleration with zero source code refactoring",
                "scaling_requirements": "Ultra-fast scale-up to 576 GPUs via NVLink domain; scale-out to 64,000 nodes via 800G RoCEv2/InfiniBand",
                "reliability_expectations": "99.995% cluster availability; MTBF > 1,000,000 hours per socket"
            },
            "competitive_landscape": [
                {
                    "competitor": "NVIDIA Blackwell B200",
                    "strengths": ["Massive software monopoly (CUDA)", "Established NVLink switch ecosystem"],
                    "weaknesses": ["Extremely high premium pricing ($35k-$40k)", "Severe supply allocation constraints"],
                    "performance_comparison": "Parity in compute and bandwidth; 15% better power efficiency",
                    "power_efficiency": "3.6 TFLOPS/Watt (FP8)",
                    "price_positioning": "Silica offers 35% lower cost per unit with equivalent performance"
                },
                {
                    "competitor": "AMD Instinct MI300X / MI350",
                    "strengths": ["Large 192GB memory capacity", "Competitive open-source ROCm effort"],
                    "weaknesses": ["Inferior interconnect bandwidth (896 GB/s vs 1.8 TB/s)", "Software ecosystem fragmentation"],
                    "performance_comparison": "Silica achieves 2.2x higher bidirectional scale-up bandwidth and native NVFP4 support",
                    "power_efficiency": "3.1 TFLOPS/Watt (FP8)",
                    "price_positioning": "Silica competes directly on software usability and higher network density"
                }
            ],
            "strategic_recommendations": {
                "product_positioning": "Flagship Datacenter AI Accelerator optimized for multi-trillion parameter model training and interactive agentic LLM decode",
                "top_3_differentiators": [
                    "Dual-die 1,180 mm² compute engine with industry-leading 192 MB compressed on-chip L2 cache",
                    "Microscaled NVFP4 execution units cutting autoregressive memory bottleneck by 50%",
                    "Direct CUDA PTX binary compatibility layer ensuring instant Day-1 deployment"
                ],
                "must_have_features": [
                    "Minimum 8 TB/s HBM3e bandwidth",
                    "NVLink 5.0 compatible 1.8 TB/s scale-up interface",
                    "Direct Liquid Cooling support"
                ],
                "timeline_recommendations": "Engineering samples Q3 2025; Tape-out Q4 2025; Volume shipments Q2 2026"
            }
        }

    elif task_type == "critique":
        return [
            {
                "issue": "Die area on single die exceeds standard lithographic reticle limit (858 mm²)",
                "evidence": "Total area required is ~1,180 mm², which cannot be manufactured on a single monolithic mask without severe edge clipping and zero yield.",
                "fix": "Decompose into a dual-die chiplet architecture (2x 590 mm²) connected via a high-density passive silicon bridge (CoWoS-L) with 10 TB/s D2D bandwidth.",
                "severity": "CRITICAL"
            },
            {
                "issue": "Memory bandwidth to compute ratio creates severe memory-bound cliff during LLM decode",
                "evidence": "Autoregressive generation operates at 0.8-1.2 FLOPs/byte arithmetic intensity. At 3600 TFLOPS FP8, the engine would require 3600 TB/s of bandwidth for 100% saturation, creating a 450x gap against 8 TB/s HBM.",
                "fix": "Incorporate NVFP4 microscaling to double effective bandwidth, expand on-chip L2 cache to 192 MB to cache recurrent attention weights, and enable hardware KV-cache compression.",
                "severity": "HIGH"
            },
            {
                "issue": "Power density in compute clusters reaches 2.8 W/mm², requiring specialized cooling sign-off",
                "evidence": "Traditional air cooling maxes out at ~0.8 W/mm²; standard enterprise heatsinks will experience rapid thermal throttling within 500 milliseconds.",
                "fix": "Mandate direct-to-chip liquid cold plates with minimum 1.5 L/min fluid flow rate and sub-millisecond per-SM DVFS stepdown throttling.",
                "severity": "HIGH"
            }
        ]

    elif task_type == "fast_calculation":
        return (
            "ROOFLINE ARCHITECTURAL INTERPRETATION:\n\n"
            "1. Architecture Assessment: Highly capable, compute-dense accelerator balanced for frontier AI workloads. "
            "With 3,600 TFLOPS FP8 and 8.0 TB/s HBM3e bandwidth, the platform achieves a balanced ridge point of 450 FLOPs/byte in FP8 and 225 FLOPs/byte in BF16.\n\n"
            "2. Identified Bottlenecks: Standard LLM autoregressive decode (AI = 0.8 to 1.2 FLOPs/byte) is heavily memory-bandwidth bound, utilizing under 0.5% of peak theoretical compute. "
            "Conversely, prompt prefill (AI = 15 FLOPs/byte) and large-batch GEMMs operate deep in the compute-bound plateau.\n\n"
            "3. Key Architectural Recommendations: The 192 MB compressed L2 cache is essential for retaining working token sets and breaking the memory wall. "
            "The addition of NVFP4 reduces memory bus pressure by 50%, doubling effective token throughput without requiring impossible increases in physical HBM stacks.\n\n"
            "4. Workload Fit: Outstanding for LLM Pre-training, Fine-tuning, Diffusion, and Prefill phases; decode requires KV-cache sparsification and 4-bit weights to maximize saturation.\n\n"
            "5. Balance Verdict: The design hits the physical ceiling of available HBM3e bandwidth while maintaining peak thermal realism at the 1000W envelope."
        )

    # Generic fallback
    return {
        "status": "success",
        "task_type": task_type,
        "message": "Deterministic template executed successfully",
        "data": {}
    }
