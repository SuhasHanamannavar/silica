"""
Multi-pass critique-revise engine for architectural specifications.
"""
import json
import time
from typing import Dict, Any, List
from product_architect.llm_backend import LLMBackend

CRITIQUE_PROMPT = """You are a Principal Silicon Architect reviewing this specification.
Find ANY issues:
1. MATH: Do numbers match? Bandwidth = bus_width * data_rate / 8?
2. FEASIBILITY: Can this be built on {process_node}?
3. WORKLOAD FIT: Does this serve {workloads}?
4. POWER: Are power allocations realistic for the TDP?
5. AREA: Does total die area fit reticle limits (<=858 mm²)?
6. COMPETITIVENESS: Would this beat AMD MI300 and Google TPU v5?
7. PROGRAMMABILITY: Any issues for CUDA developers?
8. COST: Is this manufacturable at a reasonable cost?

For EACH issue found, specify:
- issue_id
- description
- severity: CRITICAL / HIGH / MEDIUM / LOW
- root_cause
- specific_fix

Output ONLY a JSON array of issue objects.
"""

class MultiPassEngine:
    def __init__(self, llm: LLMBackend):
        self.llm = llm
    
    def refine_spec(self, agent, agent_kwargs: Dict, max_passes: int = 3) -> Dict:
        """Generate -> Critique -> Revise loop."""
        all_audit = []
        
        # Pass 1: Initial generation
        result = agent.run(**agent_kwargs)
        all_audit.append({
            "pass": 1,
            "action": "initial_generation", 
            "validation": result.get("validation", {})
        })
        
        spec = result.get("spec", result)
        inputs = agent_kwargs.get("inputs", agent_kwargs)
        
        for pass_num in range(2, max_passes + 1):
            # Critique
            critique = self._critique(spec, inputs)
            all_audit.append({
                "pass": pass_num,
                "action": "critique", 
                "issues_found": len(critique),
                "issues": critique[:5]
            })
            
            critical = [c for c in critique if isinstance(c, dict) and c.get("severity") in ("CRITICAL", "HIGH")]
            if not critical:
                all_audit.append({"pass": pass_num, "action": "converged"})
                break
            
            # Re-run with critique in context
            revised_kwargs = dict(agent_kwargs)
            revised_kwargs["critique"] = critique
            try:
                result = agent.run(**revised_kwargs)
            except TypeError:
                result = agent.run(**agent_kwargs)
            spec = result.get("spec", result)
            all_audit.append({"pass": pass_num, "action": "revised"})
        
        if isinstance(result, dict):
            result["_multipass_audit"] = all_audit
        
        return result
    
    def run(self, agent, agent_inputs: Dict, max_passes: int = 3) -> Dict:
        """Alias for refine_spec to maintain backward compatibility."""
        return self.refine_spec(agent, agent_inputs, max_passes=max_passes)
    
    def _critique(self, spec: Dict, inputs: Dict) -> list:
        prompt = CRITIQUE_PROMPT.format(
            spec=json.dumps(spec, indent=2)[:5000],
            workloads=", ".join(inputs.get("key_workloads", [])),
            process_node=inputs.get("process_node", "TSMC 4nm"),
        )
        r = self.llm.call("critique", prompt, enforce_json=True)
        output = r.get("structured_output", [])
        return output if isinstance(output, list) else []
