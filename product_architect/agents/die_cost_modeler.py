import math
from typing import Dict, Any

class DieCostModeler:
    """
    Deterministic semiconductor die yield and cost modeling engine.
    Uses Murphy and Poisson yield models, 300mm wafer geometry,
    and foundry economic models for advanced packaging & HBM.
    """
    
    NODE_PARAMETERS = {
        "2nm": {"wafer_cost": 30000, "mask_cost": 10000000, "defect_density": 0.22},
        "3nm": {"wafer_cost": 20000, "mask_cost": 7500000, "defect_density": 0.22},
        "4nm": {"wafer_cost": 16000, "mask_cost": 5000000, "defect_density": 0.28},
        "5nm": {"wafer_cost": 10000, "mask_cost": 4000000, "defect_density": 0.35},
        "7nm": {"wafer_cost": 6000, "mask_cost": 2500000, "defect_density": 0.40},
    }
    
    def run(self, nfr_spec: Dict, process_node: str, **kwargs) -> Dict[str, Any]:
        """Compute full physical die yield and unit manufacturing BOM cost."""
        node_key = "4nm"
        pn_lower = str(process_node).lower()
        for k in ["2nm", "3nm", "4nm", "5nm", "7nm"]:
            if k in pn_lower:
                node_key = k
                break
                
        node_cfg = self.NODE_PARAMETERS.get(node_key, self.NODE_PARAMETERS["4nm"])
        wafer_cost = node_cfg["wafer_cost"]
        mask_cost = node_cfg["mask_cost"]
        defect_density = node_cfg["defect_density"]  # defects per cm²
        
        area_budget = nfr_spec.get("area_budget", {})
        total_die_area = float(area_budget.get("total_die_area_mm2", 820.0) or 820.0)
        chiplet_required = bool(area_budget.get("chiplet_required", total_die_area > 800))
        chiplet_count = int(area_budget.get("chiplet_count_if_required", 2 if chiplet_required else 1) or 1)
        if not chiplet_required:
            chiplet_count = 1
            
        single_die_area = total_die_area / chiplet_count
        wafer_diameter = 300.0  # 300mm standard wafer
        wafer_area = math.pi * ((wafer_diameter / 2) ** 2)  # ~70,685.8 mm²
        
        # Gross dies per wafer formula (accounting for wafer edge exclusion 3mm)
        eff_radius = (wafer_diameter / 2) - 3.0
        eff_wafer_area = math.pi * (eff_radius ** 2)
        dpw = math.floor((eff_wafer_area / single_die_area) - (math.pi * wafer_diameter / math.sqrt(2 * single_die_area)))
        dpw = max(1, dpw)
        
        # Murphy Yield Model with harvesting & redundancy:
        # GPU architectures incorporate redundant SM units and laser-repairable SRAM columns,
        # reducing critical non-repairable defect-sensitive area to ~55% of raw silicon.
        crit_factor = 0.55 if chiplet_count > 1 else 0.70
        area_cm2 = (single_die_area * crit_factor) / 100.0
        da = defect_density * area_cm2
        if da > 0:
            yield_rate = ((1.0 - math.exp(-da)) / da) ** 2
        else:
            yield_rate = 1.0
            
        yield_pct = round(max(0.05, min(0.95, yield_rate)) * 100.0, 1)
        good_dies_per_wafer = max(1, math.floor(dpw * (yield_pct / 100.0)))
        
        raw_die_cost = round(wafer_cost / good_dies_per_wafer, 2)
        total_silicon_cost = round(raw_die_cost * chiplet_count, 2)
        
        # Advanced packaging (CoWoS-L with organic interposer / RDL bridge)
        pkg_cost = 980.0 if chiplet_count > 1 else 520.0
        
        # HBM memory cost (estimated 192GB HBM3e @ $18/GB)
        hbm_cost = 3450.0
        
        # Testing, substrate & assembly
        assembly_and_test = 450.0
        
        total_bom = round(total_silicon_cost + pkg_cost + hbm_cost + assembly_and_test, 2)
        
        # Commercial targets
        projected_volume = 250000
        amortized_nre = round(mask_cost / projected_volume, 2)
        total_unit_cost = round(total_bom + amortized_nre, 2)
        target_gross_margin = 75.0  # NVIDIA-tier datacenter margin
        target_asp = round(total_bom / (1.0 - (target_gross_margin / 100.0)), 2)
        
        return {
            "process_node": process_node,
            "wafer_diameter_mm": wafer_diameter,
            "wafer_cost_usd": wafer_cost,
            "mask_nre_cost_usd": mask_cost,
            "defect_density_defects_per_cm2": defect_density,
            "total_die_area_mm2": total_die_area,
            "chiplet_architecture": "Dual-Die CoWoS-L" if chiplet_count > 1 else "Monolithic Single Die",
            "die_count_per_package": chiplet_count,
            "single_die_area_mm2": round(single_die_area, 1),
            "gross_dies_per_wafer_dpw": dpw,
            "die_yield_percent": yield_pct,
            "net_good_dies_per_wafer_gdpw": good_dies_per_wafer,
            "raw_die_cost_usd": raw_die_cost,
            "total_silicon_cost_per_package_usd": total_silicon_cost,
            "advanced_packaging_cowos_usd": pkg_cost,
            "hbm_memory_subsystem_usd": hbm_cost,
            "assembly_and_final_test_usd": assembly_and_test,
            "total_unit_bom_cost_usd": total_bom,
            "amortized_mask_nre_per_unit_usd": amortized_nre,
            "total_manufacturing_cost_per_unit_usd": total_unit_cost,
            "target_gross_margin_percent": target_gross_margin,
            "target_asp_usd": target_asp,
            "projected_unit_volume": projected_volume,
            "projected_product_revenue_usd_billion": round((target_asp * projected_volume) / 1e9, 2),
        }
