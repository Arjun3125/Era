"""
Dynamic Council - Adjusts behavior based on conversation mode and ministers involved.

This module wraps CouncilAggregator with mode-aware council behavior, allowing
the council composition and aggregation logic to change based on the selected mode
(QUICK, WAR, MEETING, or DARBAR).
"""

from typing import Dict, List, Any, Optional
from ..modes.mode_orchestrator import ModeOrchestrator
from . import CouncilAggregator


class DynamicCouncil:
    """
    Wraps CouncilAggregator with mode-aware behavior.
    
    Routes council composition and aggregation based on current decision mode:
    - QUICK: No council (direct LLM response)
    - WAR: 5 focused ministers (Risk, Power, Strategy, Tech, Timing)
    - MEETING: 3-5 domain-relevant ministers
    - DARBAR: All 18+ ministers with full deliberation
    """
    
    def __init__(self, llm=None):
        """Initialize with base council and mode orchestrator."""
        self.base_council = CouncilAggregator(llm=llm)
        self.mode_orchestrator = ModeOrchestrator()
        self.current_mode = "meeting"  # Default mode
        self.llm = llm
    
    def set_mode(self, mode: str) -> bool:
        """
        Set the current decision mode.
        
        Returns True if mode was valid and set, False otherwise.
        """
        if self.mode_orchestrator.set_mode(mode):
            self.current_mode = mode
            return True
        return False
    
    def convene_for_mode(
        self,
        mode: str,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convene council appropriate for current mode.
        
        QUICK MODE: Returns immediately without invoking council
        WAR MODE: 5 ministers focused on victory
        MEETING MODE: 3-5 ministers for balanced consensus
        DARBAR MODE: All ministers for deep deliberation
        
        Args:
            mode: The mode to use (quick, war, meeting, darbar)
            user_input: The user's question/input
            context: Conversation context (domains, recent turns, etc.)
        
        Returns:
            Dict with council results, minister positions, recommendations
        """
        self.current_mode = mode
        
        # Quick mode: No council needed
        if not self.mode_orchestrator.should_invoke_council(mode):
            return {
                "outcome": "quick_mode_direct_response",
                "recommendation": "use_direct_llm_response",
                "mode": mode,
                "ministers_involved": [],
                "reasoning": "QUICK mode does not invoke ministerial council",
            }
        
        # All other modes: Convene council with mode-appropriate ministers
        return self._convene_mode_council(mode, user_input, context)
    
    def _convene_mode_council(
        self,
        mode: str,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method: Convene council with ministers appropriate for mode.
        """
        # Get minister names for this mode
        minister_names = self.mode_orchestrator.get_ministers_for_mode(mode, context)
        
        # Collect positions from only the relevant ministers
        minister_positions = {}
        failed_ministers = []
        
        for minister_name in minister_names:
            if minister_name in self.base_council.ministers:
                minister = self.base_council.ministers[minister_name]
                try:
                    position = minister.analyze(user_input, context)
                    minister_positions[minister_name] = {
                        "stance": position.stance,
                        "confidence": position.confidence,
                        "reasoning": getattr(position, "reasoning", ""),
                        "red_line_triggered": getattr(position, "red_line_triggered", False),
                    }
                except Exception as e:
                    failed_ministers.append(f"{minister_name}:{str(e)}")
        
        # Aggregate according to mode rules
        mode_aggregation = self.mode_orchestrator.aggregate_for_mode(
            minister_positions,
            mode
        )
        
        # Calculate support/oppose counts
        support_count = sum(
            1 for p in minister_positions.values()
            if p.get("stance") == "support"
        )
        oppose_count = sum(
            1 for p in minister_positions.values()
            if p.get("stance") == "oppose"
        )
        neutral_count = len(minister_positions) - support_count - oppose_count
        
        # Determine recommendation based on mode
        recommendation = self._determine_recommendation(
            mode,
            support_count,
            oppose_count,
            neutral_count,
            minister_positions
        )
        
        # Collect red line concerns
        red_lines = [
            name for name, pos in minister_positions.items()
            if pos.get("red_line_triggered", False)
        ]
        
        return {
            "outcome": mode_aggregation.get("recommendation_type", "standard_consensus"),
            "recommendation": recommendation,
            "mode": mode,
            "ministers_involved": list(minister_positions.keys()),
            "ministers_failed": failed_ministers,
            "minister_positions": minister_positions,
            "mode_metadata": mode_aggregation,
            "support_count": support_count,
            "oppose_count": oppose_count,
            "neutral_count": neutral_count,
            "red_line_concerns": red_lines,
            "consensus_strength": (
                max(support_count, oppose_count) /
                len(minister_positions) if minister_positions else 0
            ),
            "total_ministers_consulted": len(minister_positions),
        }
    
    def _determine_recommendation(
        self,
        mode: str,
        support: int,
        oppose: int,
        neutral: int,
        positions: Dict[str, Any]
    ) -> str:
        """
        Determine final recommendation based on mode logic.
        """
        total = support + oppose + neutral
        if total == 0:
            return "insufficient_data"
        
        if mode == "quick":
            # Should not reach here (quick returns early), but just in case
            return "direct_response"
        
        elif mode == "war":
            # War mode: Prioritize winning, but respect red lines
            if positions and any(p.get("red_line_triggered") for p in positions.values()):
                return "red_line_block_override_needed"
            if support >= oppose:
                return "aggressive_proceed"
            else:
                return "defensive_hold_or_pivot"
        
        elif mode == "meeting":
            # Meeting mode: Balanced consensus
            if support > oppose + neutral:
                return "strong_consensus_support"
            elif oppose > support + neutral:
                return "strong_consensus_oppose"
            else:
                return "mixed_consensus_with_tradeoffs"
        
        elif mode == "darbar":
            # Darbar mode: Doctrine-driven, full consensus
            if positions and any(p.get("red_line_triggered") for p in positions.values()):
                return "red_line_blocks_recommendation"
            
            consensus_pct = max(support, oppose) / total
            if consensus_pct >= 0.8:
                return "strong_doctrine_aligned_consensus"
            elif consensus_pct >= 0.6:
                return "consensus_with_noted_dissent"
            else:
                return "deep_disagreement_defer_decision"
        
        else:
            return "unknown_mode"
    
    def get_current_mode(self) -> str:
        """Get the current decision mode."""
        return self.current_mode
    
    def get_mode_description(self, mode: str) -> str:
        """Get human-readable description of a mode."""
        return self.mode_orchestrator.get_mode_description(mode)
    
    def list_available_modes(self) -> List[str]:
        """List all available modes."""
        return self.mode_orchestrator.list_modes()
