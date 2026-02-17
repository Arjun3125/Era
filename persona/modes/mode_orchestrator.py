"""
MODE ORCHESTRATOR - Controls pipeline based on conversation mode.

Different modes invoke different reasoning pathways:
- QUICK MODE: 1:1 conversation, direct LLM response, no council
- WAR MODE: Victory-focused, aggressive, Risk/Power/Strategy focus
- MEETING MODE: Structured debate, 3-5 relevant ministers
- DARBAR MODE: Full council, all 19 ministers, deep wisdom

This is the critical control layer that changes the entire decision pipeline.
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ModeResponse:
    """Response with mode metadata."""
    text: str
    mode: str
    ministers_involved: List[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.5
    feature_flags: Dict[str, bool] = field(default_factory=dict)


class ModeStrategy(ABC):
    """Abstract base for mode-specific behavior."""
    
    @abstractmethod
    def decide_ministers_to_invoke(self, context: Dict[str, Any]) -> List[str]:
        """Which ministers should be involved?"""
        pass
    
    @abstractmethod
    def aggregate_minister_inputs(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """How to combine minister positions?"""
        pass
    
    @abstractmethod
    def frame_decision(self, user_input: str, context: Dict[str, Any]) -> str:
        """How to frame the decision problem?"""
        pass
    
    @abstractmethod
    def should_invoke_council(self) -> bool:
        """Should we run ministerial council?"""
        pass


class QuickModeStrategy(ModeStrategy):
    """
    QUICK MODE: 1:1 Conversation
    
    - Direct LLM response
    - NO ministerial council
    - Intuitive, personal, fast
    - Suitable for: initial exploration, casual advice, emotional support
    """
    
    def decide_ministers_to_invoke(self, context: Dict[str, Any]) -> List[str]:
        """No ministers in quick mode."""
        return []
    
    def should_invoke_council(self) -> bool:
        return False
    
    def frame_decision(self, user_input: str, context: Dict[str, Any]) -> str:
        """Frame as personal conversation, not analytical."""
        return f"""
You are in QUICK MODE - a 1:1 mentor conversation.

Characteristics:
- Be personal, intuitive, exploratory
- Ask clarifying questions
- Build rapport
- Don't over-analyze
- Respond like a thoughtful mentor

User concern:
{user_input}

Respond naturally, warmly, with genuine interest.
"""
    
    def aggregate_minister_inputs(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """No aggregation needed in quick mode."""
        return {}


class WarModeStrategy(ModeStrategy):
    """
    WAR MODE: Victory-Focused Decision Making
    
    - Frame: "How do we WIN?"
    - Ministers: Risk, Power, Strategy, Technology, Timing
    - Optimize for: Victory, speed, competitive advantage
    - May sacrifice: Ethics (NO), long-term gain for short-term wins
    - Use case: Competitive situations, defensive crises, aggressive goals
    - Red lines: NEVER ignore existential risks or irreversible damage
    """
    
    def decide_ministers_to_invoke(self, context: Dict[str, Any]) -> List[str]:
        """Only invoke ministers focused on winning."""
        return [
            "risk",               # Downside protection
            "power",              # Leverage & advantage
            "grand_strategist",   # Strategic wins
            "technology",         # Tactical advantage
            "timing",             # Strike when ready
        ]
    
    def should_invoke_council(self) -> bool:
        return True
    
    def frame_decision(self, user_input: str, context: Dict[str, Any]) -> str:
        """Frame as: How do we WIN?"""
        return f"""
You are in WAR MODE - optimizing for VICTORY.

Strategic Frame: "How do we WIN this?"

Decision Criteria:
- Speed: Act decisively and quickly
- Advantage: Maximize our leverage
- Victory: Achieve the primary objective
- Protection: Minimize downside risk

This mode may sacrifice:
- Long-term relationships
- Ethical nuance
- Cautious, slow deliberation

But this mode MUST NEVER ignore:
- Existential risks (death, bankruptcy, legal trouble)
- Irreversible damage that outlasts the victory

Ministers advising: Risk, Power, Strategy, Technology, Timing
Goal: Consensus on the winning move

User situation:
{user_input}

Facilitate war council debate. Recommend the aggressive-but-smart winning strategy.
Ensure Risk minister's existential concerns are heard.
"""
    
    def aggregate_minister_inputs(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """In war mode: Support aggressive stances, but heed red lines."""
        war_aligned = sum(1 for p in positions.values() if p.get("stance") == "support")
        total = len(positions)
        red_lines = [m for m, p in positions.items() if p.get("red_line_triggered")]
        
        return {
            "war_alignment": war_aligned / total if total > 0 else 0,
            "recommendation_type": "aggressive_if_war_aligned_else_cautious",
            "red_line_concerns": red_lines,
            "ethical_override_allowed": False,  # NEVER override ethics
        }


class MeetingModeStrategy(ModeStrategy):
    """
    MEETING MODE: Structured Debate
    
    - Structure: Invoke 3-5 relevant ministers, each presents perspective
    - Synthesis: Combine into balanced view
    - Suitable for: Complex decisions, multi-stakeholder issues
    - Goal: Create consensus among diverse viewpoints
    """
    
    def decide_ministers_to_invoke(self, context: Dict[str, Any]) -> List[str]:
        """Select 3-5 ministers relevant to detected domains."""
        domains = context.get("domains", [])
        
        # Map domains to relevant ministers
        domain_minister_map = {
            "career": ["grand_strategist", "psychology", "timing"],
            "financial": ["risk", "optionality", "data"],
            "relationships": ["diplomacy", "psychology", "legitimacy"],
            "health": ["psychology", "timing", "risk"],
            "strategy": ["grand_strategist", "intelligence", "timing"],
            "power": ["power", "diplomacy", "conflict"],
            "ethics": ["legitimacy", "truth", "discipline"],
            "innovation": ["technology", "grand_strategist", "risk"],
        }
        
        # Gather ministers based on detected domains
        ministers = set()
        for domain in domains:
            if domain in domain_minister_map:
                ministers.update(domain_minister_map[domain][:2])  # Take top 2 per domain
        
        # Always include risk as sanity check
        ministers.add("risk")
        
        # Cap at 5 ministers
        return list(ministers)[:5]
    
    def should_invoke_council(self) -> bool:
        return True
    
    def frame_decision(self, user_input: str, context: Dict[str, Any]) -> str:
        """Frame as structured debate."""
        ministers = self.decide_ministers_to_invoke(context)
        return f"""
You are in MEETING MODE - structured debate and consensus building.

Structure:
1. Each minister presents their perspective
2. Identify points of agreement
3. Identify points of disagreement
4. Synthesize into balanced recommendation

Ministers present:
{', '.join(ministers)}

Decision format:
- Where do they agree strongly?
- Where do they disagree? Why?
- What's the balanced path that respects multiple viewpoints?
- What tradeoffs exist?

User situation:
{user_input}

Guide a thoughtful, structured debate. Show reasoning. Synthesize clearly.
"""
    
    def aggregate_minister_inputs(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Consensus-seeking aggregation."""
        stances = [p.get("stance") for p in positions.values()]
        support_count = sum(1 for s in stances if s == "support")
        oppose_count = sum(1 for s in stances if s == "oppose")
        total = len(stances)
        
        # High consensus if 60%+ align
        consensus_quality = "high" if abs(support_count - oppose_count) >= total * 0.6 else "mixed"
        
        return {
            "consensus_quality": consensus_quality,
            "support_ratio": support_count / total if total > 0 else 0,
            "recommendation_type": "balanced",
            "should_note_disagreement": oppose_count > 0,
            "disagreement_count": oppose_count,
        }


class DarbarModeStrategy(ModeStrategy):
    """
    DARBAR MODE: Full Council, Deep Wisdom
    
    - Invoke: ALL 19 voting ministers + judges
    - Structure: Full doctrine-driven council deliberation
    - Synthesis: Complete reasoning, consensus building
    - Red lines: Legitimacy, Truth, Fundamental harm
    - Suitable for: High-stakes decisions, existential questions, final arbitration
    """
    
    def decide_ministers_to_invoke(self, context: Dict[str, Any]) -> List[str]:
        """Invoke ALL ministers for full council."""
        return [
            "adaptation", "conflict", "diplomacy", "data", "discipline",
            "grand_strategist", "intelligence", "timing", "risk", "power",
            "psychology", "technology", "legitimacy", "truth", "narrative",
            "resources", "optionality", "sovereign",
        ]
    
    def should_invoke_council(self) -> bool:
        return True
    
    def frame_decision(self, user_input: str, context: Dict[str, Any]) -> str:
        """Frame as deep council deliberation."""
        return f"""
You are DARBAR MODE - Full Council Deliberation.

This is a high-stakes decision requiring deep, multi-perspective wisdom.

Process:
1. Each of 18 ministers states their position (doctrine-driven)
2. Identify strong consensus and deep disagreement
3. Surface any doctrine red lines
4. Synthesize into comprehensive wisdom

RED LINES (blocks any recommendation):
- Legitimacy violations (fraud, corruption, illegal acts)
- Truth violations (deception, manipulation, dishonesty)
- Fundamental harm (death, irreversible damage, existential risk)

Ministers participating:
Adaptation, Conflict, Diplomacy, Data, Discipline,
Grand Strategist, Intelligence, Timing, Risk, Power,
Psychology, Technology, Legitimacy, Truth, Narrative,
Resources, Optionality, Sovereign

User situation:
{user_input}

Facilitate a deep, multi-perspective council deliberation.
Show the reasoning from multiple viewpoints.
Note disagreements and their sources.
Synthesize into final wisdom that respects doctrine constraints.
If red lines are triggered, state them clearly and explain why recommendation is blocked.
"""
    
    def aggregate_minister_inputs(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Full consensus-seeking with doctrine respect."""
        red_lines = [m for m, p in positions.items() if p.get("red_line_triggered")]
        support = sum(1 for p in positions.values() if p.get("stance") == "support")
        total = len(positions)
        
        return {
            "red_line_concerns": red_lines,
            "consensus_strength": support / total if total > 0 else 0,
            "recommendation_type": "doctrine_compliant_consensus",
            "requires_prime_confident_review": len(red_lines) > 0,
            "total_ministers": total,
        }


class ModeOrchestrator:
    """
    Central orchestrator for mode-specific decision making.
    
    Routes the entire decision pipeline based on current mode.
    This is the critical control layer that shapes how Persona reasons.
    """
    
    def __init__(self):
        """Initialize all mode strategies."""
        self.strategies: Dict[str, ModeStrategy] = {
            "quick": QuickModeStrategy(),
            "war": WarModeStrategy(),
            "meeting": MeetingModeStrategy(),
            "darbar": DarbarModeStrategy(),
        }
        
        # Default mode
        self.current_mode = "meeting"
    
    def set_mode(self, mode: str) -> bool:
        """Set the current mode. Returns True if valid."""
        if mode in self.strategies:
            self.current_mode = mode
            return True
        return False
    
    def get_current_mode(self) -> str:
        """Get current mode."""
        return self.current_mode
    
    def get_strategy(self, mode: Optional[str] = None) -> ModeStrategy:
        """Get the strategy for specified mode (or current mode)."""
        mode = mode or self.current_mode
        return self.strategies.get(mode, self.strategies["meeting"])
    
    def should_invoke_council(self, mode: Optional[str] = None) -> bool:
        """Does this mode use ministerial council?"""
        strategy = self.get_strategy(mode)
        return strategy.should_invoke_council()
    
    def get_ministers_for_mode(
        self,
        mode: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Which ministers to invoke for this mode?"""
        context = context or {}
        strategy = self.get_strategy(mode)
        return strategy.decide_ministers_to_invoke(context)
    
    def frame_for_mode(
        self,
        user_input: str,
        mode: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get mode-specific framing prompt."""
        context = context or {}
        strategy = self.get_strategy(mode)
        return strategy.frame_decision(user_input, context)
    
    def aggregate_for_mode(
        self,
        positions: Dict[str, Any],
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aggregate minister positions according to mode rules."""
        strategy = self.get_strategy(mode)
        return strategy.aggregate_minister_inputs(positions)
    
    def list_modes(self) -> List[str]:
        """List all available modes."""
        return list(self.strategies.keys())
    
    def get_mode_description(self, mode: str) -> str:
        """Get human-readable description of a mode."""
        descriptions = {
            "quick": "1:1 mentoring - intuitive, personal, no council",
            "war": "Victory-focused - aggressive, rapid, Risk/Power/Strategy focus",
            "meeting": "Structured debate - balanced, 3-5 relevant ministers",
            "darbar": "Full council wisdom - all 18 ministers, deep deliberation",
        }
        return descriptions.get(mode, "Unknown mode")
