#!/usr/bin/env python3
"""
Test suite for Silica Product Architect Module.
Verifies NVIDIA-Caliber 9-agent pipeline, deterministic engines,
multi-pass critique loops, and specification freeze gates.
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from product_architect import (
    ProductArchitectOrchestrator,
    LLMBackend,
    KnowledgeBase,
    MultiPassEngine,
)
from product_architect.agents import (
    MarketAnalyzer,
    FunctionalSpecGenerator,
    NonFunctionalSpecGenerator,
    ArchitecturalTradeoffAnalyst,
    RooflineModeler,
    BlockDiagramArchitect,
    InterfaceSpecifier,
    RiskAssessor,
    DieCostModeler,
    DocumentAssembler,
)

class TestProductArchitect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm = LLMBackend()
        cls.kb = KnowledgeBase()
        cls.orchestrator = ProductArchitectOrchestrator(cls.llm, cls.kb)
        cls.sample_inputs = {
            "product_brief": "Flagship dual-die AI training and inference GPU for 2026-2028 frontier clusters",
            "target_market": "Datacenter & Hyperscale Cloud Infrastructure",
            "key_workloads": ["LLM training", "LLM autoregressive decode", "LLM prefill", "diffusion", "hpc"],
            "power_budget_w": 1000.0,
            "process_node": "TSMC 3nm (N3P)",
            "competitors": ["NVIDIA Blackwell B200", "AMD Instinct MI300X", "Google TPU v5p"]
        }

    def test_01_knowledge_base_retrieval(self):
        """Test domain knowledge retrieval across categories."""
        chunks = self.kb.retrieve("Blackwell NVLink HBM3e", categories=["nvidia_architecture", "hbm_specs"])
        self.assertGreater(len(chunks), 0)
        found_blackwell = any("blackwell" in c.content.lower() for c in chunks)
        self.assertTrue(found_blackwell, "Knowledge base should contain Blackwell architecture data")
        
        ctx = self.kb.get_context("TSMC 3nm wafer cost defect density", categories=["process_node_data"])
        self.assertIn("TSMC 3nm", ctx)

    def test_02_roofline_deterministic_engine(self):
        """Test deterministic roofline arithmetic intensity and bound calculations."""
        modeler = RooflineModeler(self.llm, self.kb)
        mock_func_spec = {
            "compute_architecture": {
                "precision_formats": [
                    {"format": "BF16", "peak_tflops": 1800.0, "enabled": True},
                    {"format": "FP8", "peak_tflops": 3600.0, "enabled": True}
                ]
            },
            "memory_hierarchy": {
                "hbm_subsystem": {
                    "total_bandwidth_tbs": 8.0
                }
            }
        }
        res = modeler.run(mock_func_spec, ["LLM autoregressive decode", "LLM prefill"])
        self.assertEqual(res["peak_compute"]["bf16_tflops"], 1800.0)
        self.assertEqual(res["peak_compute"]["fp8_tflops"], 3600.0)
        self.assertEqual(res["memory_bandwidth_tbs"], 8.0)
        # Ridge point = 1800 / 8 = 225
        self.assertEqual(res["ridge_points"]["bf16_flops_per_byte"], 225.0)
        # Decode has AI = 1.0 -> memory bound
        decode_res = next(w for w in res["workload_analysis"] if "decode" in w["workload"].lower())
        self.assertEqual(decode_res["bf16"]["bound_type"], "memory_bound")
        self.assertIn("ROOFLINE MODEL", res["ascii_roofline"])

    def test_03_die_cost_murphy_yield(self):
        """Test physical wafer geometry and Murphy yield equation calculations."""
        cost_modeler = DieCostModeler()
        mock_nfr = {
            "area_budget": {
                "total_die_area_mm2": 1180.0,
                "chiplet_required": True,
                "chiplet_count_if_required": 2
            }
        }
        res = cost_modeler.run(mock_nfr, "TSMC 3nm (N3P)")
        self.assertEqual(res["wafer_diameter_mm"], 300.0)
        self.assertEqual(res["wafer_cost_usd"], 20000)
        self.assertEqual(res["single_die_area_mm2"], 590.0)
        self.assertGreater(res["gross_dies_per_wafer_dpw"], 50)
        self.assertGreater(res["die_yield_percent"], 50.0)
        self.assertGreater(res["total_unit_bom_cost_usd"], 4000.0)
        self.assertGreater(res["target_asp_usd"], res["total_unit_bom_cost_usd"])

    def test_04_budget_summation_validation(self):
        """Test non-functional spec generator enforces 100% budget summations."""
        nfr_gen = NonFunctionalSpecGenerator(self.llm, self.kb)
        nfr = nfr_gen.run(self.sample_inputs, {})
        power = nfr.get("power_budget", {})
        alloc = power.get("allocation", {})
        pct_sum = sum(v.get("percent", 0) for v in alloc.values())
        self.assertAlmostEqual(pct_sum, 100.0, delta=1.0)
        
        area = nfr.get("area_budget", {})
        area_alloc = area.get("allocation", {})
        area_pct_sum = sum(v.get("percent", 0) for v in area_alloc.values())
        self.assertAlmostEqual(area_pct_sum, 100.0, delta=1.0)
        self.assertTrue(area.get("chiplet_required"))

    def test_05_tradeoff_decisions(self):
        """Test 5 critical architectural decisions scored."""
        analyst = ArchitecturalTradeoffAnalyst(self.llm, self.kb)
        res = analyst.run(self.sample_inputs, {}, {"area_budget": {"total_die_area_mm2": 1180}})
        decisions = res.get("decisions_summary", [])
        self.assertEqual(len(decisions), 5)
        decision_ids = [d.get("decision_id") for d in decisions]
        self.assertIn("monolithic_vs_chiplet", decision_ids)
        self.assertIn("precision_format_strategy", decision_ids)
        self.assertIn("l2_cache_sizing", decision_ids)
        self.assertIn("hbm_generation_selection", decision_ids)
        self.assertIn("sm_count_vs_clock_frequency", decision_ids)

    def test_06_risk_register(self):
        """Test risk assessor identifies and ranks critical failure modes."""
        assessor = RiskAssessor(self.llm, self.kb)
        mock_nfr = {
            "area_budget": {"chiplet_required": True, "total_die_area_mm2": 1180},
            "power_budget": {"total_tdp_watts": 1000}
        }
        res = assessor.run({}, mock_nfr, {})
        risks = res.get("risks", [])
        self.assertGreaterEqual(len(risks), 2)
        # Check sorted descending
        scores = [r.get("risk_score", 0) for r in risks]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_07_full_pipeline_orchestrator(self):
        """Test end-to-end multi-agent orchestration and document assembly."""
        res = self.orchestrator.run_full_pipeline(self.sample_inputs, use_multipass=True)
        self.assertEqual(res.get("status"), "draft_for_human_review")
        self.assertEqual(len(res.get("stages", {})), 9)
        docs = res.get("documents", {}).get("documents", {})
        self.assertIn("00_MARKET_REQUIREMENTS.md", docs)
        self.assertIn("01_FUNCTIONAL_SPECIFICATION.md", docs)
        self.assertIn("02_NON_FUNCTIONAL_SPECIFICATION.md", docs)
        self.assertIn("03_ARCHITECTURAL_TRADEOFFS.md", docs)
        self.assertIn("04_ROOFLINE_ANALYSIS.md", docs)
        self.assertIn("05_BLOCK_DIAGRAM_ARCHITECTURE.md", docs)
        self.assertIn("06_INTERFACE_SPECIFICATION.md", docs)
        self.assertIn("07_RISK_REGISTER.md", docs)
        self.assertIn("08_DIE_COST_MODEL.md", docs)
        self.assertIn("09_HUMAN_REVIEW_CHECKLIST.md", docs)
        self.assertIn("10_SPECIFICATION_SUMMARY.md", docs)
        self.assertIn("FULL_SPECIFICATION_PACKAGE.md", docs)
        
        # Test human feedback & spec freeze
        frozen = self.orchestrator.freeze_specification(res, signoff_lead="Dr. NVIDIA Chief Architect")
        self.assertEqual(frozen.get("status"), "SPEC_FROZEN")
        self.assertTrue(frozen.get("spec_freeze_ready"))
        self.assertIn("Dr. NVIDIA Chief Architect", frozen.get("signoff_lead"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
