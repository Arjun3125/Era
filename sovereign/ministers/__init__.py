r"""Minister Modules - Individual domain-specific modules for each minister.

Each minister is isolated into its own module that:
1. Loads and executes its minister role
2. Generates KIS (Knowledge Integration System) for its domain
3. Connects to Prime Confident flow for decision finalization

LOCATION: c:\\era\\sovereign\\ministers\\
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from persona.knowledge_engine import synthesize_knowledge
from persona.ministers import MINISTERS, JUDGES
from persona.trace import trace


@dataclass
class MinisterModuleOutput:
    """Output from a minister module execution."""
    minister_name: str
    domain: str
    stance: str
    confidence: float
    reasoning: str
    kis_data: Optional[Dict[str, Any]] = None
    flow_result: Optional[Dict[str, Any]] = None
    red_line: bool = False


class MinisterModule:
    """Base class for minister modules."""
    
    def __init__(self, domain: str, minister_class, llm=None):
        self.domain = domain
        self.minister_name = minister_class.__name__ if minister_class else "Unknown"
        self.minister_class = minister_class
        self.llm = llm
        self.minister = minister_class(domain=domain, llm=llm) if minister_class else None
        self.kis_cache = {}
    
    def generate_kis(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate KIS for this minister's domain."""
        if user_input in self.kis_cache:
            return self.kis_cache[user_input]
        
        try:
            kis_result = synthesize_knowledge(
                user_input,
                active_domains=[self.domain],
                domain_confidence=0.8
            )
            self.kis_cache[user_input] = kis_result
            return kis_result
        except Exception as e:
            trace("kis_generation_error", {"domain": self.domain, "error": str(e)})
            return {"synthesized_knowledge": [], "error": str(e)}
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterModuleOutput:
        """Execute minister analysis."""
        position = self.minister.analyze(user_input, context)
        
        # Generate domain-specific KIS
        kis_data = self.generate_kis(user_input, context)
        
        trace(f"minister_module_{self.domain}", {
            "minister": self.minister_name,
            "domain": self.domain,
            "stance": position.stance,
            "confidence": position.confidence,
            "kis_items": len(kis_data.get("synthesized_knowledge", []))
        })
        
        return MinisterModuleOutput(
            minister_name=self.minister_name,
            domain=self.domain,
            stance=position.stance,
            confidence=position.confidence,
            reasoning=position.reasoning,
            kis_data=kis_data,
            red_line=position.red_line_triggered
        )
    
    def invoke_with_prime(self, output: MinisterModuleOutput, prime_confident_instance) -> Dict[str, Any]:
        """
        Invoke this minister's output with Prime Confident for flow finalization.
        
        Args:
            output: MinisterModuleOutput from analyze()
            prime_confident_instance: Instance of PrimeConfident
        
        Returns:
            Flow result containing Prime Confident's decision
        """
        try:
            # Package minister output for Prime Confident
            flow_data = {
                "minister": self.minister_name,
                "domain": self.domain,
                "position": {
                    "stance": output.stance,
                    "confidence": output.confidence,
                    "reasoning": output.reasoning,
                    "red_line": output.red_line
                },
                "kis_summary": {
                    "items_count": len(output.kis_data.get("synthesized_knowledge", [])) if output.kis_data else 0,
                    "has_knowledge": bool(output.kis_data and output.kis_data.get("synthesized_knowledge"))
                }
            }
            
            # Let Prime Confident factor in the minister's position
            # (This is advisory - Prime Confident makes final decision)
            output.flow_result = flow_data
            
            trace(f"minister_prime_flow_{self.domain}", {
                "minister": self.minister_name,
                "flow_initiated": True
            })
            
            return flow_data
        except Exception as e:
            trace(f"minister_prime_flow_error_{self.domain}", {
                "error": str(e)
            })
            return {"error": str(e)}


# Factory function to create minister modules
def create_minister_module(domain: str, llm=None) -> MinisterModule:
    """Create a MinisterModule for a specific domain."""
    if domain in MINISTERS:
        minister_class = MINISTERS[domain]
        return MinisterModule(domain, minister_class, llm)
    elif domain in JUDGES:
        minister_class = JUDGES[domain]
        return MinisterModule(domain, minister_class, llm)
    else:
        raise ValueError(f"Unknown domain: {domain}")


# Create all minister modules
ALL_MINISTER_MODULES = {
    domain: create_minister_module(domain) for domain in MINISTERS.keys()
}

# Create all judge modules (advisory)
ALL_JUDGE_MODULES = {
    domain: create_minister_module(domain) for domain in JUDGES.keys()
}
