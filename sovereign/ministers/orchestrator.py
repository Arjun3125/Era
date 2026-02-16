r"""
Minister Flow Orchestrator - Coordinates all ministers with KIS and Prime Confident.

Location: c:\era\sovereign\ministers\orchestrator.py

This orchestrator:
1. Executes all minister modules in parallel
2. Generates domain-specific KIS for each
3. Invokes Prime Confident with aggregated input
4. Returns final decision with full audit trail
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from persona.council import CouncilAggregator
from persona.trace import trace

# Import meeting flow
from .meeting_flow import meeting_mode_flow

# Import minister module collections from __init__
from . import ALL_MINISTER_MODULES, ALL_JUDGE_MODULES
from ..llm_adapter import OllamaAdapter
from ..prime_confident import PrimeConfident


@dataclass
class MinisterFlowResult:
    """Complete flow result from all ministers through Prime Confident."""
    minister_outputs: Dict[str, MinisterModuleOutput] = field(default_factory=dict)
    judge_observations: Dict[str, MinisterModuleOutput] = field(default_factory=dict)
    council_recommendation: Optional[Any] = None
    prime_decision: Optional[Any] = None
    kis_summary: Dict[str, Any] = field(default_factory=dict)
    execution_trace: List[str] = field(default_factory=list)


class MinisterFlowOrchestrator:
    """Orchestrates execution flow for all ministers with KIS and Prime Confident."""
    
    def __init__(self, llm=None):
        self.llm = llm
        # llm can be an adapter instance or None; prefer injected adapter, else create OllamaAdapter
        if llm and hasattr(llm, "generate"):
            self.llm_adapter = llm
        else:
            try:
                self.llm_adapter = OllamaAdapter()
            except Exception:
                self.llm_adapter = None

        self.council = CouncilAggregator(llm=self.llm_adapter)
        # Instantiate PrimeConfident with the adapter so it can use LLM assessments
        try:
            self.prime_confident = PrimeConfident(risk_threshold=0.7, llm_adapter=self.llm_adapter)
        except Exception:
            self.prime_confident = None
        
        # Use pre-instantiated minister modules (already have full context)
        self.minister_modules = ALL_MINISTER_MODULES.copy()
        self.judge_modules = ALL_JUDGE_MODULES.copy()

    
    def execute_ministers(self, user_input: str, context: Dict[str, Any]) -> MinisterFlowResult:
        """
        Execute ministers with mode-aware routing.
        
        If context contains "mode": "meeting", routes to 2-3 minister meeting discussion.
        Otherwise executes full darbar (all ministers).
        
        Args:
            user_input: User's input/decision to evaluate
            context: Conversation context
        
        Returns:
            MinisterFlowResult with full decision audit trail
        """
        
        # Check for meeting mode branch
        if context.get("mode") == "meeting":
            return self._execute_meeting_mode(user_input, context)
        
        # Default: Full darbar execution (all ministers)
        return self._execute_darbar_mode(user_input, context)
    
    def _execute_meeting_mode(self, user_input: str, context: Dict[str, Any]) -> MinisterFlowResult:
        """
        Meeting mode: 2-3 minister discussion & debate branch.
        
        Selects relevant ministers, synthesizes debate, and passes to Prime Confident.
        """
        result = MinisterFlowResult()
        
        trace("meeting_mode_flow_start", {"user_input": user_input[:80]})
        
        # Get topic from context or use general
        topic = context.get("topic", "general decision")
        
        # Execute meeting flow - 2-3 ministers discuss and debate
        synthesis, should_continue = meeting_mode_flow(
            self.minister_modules,
            topic,
            user_input,
            context,
            llm_adapter=self.llm_adapter
        )
        
        if synthesis is None:
            result.execution_trace.append("Meeting mode: No synthesis generated")
            return result
        
        # Add synthesis results to flow result
        result.minister_outputs = synthesis.debate_outputs
        result.execution_trace.append(f"Meeting {topic}: {synthesis.shared_recommendation}")
        result.execution_trace.append(f"  Consensus: {synthesis.consensus_strength:.0%}")
        result.execution_trace.append(f"  Viability: {synthesis.viability_score:.2f}")
        result.execution_trace.append(f"  Reason: {synthesis.viability_reason}")
        
        # Add KIS summary from synthesis
        total_kis = sum(
            len(output.kis_points) 
            for output in synthesis.debate_outputs.values()
        )
        result.kis_summary = {
            "total_kis_items": total_kis,
            "domains_with_kis": len(synthesis.debate_outputs),
            "kis_per_domain": {domain: len(output.kis_points) for domain, output in synthesis.debate_outputs.items()}
        }
        
        # If viability check passes, invoke Prime Confident
        if should_continue:
            trace("meeting_mode_passed_viability", {"viability_score": synthesis.viability_score})
            result.execution_trace.append("MEETING SYNTHESIS PASSED VIABILITY - Forwarding to Prime Confident")
            # Convert DebateOutput objects into the MinisterModuleOutput-like dicts expected by PrimeConfident
            converted = {}
            for domain, out in synthesis.debate_outputs.items():
                try:
                    converted[domain] = {
                        "stance": out.stance,
                        "confidence": out.confidence,
                        "reasoning": out.reasoning,
                        "red_line_triggered": bool(getattr(out, "red_lines_triggered", [])),
                    }
                except Exception:
                    converted[domain] = {"stance": "unknown", "confidence": 0.0, "reasoning": "", "red_line": False}
            result.minister_outputs = converted
            return self.invoke_prime_confident(result, self.prime_confident)
        else:
            trace("meeting_mode_failed_viability", {"viability_score": synthesis.viability_score})
            result.execution_trace.append("MEETING SYNTHESIS LOW VIABILITY - Requires escalation/review")
            return result
    
    def _execute_darbar_mode(self, user_input: str, context: Dict[str, Any]) -> MinisterFlowResult:
        """
        Darbar mode: Full council execution (all 19 ministers + 1 judge).
        
        All ministers analyze independently, council aggregates, Prime Confident decides.
        """
        result = MinisterFlowResult()
        
        trace("minister_flow_start", {
            "total_ministers": len(self.minister_modules),
            "total_judges": len(self.judge_modules)
        })
        
        # Execute voting ministers
        for domain, module in self.minister_modules.items():
            try:
                output = module.analyze(user_input, context)
                result.minister_outputs[domain] = output
                result.execution_trace.append(f"Minister {domain}: {output.stance} ({output.confidence:.2f})")
                
                # Invoke with Prime Confident flow
                flow_result = module.invoke_with_prime(output, self.prime_confident)
                
                trace(f"minister_flow_{domain}", {
                    "stance": output.stance,
                    "confidence": output.confidence,
                    "kis_items": len(output.kis_data.get("synthesized_knowledge", [])) if output.kis_data else 0
                })
                
            except Exception as e:
                trace(f"minister_flow_error_{domain}", {"error": str(e)})
                result.execution_trace.append(f"Minister {domain}: ERROR - {str(e)}")
        
        # Execute judge observations (advisory, non-voting)
        for domain, module in self.judge_modules.items():
            try:
                output = module.analyze(user_input, context)
                result.judge_observations[domain] = output
                result.execution_trace.append(f"Judge {domain}: {output.stance} (advisory)")
                
                trace(f"judge_observation_{domain}", {
                    "stance": output.stance,
                    "advisory_only": True
                })
                
            except Exception as e:
                trace(f"judge_observation_error_{domain}", {"error": str(e)})
        
        # Get Council recommendation (voting ministers only)
        try:
            result.council_recommendation = self.council.convene(user_input, context)
            result.execution_trace.append(
                f"Council: {result.council_recommendation.recommendation} "
                f"({result.council_recommendation.consensus_strength:.2%} strength)"
            )
            
            trace("council_recommendation", {
                "outcome": result.council_recommendation.outcome,
                "recommendation": result.council_recommendation.recommendation,
                "consensus": result.council_recommendation.consensus_strength
            })
        except Exception as e:
            trace("council_recommendation_error", {"error": str(e)})
            result.execution_trace.append(f"Council: ERROR - {str(e)}")
        
        # Summarize KIS data
        kis_counts = {
            domain: len(output.kis_data.get("synthesized_knowledge", []))
            for domain, output in result.minister_outputs.items()
            if output.kis_data
        }
        result.kis_summary = {
            "total_kis_items": sum(kis_counts.values()),
            "domains_with_kis": len([c for c in kis_counts.values() if c > 0]),
            "kis_per_domain": kis_counts
        }
        
        trace("minister_flow_complete", {
            "ministers_executed": len(result.minister_outputs),
            "judges_observed": len(result.judge_observations),
            "total_kis_items": result.kis_summary["total_kis_items"]
        })
        
        return result
    
    def invoke_prime_confident(self, flow_result: MinisterFlowResult, prime_confident_instance) -> MinisterFlowResult:
        """Invoke Prime Confident with aggregated minister output."""
        if not prime_confident_instance:
            flow_result.execution_trace.append("Prime Confident: Not available (None)")
            return flow_result
        
        try:
            # Package all minister recommendations for Prime Confident
            def _get_attr(obj, name, default=None):
                try:
                    if isinstance(obj, dict):
                        return obj.get(name, default)
                    return getattr(obj, name, default)
                except Exception:
                    return default

            minister_positions = {}
            for domain, output in flow_result.minister_outputs.items():
                minister_positions[domain] = {
                    "stance": _get_attr(output, "stance", "unknown"),
                    "confidence": float(_get_attr(output, "confidence", 0.0) or 0.0),
                    "red_line": bool(_get_attr(output, "red_line", _get_attr(output, "red_line_triggered", False)))
                }

            judge_positions = {}
            for domain, output in flow_result.judge_observations.items():
                judge_positions[domain] = {
                    "stance": _get_attr(output, "stance", "unknown"),
                    "confidence": float(_get_attr(output, "confidence", 0.0) or 0.0),
                    "advisory": True
                }
            
            # This is where Prime Confident makes final decision
            prime_decision = {
                "ministers_input": minister_positions,
                "judges_input": judge_positions,
                "council_recommendation": flow_result.council_recommendation.recommendation
                    if flow_result.council_recommendation else None,
                "flow_complete": True
            }
            
            flow_result.prime_decision = prime_decision
            flow_result.execution_trace.append(
                "Prime Confident: Flow complete, decision ready"
            )
            
            trace("prime_confident_flow", {
                "ministers_input_count": len(minister_positions),
                "judges_input_count": len(judge_positions),
                "decision_ready": True
            })
            
        except Exception as e:
            trace("prime_confident_flow_error", {"error": str(e)})
            flow_result.execution_trace.append(f"Prime Confident: ERROR - {str(e)}")
        
        return flow_result


# Singleton orchestrator
_orchestrator_instance = None


def get_orchestrator(llm=None) -> MinisterFlowOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MinisterFlowOrchestrator(llm=llm)
    return _orchestrator_instance
