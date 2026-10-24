"""
Deterministic architectural templates interface.
"""
from typing import Dict, Any, Union
from product_architect.product_architect_templates import (
    get_deterministic_template as _get_deterministic_template
)

def get_deterministic_template(task_type: str, prompt: str = "") -> Union[Dict[str, Any], list, str]:
    return _get_deterministic_template(task_type, prompt)

def get_functional_spec_template(inputs: Dict[str, Any]) -> Dict[str, Any]:
    brief = inputs.get("product_brief", "")
    power = inputs.get("power_budget_w", 1000)
    prompt = f"{brief} {inputs.get('target_market', '')} {power}W {inputs.get('process_node', '')}"
    res = _get_deterministic_template("functional_spec", prompt)
    if isinstance(res, dict):
        return res
    return {}

def get_nfr_spec_template(inputs: Dict[str, Any], func_spec: Dict[str, Any] = None) -> Dict[str, Any]:
    brief = inputs.get("product_brief", "")
    power = inputs.get("power_budget_w", 1000)
    prompt = f"{brief} {inputs.get('target_market', '')} {power}W {inputs.get('process_node', '')}"
    res = _get_deterministic_template("nfr_spec", prompt)
    if isinstance(res, dict):
        return res
    return {}
