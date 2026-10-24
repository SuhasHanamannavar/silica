"""
Test SpecValidator deterministic validation and auto-fixing logic.
"""
from product_architect.validators import SpecValidator

v = SpecValidator()

# Test 1: HBM bandwidth calculation
print("=== Test 1: HBM Bandwidth ===")
spec = {
    "memory_hierarchy": {
        "hbm_subsystem": {
            "bus_width_bits": 1024,
            "data_rate_gbps_per_pin": 8.0,
            # total_bandwidth_tbs intentionally missing
        }
    }
}
fixed, result = v.validate_functional_spec(spec)
bw = fixed["memory_hierarchy"]["hbm_subsystem"]["total_bandwidth_tbs"]
print(f"  Calculated bandwidth: {bw} TB/s")
print(f"  Expected: 1.024 TB/s")
assert abs(bw - 1.024) < 0.01, f"Bandwidth error: got {bw}"
print(f"  PASS")
print(f"  Fixes: {result.fixes_applied}")

# Test 2: Die cost model
print("\n=== Test 2: Die Cost Model ===")
cost = v.validate_die_cost(800, "TSMC 4nm")
print(f"  800mm² on TSMC 4nm:")
print(f"    Yield: {cost['yield_rate_percent']}%")
print(f"    Die cost: ${cost['die_cost_usd']}")
print(f"    Dies/wafer: {cost['good_dies_per_wafer']}")
assert cost["yield_rate_percent"] > 0
assert cost["die_cost_usd"] > 0

# Test 3: Reticle limit check
print("\n=== Test 3: Reticle Limit ===")
nfr = {"area_budget": {"total_die_area_mm2": 900, "allocation": {}}}
fixed_nfr, r = v.validate_nonfunctional_spec(nfr)
print(f"  900mm² die: {fixed_nfr['area_budget']['reticle_limit_check']}")
print(f"  Chiplet required: {fixed_nfr['area_budget']['chiplet_required']}")
print(f"  Warnings: {r.warnings}")
assert fixed_nfr["area_budget"]["reticle_limit_check"] == "EXCEEDS"
assert fixed_nfr["area_budget"]["chiplet_required"] is True

# Test 4: Roofline
print("\n=== Test 4: Roofline Model ===")
rl = v.validate_roofline(peak_tflops=2000, bandwidth_tbs=8.0, arithmetic_intensity=1.0)
print(f"  2000 TFLOPS, 8 TB/s, AI=1.0 FLOPs/byte:")
print(f"    Ridge point: {rl['ridge_point_flops_per_byte']} FLOPs/byte")
print(f"    Bound type: {rl['bound_type']}")
print(f"    Utilization: {rl['peak_utilization_percent']}%")
print(f"    Expected: memory_bound, ~0.4% utilization (LLM decode scenario)")
assert rl["bound_type"] == "memory_bound"
assert abs(rl["ridge_point_flops_per_byte"] - 250.0) < 0.1
assert abs(rl["peak_utilization_percent"] - 0.4) < 0.1

print("\nALL VALIDATOR TESTS PASSED!")
