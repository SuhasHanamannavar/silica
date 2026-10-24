"""
Deterministic validation engines. These are COMPUTERS, not LLMs.
They never hallucinate. They never get math wrong.
Every output from the LLM must pass through these.
"""
import math
from typing import Dict, Any, List, Tuple

class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.fixes_applied: List[str] = []
    
    def add_error(self, msg: str):
        self.errors.append(msg)
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
    
    def add_fix(self, msg: str):
        self.fixes_applied.append(msg)
    
    @property
    def ok(self) -> bool:
        return len(self.errors) == 0
    
    def summary(self) -> Dict:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixes_applied": self.fixes_applied,
            "severity": "CRITICAL" if len(self.errors) > 0 else ("WARNING" if len(self.warnings) > 0 else "CLEAN")
        }


class SpecValidator:
    """Validates and auto-fixes architectural specifications."""
    
    RETICLE_LIMIT_MM2 = 858.0  # Maximum single die size
    HBM_PIN_SPEEDS = {
        "HBM2": 2.4, "HBM2e": 3.6, "HBM3": 6.4, 
        "HBM3e": 8.0, "HBM4": 6.4  # HBM4 starts at 6.4, goes to 8.0+
    }
    
    def validate_functional_spec(self, spec: Dict) -> Tuple[Dict, ValidationResult]:
        """Validate functional spec, auto-fix where possible."""
        result = ValidationResult()
        spec = dict(spec)  # Shallow copy to modify
        
        # --- Memory bandwidth validation ---
        try:
            hbm = spec.get("memory_hierarchy", {}).get("hbm_subsystem", {})
            bus_width = hbm.get("bus_width_bits")
            data_rate = hbm.get("data_rate_gbps_per_pin")
            claimed_bw = hbm.get("total_bandwidth_tbs")
            
            if bus_width and data_rate:
                calculated_bw = round(bus_width * data_rate / 8 / 1000, 3)
                
                if claimed_bw is None:
                    hbm["total_bandwidth_tbs"] = calculated_bw
                    result.add_fix(f"Calculated HBM bandwidth: {calculated_bw} TB/s")
                elif abs(claimed_bw - calculated_bw) > 0.1:
                    result.add_warning(f"HBM bandwidth mismatch: claimed {claimed_bw} TB/s, calculated {calculated_bw} TB/s. Using calculated value.")
                    hbm["total_bandwidth_tbs"] = calculated_bw
                    result.add_fix(f"Corrected HBM bandwidth to {calculated_bw} TB/s")
        except Exception as e:
            result.add_error(f"Memory bandwidth validation error: {e}")
        
        # --- Compute consistency validation ---
        try:
            compute = spec.get("compute_architecture", {})
            sm = compute.get("sm_architecture", {})
            sm_count = sm.get("total_sm_count")
            boost_mhz = sm.get("boost_clock_mhz")
            
            if sm_count and boost_mhz:
                # Sanity check: typical 128 CUDA cores/SM * 2 (FMA) * clock * precision factor
                clock_ghz = boost_mhz / 1000
                fp32_estimate = sm_count * 128 * 2 * clock_ghz / 1000  # TFLOPS
                
                # Check claimed precision formats
                formats = compute.get("precision_formats", [])
                for fmt in formats:
                    pname = fmt.get("format", "")
                    claimed = fmt.get("peak_tflops", fmt.get("peak_tops"))
                    if claimed:
                        # Expected ratios relative to FP32
                        ratios = {
                            "FP64": 0.5, "FP32": 1.0, "TF32": 2.0, "FP16": 2.0, 
                            "BF16": 2.0, "FP8": 4.0, "NVFP4": 8.0, "INT8": 4.0, "INT4": 8.0
                        }
                        expected = fp32_estimate * ratios.get(pname.upper(), 1.0)
                        deviation = abs(claimed - expected) / expected if expected > 0 else 1
                        
                        if deviation > 0.5:  # Allow 50% tolerance for different SM designs
                            result.add_warning(f"{pname} peak looks off: claimed {claimed}, expected ~{expected:.1f} TFLOPS (±50%)")
        except Exception as e:
            result.add_error(f"Compute validation error: {e}")
        
        # --- Register file calculation ---
        try:
            mem = spec.get("memory_hierarchy", {}).get("register_file", {})
            sm = spec.get("compute_architecture", {}).get("sm_architecture", {})
            sm_count = sm.get("total_sm_count")
            per_sm_kb = sm.get("register_file_per_sm_kb", 256)
            if sm_count and per_sm_kb and not mem.get("total_gpu_kb"):
                mem["total_gpu_kb"] = sm_count * per_sm_kb
                result.add_fix(f"Calculated total register file: {mem['total_gpu_kb']} KB")
        except Exception:
            pass
        
        spec["_validation"] = result.summary()
        return spec, result
    
    def validate_nonfunctional_spec(self, spec: Dict) -> Tuple[Dict, ValidationResult]:
        """Validate NFR spec, ensure budgets sum correctly."""
        result = ValidationResult()
        spec = dict(spec)
        
        # --- Power budget summation ---
        try:
            power = spec.get("power_budget", {})
            total_tdp = power.get("total_tdp_watts", 0)
            alloc = power.get("allocation", {})
            
            pct_sum = 0
            watt_sum = 0
            for key, val in alloc.items():
                pct = val.get("percent", 0)
                pct_sum += pct
                
                # Calculate correct watts from percentage
                correct_watts = round(total_tdp * pct / 100, 1)
                if val.get("watts") != correct_watts:
                    val["watts"] = correct_watts
                    result.add_fix(f"Corrected {key} power: {correct_watts} W ({pct}%)")
                watt_sum += correct_watts
            
            if abs(pct_sum - 100) > 1:
                result.add_warning(f"Power percentages sum to {pct_sum}%, not 100%")
            if abs(watt_sum - total_tdp) > 1:
                result.add_warning(f"Power watts sum to {watt_sum}W, not {total_tdp}W")
        except Exception as e:
            result.add_error(f"Power budget validation error: {e}")
        
        # --- Area budget summation ---
        try:
            area = spec.get("area_budget", {})
            total_area = area.get("total_die_area_mm2", 0)
            alloc = area.get("allocation", {})
            
            pct_sum = 0
            mm2_sum = 0
            for key, val in alloc.items():
                pct = val.get("percent", 0)
                pct_sum += pct
                
                correct_mm2 = round(total_area * pct / 100, 1)
                if val.get("mm2") != correct_mm2:
                    val["mm2"] = correct_mm2
                    result.add_fix(f"Corrected {key} area: {correct_mm2} mm² ({pct}%)")
                mm2_sum += correct_mm2
            
            # Reticle limit check
            if total_area > self.RETICLE_LIMIT_MM2:
                area["reticle_limit_check"] = "EXCEEDS"
                area["chiplet_required"] = True
                result.add_warning(f"Die area {total_area} mm² EXCEEDS reticle limit ({self.RETICLE_LIMIT_MM2} mm²). Chiplet required.")
            else:
                area["reticle_limit_check"] = "WITHIN"
                if total_area > 800:
                    area["chiplet_required"] = True
                    result.add_warning(f"Die area {total_area} mm² near reticle limit — chiplet recommended for yield.")
                else:
                    area["chiplet_required"] = False
        except Exception as e:
            result.add_error(f"Area budget validation error: {e}")
        
        spec["_validation"] = result.summary()
        return spec, result
    
    def validate_roofline(self, peak_tflops: float, bandwidth_tbs: float, 
                         arithmetic_intensity: float) -> Dict:
        """Pure math roofline calculation. No LLM involved."""
        ridge_point = peak_tflops / bandwidth_tbs if bandwidth_tbs > 0 else float('inf')
        attainable = min(peak_tflops, bandwidth_tbs * arithmetic_intensity)
        bound_type = "memory_bound" if arithmetic_intensity < ridge_point else "compute_bound"
        utilization = attainable / peak_tflops * 100 if peak_tflops > 0 else 0
        
        return {
            "ridge_point_flops_per_byte": round(ridge_point, 2),
            "attainable_tflops": round(attainable, 2),
            "bound_type": bound_type,
            "peak_utilization_percent": round(utilization, 1),
            "bandwidth_needed_for_full_util_tbs": round(peak_tflops / arithmetic_intensity, 2) if arithmetic_intensity > 0 else float('inf'),
            "bandwidth_gap_tbs": round(max(0, peak_tflops / arithmetic_intensity - bandwidth_tbs), 2) if arithmetic_intensity > 0 else 0,
            "validated_by": "deterministic_engine"
        }
    
    def validate_die_cost(self, area_mm2: float, process_node: str = "TSMC 4nm") -> Dict:
        """Pure math die cost model."""
        node_params = {
            "TSMC 3nm": {"wafer_cost": 20000, "wafer_diameter_mm": 300, "defect_density_per_cm2": 0.22},
            "TSMC 4nm": {"wafer_cost": 16000, "wafer_diameter_mm": 300, "defect_density_per_cm2": 0.30},
            "TSMC 5nm": {"wafer_cost": 10000, "wafer_diameter_mm": 300, "defect_density_per_cm2": 0.35},
            "TSMC 7nm": {"wafer_cost": 6000, "wafer_diameter_mm": 300, "defect_density_per_cm2": 0.45},
        }
        params = node_params.get(process_node, node_params["TSMC 5nm"])
        
        wafer_r = params["wafer_diameter_mm"] / 2
        wafer_area_mm2 = math.pi * wafer_r * wafer_r
        
        # Gross dies per wafer (with 90% utilization)
        dies_per_wafer = int(wafer_area_mm2 / area_mm2 * 0.9)
        
        # Yield: simple negative exponential model
        area_cm2 = area_mm2 / 100
        yield_rate = math.exp(-params["defect_density_per_cm2"] * area_cm2)
        
        good_dies = dies_per_wafer * yield_rate
        die_cost = params["wafer_cost"] / good_dies if good_dies > 0 else float('inf')
        
        return {
            "process_node": process_node,
            "die_area_mm2": area_mm2,
            "wafer_cost_usd": params["wafer_cost"],
            "dies_per_wafer_gross": dies_per_wafer,
            "defect_density_per_cm2": params["defect_density_per_cm2"],
            "yield_rate_percent": round(yield_rate * 100, 2),
            "good_dies_per_wafer": round(good_dies, 1),
            "die_cost_usd": round(die_cost, 2),
            "reticle_check": "WITHIN" if area_mm2 <= 858 else "EXCEEDS — CHIPLET REQUIRED",
            "validated_by": "deterministic_engine"
        }
    
    def validate_interface_spec(self, spec: Dict) -> Tuple[Dict, ValidationResult]:
        """Validate interface specifications."""
        result = ValidationResult()
        spec = dict(spec)
        
        # PCIe bandwidth validation
        try:
            ext = spec.get("external_interfaces", {})
            pcie = ext.get("pcie", {})
            gen = pcie.get("generation", "5.0")
            lanes = pcie.get("lane_count", "x16")
            
            lane_counts = {"x1": 1, "x2": 2, "x4": 4, "x8": 8, "x16": 16}
            gen_rates = {"4.0": 16, "5.0": 32, "6.0": 64}  # GT/s per lane
            
            n_lanes = lane_counts.get(lanes, 16)
            rate = gen_rates.get(str(gen), 32)
            
            # PCIe uses 128b/130b encoding for gen 4/5, PAM4+FEC for gen 6
            # Rough effective bandwidth: ~0.97 of raw for gen 4/5, ~0.9 for gen 6
            efficiency = 0.9 if float(gen) >= 6.0 else 0.97
            raw_bw = n_lanes * rate / 8  # GB/s one direction
            effective_bw = round(raw_bw * efficiency, 1)
            
            if not pcie.get("bidirectional_bandwidth_gbs"):
                pcie["bidirectional_bandwidth_gbs"] = effective_bw * 2
                result.add_fix(f"Calculated PCIe gen {gen} {lanes} bandwidth: {effective_bw * 2} GB/s bidirectional")
        except Exception as e:
            result.add_error(f"PCIe validation error: {e}")
        
        spec["_validation"] = result.summary()
        return spec, result
