"""
Base minister interface for MCA.
Ministers must produce a structured, non-prose output contract.
"""
from typing import Dict, Any, List


class BaseMinister:
    def __init__(self, name: str, domain: str, doctrine: Dict[str, Any] | None = None):
        self.name = name
        self.domain = domain
        self.doctrine = doctrine or {}

    def produce_advice(self, situation: Dict[str, Any], active_domains: List[str], context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Return a structured minister output (default: cautious placeholder).

        Output contract:
        {
          "minister": "risk",
          "stance": "support|oppose|caution",
          "confidence": 0.0-1.0,
          "primary_argument": "...",
          "supporting_evidence": [ {"type":"principle","book":"...","kis":1.23} ],
          "second_order_effects": "...",
          "red_line_triggered": False
        }
        """
        return {
            "minister": self.domain,
            "stance": "caution",
            "confidence": 0.0,
            "primary_argument": "no-op placeholder",
            "supporting_evidence": [],
            "second_order_effects": "",
            "red_line_triggered": False,
        }
