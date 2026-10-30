import json
from typing import Dict, Any

class InterfaceSpecifier:
    """
    Generates precise interface specifications for all external and internal interfaces.
    """
    
    PROMPT_TEMPLATE = """You are a PRINCIPAL NVIDIA I/O ARCHITECT.
Define EVERY interface on this GPU with PRECISE, QUANTIFIED specifications.

{context}

FUNCTIONAL SPEC:
{functional_spec}

NON-FUNCTIONAL SPEC:
{nfr_spec}

Generate the complete interface specification as JSON:
{{
  "external_interfaces": {{
    "hbm": {{
      "standard": "HBM3e / HBM4",
      "channel_count": NUMBER,
      "pseudo_channels_per_channel": 2,
      "data_rate_gbps": NUMBER,
      "bus_width_total_bits": NUMBER,
      "total_bandwidth_tbs": NUMBER,
      "voltage_v": 1.1,
      "channel_width_bits": 128,
      "ecc": "SEC-DED / Double-chipkill",
      "physics": "Wide I/O, micro-bumps, 2.5D/3D packaging",
      "stack_count": NUMBER,
      "capacity_per_stack_gb": NUMBER,
      "total_capacity_gb": NUMBER
    }},
    "nvlink": {{
      "generation": "5.0",
      "lane_count": NUMBER,
      "data_rate_gbps_per_lane": 100,
      "encoding": "PAM4",
      "bidirectional_bandwidth_tbs": NUMBER,
      "latency_ns": NUMBER,
      "voltage_v": 0.9,
      "protocol_layers": ["Physical", "Link", "Transport", "Transaction"],
      "features": ["FEC", "ARQ", "Flow control", "Multicast"],
      "max_gpus_per_node": 8,
      "switch_supported": true
    }},
    "pcie": {{
      "generation": "6.0",
      "lane_count": "x16",
      "data_rate_gtps": 64,
      "encoding": "PAM4",
      "bidirectional_bandwidth_gbs": NUMBER,
      "cxl_supported": true,
      "cxl_version": "3.1",
      "cxl_protocols": ["io", "cache", "mem"],
      "sriov_supported": true,
      "max_vfs": 20,
      "voltage_v": 0.85
    }},
    "power": {{
      "rails": [
        {{"name": "VDD_CORE", "voltage_v": 0.85, "tolerance_pct": 5, "max_current_a": NUMBER, "ripple_mv": 25}},
        {{"name": "VDD_MEM", "voltage_v": 1.1, "tolerance_pct": 5, "max_current_a": NUMBER, "ripple_mv": 25}},
        {{"name": "VDD_IO", "voltage_v": 1.8, "tolerance_pct": 10, "max_current_a": NUMBER}}
      ],
      "power_sequencing": "VDD_MEM → 200us → VDD_CORE → 100us → VDD_IO",
      "sense_points_required": true
    }},
    "clock": {{
      "reference_clocks": [
        {{"name": "PCIe_REFCLK", "freq_mhz": 100, "jitter_ps_rms": 0.5}},
        {{"name": "HBM_REFCLK", "freq_mhz": 1600, "jitter_ps_rms": 1.0}}
      ],
      "spread_spectrum": "Downspread 0.5%",
      "clock_enable_requirements": true
    }},
    "management": {{
      "i2c": {{"speed_khz": 400, "address": "0x20", "purpose": "PMBUS, thermal, EEPROM"}},
      "spi": {{"speed_mhz": 50, "purpose": "Boot ROM, firmware loading"}},
      "jtag": {{"standard": "IEEE 1149.1", "purpose": "Test, debug, DFT access"}},
      "gpio_count": 16,
      "uart": {{"baud_rate": 115200, "purpose": "Debug console"}}
    }},
    "thermal": {{
      "diode_count": 4,
      "placement": "One per quadrant, one near hotspot",
      "accuracy_c": "±1°C",
      "alert_pin": true
    }}
  }},
  "internal_interfaces": {{
    "noc": {{
      "protocol": "Custom / CHI-like",
      "topology": "Mesh / Distributed crossbar",
      "data_width_bits": 512,
      "clock_mhz": NUMBER,
      "bisection_bandwidth_tbs": NUMBER,
      "qos_supported": true,
      "coherency_supported": true
    }},
    "sm_to_l2": {{"interface": "Custom", "bandwidth_per_sm_gbs": NUMBER, "latency_ns": NUMBER}},
    "l2_to_mc": {{"interface": "Custom", "bandwidth_gbs": NUMBER, "latency_ns": NUMBER}},
    "clock_domains": [
      {{"name": "core_clk", "freq_mhz": "varies (DVFS)"}},
      {{"name": "hbm_clk", "freq_mhz": NUMBER}},
      {{"name": "nvlink_clk", "freq_mhz": NUMBER}},
      {{"name": "pcie_clk", "freq_mhz": 250}},
      {{"name": "noc_clk", "freq_mhz": NUMBER}}
    ],
    "power_domains": [
      {{"name": "core", "always_on": false, "gating_supported": true}},
      {{"name": "memory", "always_on": true}},
      {{"name": "nvlink_phy", "always_on": false, "gating_supported": true}},
      {{"name": "pcie_phy", "always_on": false, "gating_supported": true}}
    ],
    "reset_strategy": {{
      "type": "Active-low asynchronous reset, synchronous release",
      "domains": "Per-clock-domain reset",
      "power_on_reset_sequence": "Assert all resets → de-assert in order: MEM → CORE → I/O"
    }}
  }},
  "electrical_specifications": {{
    "esd_protection": "HBM 2kV, CDM 500V",
    "signal_integrity": {{
      "nvlink_insertion_loss_db": "< 25dB at Nyquist",
      "nvlink_crosstalk_db": "< -35dB",
      "pcie_insertion_loss_db": "< 30dB at Nyquist"
    }},
    "power_integrity": {{
      "core_ir_drop_pct": "< 3%",
      "ac_noise_mv_pp": "< 25"
    }}
  }}
}}
"""
    
    def __init__(self, llm_backend=None, knowledge_base=None, validator=None):
        self.llm = llm_backend
        self.kb = knowledge_base
        from product_architect.validators import SpecValidator
        self.validator = validator or SpecValidator()
    
    def run(self, functional_spec: Dict, nfr_spec: Dict, **kwargs) -> Dict:
        context = ""
        if self.kb:
            context = self.kb.get_context(
                "HBM NVLink PCIe CXL interface specification electrical",
                categories=["interface_standards", "hbm_specs"]
            )
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            functional_spec=json.dumps(functional_spec, indent=2)[:3000],
            nfr_spec=json.dumps(nfr_spec, indent=2)[:2000],
        )
        
        out = None
        model_used = "deterministic"
        provider = "local"
        latency_s = 0.0
        if self.llm:
            result = self.llm.call("interface_spec", prompt, enforce_json=True)
            out = result.get("structured_output")
            model_used = result.get("model_used", model_used)
            provider = result.get("provider", provider)
            latency_s = result.get("latency_s", latency_s)
        if not isinstance(out, dict) or not out:
            out = self._get_fallback_interfaces(functional_spec, nfr_spec)
        
        # Deterministic validator pass
        fixed_spec, _ = self.validator.validate_interface_spec(out)
        fixed_spec["model_used"] = model_used
        fixed_spec["provider"] = provider
        fixed_spec["latency_s"] = latency_s
        return fixed_spec
    
    def _get_fallback_interfaces(self, functional_spec: Dict, nfr_spec: Dict) -> Dict:
        """Deterministic default interface spec."""
        hbm_sub = functional_spec.get("memory_hierarchy", {}).get("hbm_subsystem", {})
        return {
            "external_interfaces": {
                "hbm": {
                    "standard": hbm_sub.get("hbm_generation", "HBM3e"),
                    "channel_count": 16,
                    "pseudo_channels_per_channel": 2,
                    "data_rate_gbps": hbm_sub.get("data_rate_gbps_per_pin", 8.0),
                    "bus_width_total_bits": hbm_sub.get("bus_width_bits", 8192),
                    "total_bandwidth_tbs": hbm_sub.get("total_bandwidth_tbs", 8.0),
                    "voltage_v": 1.1,
                    "channel_width_bits": 128,
                    "ecc": "SEC-DED / Double-chipkill",
                    "physics": "Wide I/O, micro-bumps, 2.5D CoWoS-L packaging",
                    "stack_count": hbm_sub.get("stack_count", 8),
                    "capacity_per_stack_gb": 24,
                    "total_capacity_gb": hbm_sub.get("total_capacity_gb", 192)
                },
                "nvlink": {
                    "generation": "5.0",
                    "lane_count": 18,
                    "data_rate_gbps_per_lane": 100,
                    "encoding": "PAM4",
                    "bidirectional_bandwidth_tbs": 1.8,
                    "latency_ns": 45,
                    "voltage_v": 0.9,
                    "protocol_layers": ["Physical", "Link", "Transport", "Transaction"],
                    "features": ["FEC", "ARQ", "Flow control", "Hardware Multicast"],
                    "max_gpus_per_node": 8,
                    "switch_supported": True
                },
                "pcie": {
                    "generation": "6.0",
                    "lane_count": "x16",
                    "data_rate_gtps": 64,
                    "encoding": "PAM4",
                    "bidirectional_bandwidth_gbs": 128.0,
                    "cxl_supported": True,
                    "cxl_version": "3.1",
                    "cxl_protocols": ["io", "cache", "mem"],
                    "sriov_supported": True,
                    "max_vfs": 32,
                    "voltage_v": 0.85
                },
                "power": {
                    "rails": [
                        {"name": "VDD_CORE", "voltage_v": 0.85, "tolerance_pct": 3, "max_current_a": 950.0, "ripple_mv": 20},
                        {"name": "VDD_MEM", "voltage_v": 1.1, "tolerance_pct": 4, "max_current_a": 160.0, "ripple_mv": 25},
                        {"name": "VDD_IO", "voltage_v": 1.8, "tolerance_pct": 5, "max_current_a": 45.0}
                    ],
                    "power_sequencing": "VDD_IO -> 100us -> VDD_MEM -> 150us -> VDD_CORE",
                    "sense_points_required": True
                },
                "clock": {
                    "reference_clocks": [
                        {"name": "PCIe_REFCLK", "freq_mhz": 100, "jitter_ps_rms": 0.5},
                        {"name": "HBM_REFCLK", "freq_mhz": 1600, "jitter_ps_rms": 0.8}
                    ],
                    "spread_spectrum": "Downspread 0.5%",
                    "clock_enable_requirements": True
                },
                "management": {
                    "i2c": {"speed_khz": 400, "address": "0x20", "purpose": "PMBus telemetry, VRM monitor"},
                    "spi": {"speed_mhz": 50, "purpose": "Secure boot ROM and microcode reload"},
                    "jtag": {"standard": "IEEE 1149.1 / IEEE 1500", "purpose": "Boundary scan, DFT, BIST"},
                    "gpio_count": 16,
                    "uart": {"baud_rate": 115200, "purpose": "Debug telemetry console"}
                },
                "thermal": {
                    "diode_count": 8,
                    "placement": "Distributed across each GPC tile and HBM PHY border",
                    "accuracy_c": "±0.5°C",
                    "alert_pin": True
                }
            },
            "internal_interfaces": {
                "noc": {
                    "protocol": "Custom Credit-Based Flit Network",
                    "topology": "2D Torus / Mesh",
                    "data_width_bits": 512,
                    "clock_mhz": 2000,
                    "bisection_bandwidth_tbs": 24.0,
                    "qos_supported": True,
                    "coherency_supported": True
                },
                "sm_to_l2": {"interface": "AXI-Stream Extension", "bandwidth_per_sm_gbs": 512.0, "latency_ns": 12},
                "l2_to_mc": {"interface": "Ultra-Wide Port", "bandwidth_gbs": 1024.0, "latency_ns": 20},
                "clock_domains": [
                    {"name": "core_clk", "freq_mhz": "1800-2250 (DVFS)"},
                    {"name": "hbm_clk", "freq_mhz": 3906},
                    {"name": "nvlink_clk", "freq_mhz": 1562},
                    {"name": "pcie_clk", "freq_mhz": 500},
                    {"name": "noc_clk", "freq_mhz": 2000}
                ],
                "power_domains": [
                    {"name": "core", "always_on": False, "gating_supported": True},
                    {"name": "memory", "always_on": True},
                    {"name": "nvlink_phy", "always_on": False, "gating_supported": True},
                    {"name": "pcie_phy", "always_on": False, "gating_supported": True}
                ],
                "reset_strategy": {
                    "type": "Active-low asynchronous assert, synchronous de-assert",
                    "domains": "Per-clock-domain reset sequencing",
                    "power_on_reset_sequence": "Assert all resets -> De-assert: MEM -> CORE -> I/O"
                }
            },
            "electrical_specifications": {
                "esd_protection": "HBM 2kV, CDM 500V",
                "signal_integrity": {
                    "nvlink_insertion_loss_db": "< 25dB at 25GHz Nyquist",
                    "nvlink_crosstalk_db": "< -38dB",
                    "pcie_insertion_loss_db": "< 28dB at 16GHz Nyquist"
                },
                "power_integrity": {
                    "core_ir_drop_pct": "< 2.5%",
                    "ac_noise_mv_pp": "< 20"
                }
            }
        }