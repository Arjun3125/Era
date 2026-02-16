"""
minister_runtime.py
Orchestrates minister activation and execution based on latched domains.
"""
from typing import Dict, Any, List


class MinisterRuntime:
    def __init__(self):
        # registry: domain -> minister instance
        self.registry: Dict[str, Any] = {}

    def register_minister(self, domain: str, minister_obj: Any) -> None:
        self.registry[domain] = minister_obj

    def activate_ministers(self, situation: Dict[str, Any], latched_domains: List[str], context: Dict[str, Any] | None = None) -> Dict[str, Dict[str, Any]]:
        outputs: Dict[str, Dict[str, Any]] = {}
        for d in latched_domains:
            minister = self.registry.get(d)
            if not minister:
                continue
            try:
                out = minister.produce_advice(situation=situation, active_domains=latched_domains, context=context or {})
                outputs[d] = out
            except Exception as e:
                outputs[d] = {"error": str(e)}
        return outputs
