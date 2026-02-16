"""Mode-specific reward shaping utilities."""
from typing import Dict

def reward_function(mode: str, features: Dict[str, float]) -> float:
    """Compute a scalar reward conditioned on `mode` and feature dict."""
    # Safe getters with default 0.0
    get = lambda k: float(features.get(k, 0.0))

    if mode == "QUICK":
        # brevity and accuracy prioritized
        return get("brevity") * 0.5 + get("accuracy") * 0.5

    if mode == "WAR":
        return get("argument_strength") * 0.6 + get("consistency") * 0.4

    if mode == "MEETING":
        return get("structure") * 0.4 + get("synthesis") * 0.6

    if mode == "DARBAR":
        return get("multi_agent_coherence") * 0.7 + get("optimality") * 0.3

    # Default: balanced
    return sum(features.values()) / (len(features) or 1)
