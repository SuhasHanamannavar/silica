import json
from typing import Dict, Any

class MarketAnalyzer:
    """
    Analyzes target market, customer needs, and competitive landscape.
    Output: Market Requirements Document (MRD) in structured form.
    """
    
    PROMPT_TEMPLATE = """You are a SENIOR NVIDIA MARKET & COMPETITIVE ANALYST with 15 years of experience.
Analyze the following GPU/AI accelerator opportunity and produce a quantified market analysis.

{context}

PRODUCT VISION: {product_brief}
TARGET MARKET: {target_market}
KEY WORKLOADS: {workloads}
POWER BUDGET: {power_budget}W
PROCESS NODE: {process_node}
COMPETITORS: {competitors}

Produce a structured analysis with these sections:

1. MARKET OPPORTUNITY
   - Market size estimate ($B) and CAGR
   - Key customer segments (hyperscalers, cloud, enterprise, etc.)
   - Primary purchase drivers
   - Timeline for volume deployment

2. CUSTOMER REQUIREMENTS (quantified)
   - Performance targets per workload
   - Power constraints (rack-level, chip-level)
   - Software compatibility needs
   - Scaling requirements (multi-GPU, multi-node)
   - Reliability/availability expectations

3. COMPETITIVE LANDSCAPE
   For each competitor, provide:
   - Key strengths and weaknesses
   - Performance comparison (estimated TFLOPS, bandwidth)
   - Power efficiency
   - Software ecosystem maturity
   - Price/performance positioning

4. STRATEGIC RECOMMENDATIONS
   - Where should this product play? (training vs inference, scale-up vs scale-out)
   - What are the 3 most important differentiators?
   - What are the "must-have" vs "nice-to-have" features?
   - Timeline recommendations (when to tape-out, when to ship)

Output as valid JSON only.
"""
    
    def __init__(self, llm_backend, knowledge_base):
        self.llm = llm_backend
        self.kb = knowledge_base
    
    def run(self, inputs: Dict, **kwargs) -> Dict:
        context = self.kb.get_context(
            f"{inputs.get('product_brief', '')} {inputs.get('target_market', '')} GPU AI accelerator",
            categories=["nvidia_architecture", "workload_characteristics", "cost_models"]
        )
        
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            product_brief=inputs.get("product_brief", "AI Accelerator"),
            target_market=inputs.get("target_market", "Datacenter"),
            workloads=", ".join(inputs.get("key_workloads", ["LLM", "Diffusion"])),
            power_budget=inputs.get("power_budget_w", 700),
            process_node=inputs.get("process_node", "TSMC 3nm"),
            competitors=", ".join(inputs.get("competitors", ["NVIDIA B200", "AMD MI300X", "Google TPU v5p"])),
        )
        
        result = self.llm.call("market_analysis", prompt, enforce_json=True)
        return result.get("structured_output", {"raw_text": result.get("text", "")})
