import json
from typing import Dict, Any

class BlockDiagramArchitect:
    """
    Defines the chip-level block diagram and subsystem partitioning.
    Outputs both structured data and ASCII/Mermaid diagram.
    """
    
    def run(self, functional_spec: Dict, nfr_spec: Dict, **kwargs) -> Dict:
        compute = functional_spec.get("compute_architecture", {})
        mem = functional_spec.get("memory_hierarchy", {})
        interconnect = functional_spec.get("interconnect", {})
        area = nfr_spec.get("area_budget", {})
        
        sm_count = compute.get("sm_architecture", {}).get("total_sm_count", 144)
        chiplet = area.get("chiplet_required", True)
        chiplet_count = area.get("chiplet_count_if_required", 2) if chiplet else 1
        
        sm_per_gpc = 16  # Typical NVIDIA grouping
        gpc_count = max(1, (sm_count + sm_per_gpc - 1) // sm_per_gpc)
        sm_per_gpc_actual = max(1, sm_count // gpc_count)
        
        hbm_stacks = mem.get("hbm_subsystem", {}).get("stack_count", 8)
        l2_total = mem.get("l2_cache", {}).get("total_size_mb", 192)
        
        nvlink_lanes = interconnect.get("nvlink", {}).get("lane_count", 18)
        pcie_lanes = interconnect.get("pcie", {}).get("lane_count", "x16")
        
        diagram = {
            "chiplet_strategy": {
                "chiplet_required": chiplet,
                "chiplet_count": chiplet_count,
                "inter_die_interconnect": "CoWoS-L Silicon Bridge with D2D High-Density PHY" if chiplet else "N/A",
                "inter_die_bandwidth_tbs": 10.0 if chiplet else 0.0,
            },
            "per_die_structure": {
                "gpc_count": gpc_count // chiplet_count if chiplet else gpc_count,
                "sm_per_gpc": sm_per_gpc_actual,
                "total_sm_count": sm_count,
                "gpc_components": [
                    f"{sm_per_gpc_actual} × SMs (Streaming Multiprocessors)",
                    "L1 Instruction & Texture Caches",
                    "Tensor Memory Accelerators (TMA 2.0)",
                    "Rasterization & Work Distribution Units"
                ],
            },
            "memory_subsystem": {
                "hbm_stack_count": hbm_stacks,
                "memory_controllers": hbm_stacks * 2,
                "l2_cache_partitions": gpc_count,
                "l2_per_partition_mb": round(l2_total / gpc_count, 1) if gpc_count else l2_total,
            },
            "interconnect_subsystem": {
                "noc_topology": "Distributed 2D Mesh with Crossbar Tiles",
                "nvlink_lanes": nvlink_lanes,
                "nvlink_phys": 2,
                "pcie_lanes": pcie_lanes,
                "pcie_phy_count": 1,
            },
            "support_subsystems": [
                "Clock generation (H-tree PLLs)",
                "Power management & DVFS Controller",
                "On-die thermal diode matrix (16 sensors)",
                "JTAG / IEEE 1149.1 test access port",
                "PMBus / I2C / SMBus system management",
                "GPIO control logic",
                "SPI boot ROM interface"
            ],
            "floorplan_notes": [
                "Compute GPCs placed symmetrically across center core",
                "HBM PHYs aligned along perimeter micro-bumps directly above CoWoS interposer",
                "192 MB L2 cache partitions interleaved directly between GPC tiles to reduce hop count",
                "High-speed NVLink 5.0 SerDes PHYs located on external edge",
                "Power grid mesh with dedicated backside delivery vias for minimal IR-drop"
            ],
        }
        
        diagram["mermaid_diagram"] = self._generate_mermaid(diagram, chiplet_count)
        diagram["ascii_diagram"] = self._generate_ascii(diagram)
        
        return diagram
    
    def _generate_mermaid(self, d: Dict, chiplet_count: int) -> str:
        """Generate Mermaid.js block diagram."""
        lines = ["graph TB"]
        
        if chiplet_count > 1:
            lines.append("    subgraph PACKAGE[Package - CoWoS-L Advanced Substrate]")
            for i in range(chiplet_count):
                lines.append(f"        subgraph DIE{i+1}[Compute Die {i+1} (TSMC 4NP/3nm)]")
                lines.append(f"            GPC{i+1}_GROUP[{d['per_die_structure']['gpc_count']} GPCs<br/>{d['per_die_structure']['total_sm_count'] // chiplet_count} SMs]")
                lines.append(f"            L2_{i+1}[Distributed L2 Cache]")
                lines.append(f"            MC_{i+1}[HBM Memory Controllers]")
                lines.append(f"            D2D_{i+1}[10 TB/s Die-to-Die PHY]")
                lines.append("        end")
            lines.append("        HBM[8x HBM3e Memory Stacks (192 GB @ 8 TB/s)]")
            lines.append("        NVLINK[18-Lane NVLink 5.0 PHYs (1.8 TB/s)]")
            lines.append("        PCIE[PCIe Gen6 x16 PHY (128 GB/s)]")
            lines.append("    end")
            lines.append("    D2D_1 <-->|Passive Silicon Bridge| D2D_2")
            lines.append("    GPC1_GROUP <--> L2_1")
            lines.append("    GPC2_GROUP <--> L2_2")
            lines.append("    L2_1 <--> MC_1")
            lines.append("    L2_2 <--> MC_2")
            lines.append("    MC_1 <--> HBM")
            lines.append("    MC_2 <--> HBM")
            lines.append("    L2_1 <--> NVLINK")
            lines.append("    L2_2 <--> PCIE")
        else:
            lines.append("    subgraph DIE[Monolithic GPU Die]")
            lines.append(f"        GPC_GROUP[{d['per_die_structure']['gpc_count']} GPCs<br/>Each: {d['per_die_structure']['sm_per_gpc']} SMs]")
            lines.append(f"        L2[L2 Cache {d['memory_subsystem']['l2_cache_partitions']} partitions]")
            lines.append(f"        MC[Memory Controllers x {d['memory_subsystem']['memory_controllers']}]")
            lines.append("        NOC[NoC 2D-Mesh Interconnect Fabric]")
            lines.append("    end")
            lines.append(f"    HBM[HBM Stacks x {d['memory_subsystem']['hbm_stack_count']}]")
            lines.append(f"    NVLINK[NVLink PHYs<br/>{d['interconnect_subsystem']['nvlink_lanes']} lanes]")
            lines.append(f"    PCIE[PCIe {d['interconnect_subsystem']['pcie_lanes']}]")
            lines.append("    GPC_GROUP <--> NOC")
            lines.append("    L2 <--> NOC")
            lines.append("    MC <--> NOC")
            lines.append("    MC <--> HBM")
            lines.append("    NOC <--> NVLINK")
            lines.append("    NOC <--> PCIE")
        
        return "\n".join(lines)
    
    def _generate_ascii(self, d: Dict) -> str:
        """Generate ASCII block diagram."""
        lines = []
        lines.append("")
        lines.append("┌─────────────────────────────────────────────────────────────────┐")
        lines.append("│                        GPU DIE FLOORPLAN                        │")
        lines.append("├─────────────────────────────────────────────────────────────────┤")
        lines.append("│                                                                 │")
        lines.append("│   ┌─────────┐  ┌─────────┐         ┌─────────────────────────┐  │")
        lines.append("│   │   GPC   │  │   GPC   │  ...    │   HBM PHY / Mem Ctrl    │  │")
        lines.append(f"│   │ {d['per_die_structure']['sm_per_gpc']}× SMs │  │ {d['per_die_structure']['sm_per_gpc']}× SMs │         │   ×{d['memory_subsystem']['memory_controllers']} controllers   │  │")
        lines.append("│   └─────────┘  └─────────┘         └─────────────────────────┘  │")
        lines.append("│                                                                 │")
        lines.append("│   ┌─────────────────────────────────────────────────────────┐  │")
        lines.append(f"│   │              L2 CACHE ({d['memory_subsystem']['l2_cache_partitions']} partitions, distributed)              │  │")
        lines.append("│   └─────────────────────────────────────────────────────────┘  │")
        lines.append("│                                                                 │")
        lines.append("│   ┌─────────┐  ┌─────────┐         ┌─────────────────────────┐  │")
        lines.append("│   │   GPC   │  │   GPC   │  ...    │   NVLink / PCIe PHYs    │  │")
        lines.append(f"│   │         │  │         │         │   {d['interconnect_subsystem']['nvlink_lanes']} lanes NVLink   │  │")
        lines.append("│   └─────────┘  └─────────┘         └─────────────────────────┘  │")
        lines.append("│                                                                 │")
        lines.append("│   ┌─────────────────────────────────────────────────────────┐  │")
        lines.append("│   │   Clock Gen │ Power Mgmt │ Thermal │ JTAG │ I2C │ SPI    │  │")
        lines.append("│   └─────────────────────────────────────────────────────────┘  │")
        lines.append("│                                                                 │")
        lines.append("└─────────────────────────────────────────────────────────────────┘")
        lines.append("")
        lines.append(f"  Total: {d['per_die_structure']['gpc_count']} GPCs per die, {d['per_die_structure']['total_sm_count']} SMs Total")
        lines.append(f"  NoC: {d['interconnect_subsystem']['noc_topology']}")
        lines.append("")
        return "\n".join(lines)
