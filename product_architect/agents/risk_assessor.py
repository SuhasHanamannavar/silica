import json
from typing import Dict, Any, List

class RiskAssessor:
    """
    Identifies technical, schedule, cost, and market risks.
    NVIDIA-level: thinks about EVERYTHING that could go wrong.
    """
    
    PROMPT_TEMPLATE = """You are a SENIOR NVIDIA RISK ASSESSMENT ARCHITECT.
You have 20 years of experience identifying what kills chip programs.
Be PARANOID. Be SPECIFIC. If it CAN go wrong, it WILL go wrong.

{context}

FUNCTIONAL SPEC:
{functional_spec}

NON-FUNCTIONAL SPEC:
{nfr_spec}

TRADEOFF DECISIONS:
{tradeoffs}

Identify ALL significant risks. For each risk provide:
- Risk ID and description
- Category: technical / schedule / cost / market / supply_chain / regulatory
- Likelihood: 1-5 (5 = certain)
- Impact: 1-5 (5 = catastrophic)
- Risk Score: likelihood × impact
- Root cause analysis
- Early warning indicators
- Mitigation strategy (prevent / detect / recover)
- Contingency plan
- Owner (which downstream team)

Focus areas to cover:
1. Technology risks (new process node, new HBM, new NVLink)
2. Architecture risks (chiplet yield, bandwidth, power)
3. Implementation risks (timing closure, area, verification)
4. Supply chain risks (HBM shortage, foundry capacity)
5. Market risks (competitor response, customer adoption)
6. Software risks (CUDA compatibility, library enablement)
7. Regulatory risks (export controls, safety standards)

Output as JSON array of risk objects.
"""
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, functional_spec: Dict, nfr_spec: Dict, tradeoffs: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            "GPU risk failure modes HBM supply process yield",
            categories=["process_node_data", "hbm_specs", "cost_models"]
        )
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            functional_spec=json.dumps(functional_spec, indent=2)[:3000],
            nfr_spec=json.dumps(nfr_spec, indent=2)[:2000],
            tradeoffs=json.dumps(tradeoffs, indent=2)[:2000],
        )
        
        result = self.llm.call("risk_assessment", prompt, enforce_json=True)
        risks = result.get("structured_output")
        if not isinstance(risks, list) or not risks:
            risks = self.llm._deterministic_fallback("risk_assessment", prompt).get("structured_output", [])
        if not isinstance(risks, list):
            risks = []
            
        # Add deterministic risks
        self._add_deterministic_risks(risks, nfr_spec)
        
        # Sort by risk score
        risks.sort(key=lambda r: r.get("risk_score", 0) if isinstance(r, dict) else 0, reverse=True)
        
        return {
            "risks": risks,
            "summary": self._generate_summary(risks),
            "high_risk_count": sum(1 for r in risks if isinstance(r, dict) and r.get("risk_score", 0) >= 15),
            "medium_risk_count": sum(1 for r in risks if isinstance(r, dict) and 10 <= r.get("risk_score", 0) < 15),
            "low_risk_count": sum(1 for r in risks if isinstance(r, dict) and r.get("risk_score", 0) < 10),
        }
    
    def _add_deterministic_risks(self, risks: list, nfr_spec: Dict):
        """Add risks that are deterministically identifiable from the spec."""
        area = nfr_spec.get("area_budget", {})
        existing_ids = {r.get("risk_id") for r in risks if isinstance(r, dict)}
        
        if area.get("chiplet_required", False) and "RISK-CHIPLET-001" not in existing_ids:
            risks.append({
                "risk_id": "RISK-CHIPLET-001",
                "description": "Chiplet integration yield, thermal warpage, and assembly bonding defects",
                "category": "technical",
                "likelihood": 4,
                "impact": 5,
                "risk_score": 20,
                "root_cause": "Advanced CoWoS-L substrate complexity and high-density micro-bump array",
                "early_warning_indicators": "Test coupon micro-voids, elevated link resistance on daisy chains",
                "mitigation": "Test chips for inter-die interface; redundant lanes; qualified packaging house",
                "contingency": "Fall back to monolithic design if packaging yield < 65%",
                "owner": "Package Engineering + DFT",
            })
        
        power = nfr_spec.get("power_budget", {}).get("total_tdp_watts", 0)
        if power >= 1000 and "RISK-POWER-001" not in existing_ids:
            risks.append({
                "risk_id": "RISK-POWER-001",
                "description": f"High power envelope ({power}W) causes thermal hot-spots and transient voltage droop",
                "category": "technical",
                "likelihood": 3,
                "impact": 5,
                "risk_score": 15,
                "root_cause": "Compute power density exceeding 2.5 W/mm² during sustained tensor operations",
                "early_warning_indicators": "Thermal sensor alarm triggers, millivolt drop on VDD_CORE sense lines",
                "mitigation": "Conservative DVFS; extensive thermal simulation; direct liquid cooling cold plates",
                "contingency": "Reduce boost frequency by 5-10%; implement aggressive voltage binning",
                "owner": "Physical Design + System Engineering",
            })
    
    def _generate_summary(self, risks: list) -> str:
        if not isinstance(risks, list) or len(risks) == 0:
            return "No risks identified."
        
        high = [r for r in risks if isinstance(r, dict) and r.get("risk_score", 0) >= 15]
        summary = f"Identified {len(risks)} risks total. "
        summary += f"{len(high)} HIGH risks (score ≥ 15). "
        if high:
            summary += "Top concerns: " + ", ".join(r.get("risk_id", "?") for r in high[:5])
        return summary
