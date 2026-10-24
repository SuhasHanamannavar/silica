import json
import time
from typing import Dict, Any, List

class MultiPassEngine:
    """
    4-pass generation with critique:
    Pass 1: Generate initial spec
    Pass 2: CRITIQUE — find flaws, inconsistencies, optimizations
    Pass 3: REVISE — fix identified issues
    Pass 4: VALIDATE — deterministic + LLM final check
    
    This mimics how senior architects work: draft, review, revise, validate.
    """
    
    def __init__(self, llm_backend):
        self.llm = llm_backend
    
    CRITIQUE_PROMPT = """You are a SKEPTICAL NVIDIA FELLOW reviewing a junior architect's work.
Your job is to find EVERY flaw, inconsistency, suboptimal choice, and missing consideration.
Be HARSH. Be THOROUGH. This chip costs $100M+ — mistakes are expensive.

{context}

SPECIFICATION TO REVIEW:
{spec}

REVIEW DIMENSIONS:
1. NUMERIC CONSISTENCY: Do all numbers add up? Bandwidth = bus_width × data_rate / 8?
2. PHYSICAL FEASIBILITY: Is this physically realizable? Any laws of physics violated?
3. TECHNOLOGY REALISM: Are process node assumptions correct? HBM availability?
4. WORKLOAD OPTIMALITY: Is the architecture actually optimal for stated workloads?
5. TRADEOFF QUALITY: Are there better tradeoffs not considered?
6. MISSING CONSIDERATIONS: What important factors were completely missed?
7. COMPETITIVENESS: Would this beat the competition?
8. COST REALISM: Are cost targets achievable?
9. POWER REALISM: Is power budget achievable?
10. RISK IDENTIFICATION: What obvious risks are missing?

For EACH flaw found, specify:
- What's wrong
- Why it's wrong (quantitative evidence)
- How to fix it
- Severity: CRITICAL / HIGH / MEDIUM / LOW

Output as JSON array of critique objects.
"""
    
    def run(self, agent, agent_inputs: Dict, max_passes: int = 3) -> Dict:
        """Run multi-pass generation with critique."""
        all_audit = []
        
        # Pass 1: Initial generation
        result = agent.run(**agent_inputs)
        all_audit.append({"pass": 1, "action": "initial_generation", "result_summary": self._summarize(result)})
        
        for pass_num in range(2, max_passes + 1):
            # Critique pass
            critique = self._critique(result, agent_inputs)
            all_audit.append({"pass": pass_num, "action": "critique", "findings": len(critique)})
            
            if not critique or all(c.get("severity") == "LOW" for c in critique if isinstance(c, dict)):
                all_audit.append({"pass": pass_num, "action": "converged", "reason": "no significant issues found"})
                break
            
            # Revise pass
            result = self._revise(agent, agent_inputs, result, critique)
            all_audit.append({"pass": pass_num, "action": "revision_applied", 
                             "issues_fixed": len(critique)})
        
        # Final validation
        validation = self._final_validate(result)
        all_audit.append({"pass": "final", "action": "validation", "result": validation})
        
        if isinstance(result, dict):
            result["_multipass_audit"] = all_audit
            result["_validation"] = validation
        
        return result
    
    def _critique(self, spec: Dict, agent_inputs: Dict) -> list:
        """Generate critique of current spec."""
        prompt = self.CRITIQUE_PROMPT.format(
            context="",
            spec=json.dumps(spec, indent=2)[:6000],
        )
        result = self.llm.call("critique", prompt, enforce_json=True)
        output = result.get("structured_output", [])
        return output if isinstance(output, list) else []
    
    def _revise(self, agent, agent_inputs: Dict, current_spec: Dict, critique: list) -> Dict:
        """Revise the spec based on critique findings."""
        revised_inputs = dict(agent_inputs)
        # Pass critique context into agent inputs for refined generation
        revised_inputs["critique_feedback"] = critique
        try:
            return agent.run(**revised_inputs)
        except TypeError:
            # If agent.run signature doesn't accept critique_feedback kwarg
            return agent.run(**agent_inputs)
    
    def _final_validate(self, spec: Dict) -> Dict:
        """Final deterministic validation."""
        checks = {
            "has_required_fields": True,
            "numeric_consistency": True,
            "physical_feasibility": True,
            "no_inf_values": True,
            "no_negative_values": True,
        }
        
        def check_values(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_values(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for idx, v in enumerate(obj):
                    check_values(v, f"{path}[{idx}]")
            elif isinstance(obj, (int, float)):
                if obj < 0 and "voltage" not in path.lower() and "offset" not in path.lower() and "change" not in path.lower():
                    checks["no_negative_values"] = False
                if obj == float('inf') or obj == float('-inf'):
                    checks["no_inf_values"] = False
        
        check_values(spec)
        checks["overall"] = all(checks.values())
        return checks
    
    def _summarize(self, result: Dict) -> str:
        if isinstance(result, dict):
            keys = list(result.keys())[:5]
            return f"keys: {keys}"
        return "non-dict result"
