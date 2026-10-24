import json
from typing import Dict, Any, List

class RooflineModeler:
    """
    Deterministic roofline analysis engine.
    This is PURE MATH — no LLM needed for the core calculation.
    LLM is used only for interpretation and recommendations.
    """
    
    WORKLOAD_AI = {
        # Arithmetic intensity in FLOPs/byte
        "llm training": 3.5,
        "llm inference": 0.8,
        "llm autoregressive decode": 1.0,
        "llm prefill": 15.0,
        "llm": 2.0,  # average
        "diffusion training": 8.0,
        "diffusion inference": 5.0,
        "diffusion": 6.5,
        "cnn training": 12.0,
        "cnn inference": 8.0,
        "cnn": 10.0,
        "hpc": 4.0,
        "general ai compute": 5.0,
        "graphics": 3.0,
    }
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, functional_spec: Dict, workloads: list, **kwargs) -> Dict:
        """Run deterministic roofline analysis."""
        compute = functional_spec.get("compute_architecture", {})
        mem = functional_spec.get("memory_hierarchy", {}).get("hbm_subsystem", {})
        
        # Get peak BF16 TFLOPS
        peak_bf16 = self._extract_peak_tflops(compute, "BF16")
        peak_fp8 = self._extract_peak_tflops(compute, "FP8")
        bandwidth = float(mem.get("total_bandwidth_tbs", 8.0) or 8.0)
        
        # Ridge point = peak / bandwidth
        ridge_bf16 = peak_bf16 / bandwidth if bandwidth > 0 else float('inf')
        ridge_fp8 = peak_fp8 / bandwidth if bandwidth > 0 else float('inf')
        
        # Analyze each workload
        workload_results = []
        for wl in workloads:
            ai = self._estimate_ai(wl)
            
            # BF16 analysis
            attainable_bf16 = min(peak_bf16, bandwidth * ai)
            bound_bf16 = "memory_bound" if ai < ridge_bf16 else "compute_bound"
            util_bf16 = attainable_bf16 / peak_bf16 * 100 if peak_bf16 > 0 else 0
            
            # FP8 analysis
            attainable_fp8 = min(peak_fp8, bandwidth * ai)
            bound_fp8 = "memory_bound" if ai < ridge_fp8 else "compute_bound"
            util_fp8 = attainable_fp8 / peak_fp8 * 100 if peak_fp8 > 0 else 0
            
            workload_results.append({
                "workload": wl,
                "arithmetic_intensity_flops_per_byte": round(ai, 2),
                "bf16": {
                    "peak_tflops": peak_bf16,
                    "attainable_tflops": round(attainable_bf16, 1),
                    "bound_type": bound_bf16,
                    "peak_utilization_percent": round(util_bf16, 1),
                },
                "fp8": {
                    "peak_tflops": peak_fp8,
                    "attainable_tflops": round(attainable_fp8, 1),
                    "bound_type": bound_fp8,
                    "peak_utilization_percent": round(util_fp8, 1),
                },
                "bandwidth_needed_for_full_util_tbs": round(peak_bf16 / ai, 2) if ai > 0 else float('inf'),
                "bandwidth_gap_tbs": round(max(0, peak_bf16 / ai - bandwidth), 2) if ai > 0 else 0,
            })
        
        # Generate interpretation
        interpretation = self._generate_interpretation(
            peak_bf16, peak_fp8, bandwidth, ridge_bf16, ridge_fp8, workload_results
        )
        
        return {
            "peak_compute": {
                "bf16_tflops": peak_bf16,
                "fp8_tflops": peak_fp8,
            },
            "memory_bandwidth_tbs": bandwidth,
            "ridge_points": {
                "bf16_flops_per_byte": round(ridge_bf16, 1),
                "fp8_flops_per_byte": round(ridge_fp8, 1),
            },
            "workload_analysis": workload_results,
            "interpretation": interpretation,
            "ascii_roofline": self._generate_ascii_roofline(peak_bf16, bandwidth, ridge_bf16, workload_results),
        }
    
    def _extract_peak_tflops(self, compute_spec: Dict, precision: str) -> float:
        """Extract peak TFLOPS for a given precision from spec."""
        formats = compute_spec.get("precision_formats", [])
        for f in formats:
            if f.get("format", "").upper() == precision.upper():
                return float(f.get("peak_tflops", f.get("peak_tops", 1800.0)))
        
        sm = compute_spec.get("sm_architecture", {})
        sm_count = sm.get("total_sm_count", 144)
        clock_ghz = sm.get("boost_clock_mhz", 2250) / 1000
        
        fp32 = sm_count * 128 * 2 * clock_ghz / 1000  # TFLOPS
        factors = {"FP64": 0.5, "FP32": 1.0, "TF32": 2.0, "FP16": 2.0, 
                   "BF16": 2.0, "FP8": 4.0, "NVFP4": 8.0, "INT8": 4.0, "INT4": 8.0}
        
        return round(fp32 * factors.get(precision.upper(), 1.0), 1)
    
    def _estimate_ai(self, workload: str) -> float:
        """Estimate arithmetic intensity based on workload name."""
        wl_lower = workload.lower()
        for key, val in self.WORKLOAD_AI.items():
            if key in wl_lower:
                return val
        return 5.0
    
    def _generate_interpretation(self, peak_bf16, peak_fp8, bandwidth, 
                                 ridge_bf16, ridge_fp8, results) -> str:
        """Use LLM or fallback to generate human-readable interpretation."""
        prompt = f"""Interpret this roofline analysis for a GPU architect:

- Peak BF16: {peak_bf16} TFLOPS
- Peak FP8: {peak_fp8} TFLOPS  
- HBM Bandwidth: {bandwidth} TB/s
- Ridge point BF16: {ridge_bf16:.1f} FLOPs/byte
- Ridge point FP8: {ridge_fp8:.1f} FLOPs/byte

Workload analysis:
{json.dumps(results, indent=2)}

Provide:
1. Overall architecture assessment (balanced? memory-heavy? compute-heavy?)
2. Key bottlenecks identified
3. Specific architectural recommendations to improve
4. Which workloads are well-served, which are not
5. Should we prioritize more bandwidth or more compute?

Keep it concise and architectural.
"""
        result = self.llm.call("fast_calculation", prompt, enforce_json=False)
        return result.get("text", "Interpretation not available")
    
    def _generate_ascii_roofline(self, peak, bandwidth, ridge, results) -> str:
        """Generate ASCII roofline plot."""
        lines = []
        lines.append("")
        lines.append("          ROOFLINE MODEL")
        lines.append("")
        lines.append(f"  Peak TFLOPS  |        ┌───────────────────────────── Compute Roof ({peak:.0f} TFLOPS)")
        lines.append(f"     {peak:>6.0f}   |       /")
        lines.append(f"               |      /")
        lines.append(f"               |     /  Memory Slope: {bandwidth:.1f} TB/s")
        lines.append(f"               |    /")
        lines.append(f"               |   /")
        lines.append(f"               |  /")
        lines.append(f"               | /")
        lines.append(f"               |/")
        lines.append(f"               └────────────────────────────────── Arithmetic Intensity (FLOPs/byte)")
        lines.append(f"               0        Ridge: {ridge:.1f} FLOPs/byte")
        lines.append("")
        lines.append("  Workload positions:")
        for r in results:
            ai = r["arithmetic_intensity_flops_per_byte"]
            marker = "●"
            lines.append(f"    {r['workload'][:30]:<30s} AI={ai:>5.1f}  [{marker}]  {r['bf16']['bound_type']}")
        lines.append("")
        return "\n".join(lines)
