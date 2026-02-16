r"""
Meeting Mode Flow - 2-3 Minister Discussion & Debate Branch

This is a conditional branch in the main orchestrator flow that:
1. Selects 2-3 relevant ministers based on topic
2. Executes minister analysis in parallel
3. Synthesizes shared output from debate
4. Passes synthesis to Prime Confident for viability check
5. Returns viability assessment + recommendation

Location: c:\era\sovereign\ministers\meeting_flow.py
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from . import MinisterModuleOutput
from persona.knowledge_engine import synthesize_knowledge
from persona.trace import trace


class TopicCategory(Enum):
    """Topic classification for minister selection."""
    STRATEGIC = "strategic"          # Grand strategist, power, timing
    RISK_ASSESSMENT = "risk"         # Risk, truth, discipline
    RELATIONSHIP = "relationship"    # Diplomacy, legitimacy, narrative
    DATA_DRIVEN = "data"             # Data, adaptation, intelligence
    CONFLICT = "conflict"            # Conflict, war_mode, sovereignty
    OPPORTUNITY = "opportunity"      # Optionality, psychology, power


@dataclass
class MinisterSelection:
    """Selected ministers for meeting discussion."""
    primary: str                      # Lead minister for topic
    secondary: List[str] = field(default_factory=list)  # 1-2 supporting ministers
    keywords: List[str] = field(default_factory=list)


@dataclass
class DebateOutput:
    """Output from minister debate phase."""
    minister_domain: str
    stance: str
    confidence: float
    reasoning: str
    kis_points: List[Dict[str, Any]] = field(default_factory=list)
    red_lines_triggered: List[str] = field(default_factory=list)


@dataclass
class MeetingSynthesis:
    """Synthesized output from 2-3 minister meeting."""
    topic: str
    selected_ministers: List[str]
    debate_outputs: Dict[str, DebateOutput]
    
    # Synthesis results
    shared_recommendation: str
    consensus_strength: float          # 0.0-1.0: how much agreement
    key_risks_identified: List[str]
    key_opportunities: List[str]
    
    # Viability assessment
    viability_score: float             # 0.0-1.0: how viable is recommendation
    viability_reason: str
    prime_confident_ready: bool        # Pass to Prime for final check


def select_ministers_for_topic(topic: str, user_input: str) -> MinisterSelection:
    """Select 2-3 most relevant ministers for the discussion topic."""
    
    topic_lower = topic.lower() + " " + user_input.lower()
    
    # Strategy/planning keywords
    if any(word in topic_lower for word in ["strategy", "plan", "vision", "direction", "long-term"]):
        return MinisterSelection(
            primary="grand_strategist",
            secondary=["timing", "power"],
            keywords=["strategy", "planning", "vision"]
        )
    
    # Risk/safety keywords
    if any(word in topic_lower for word in ["risk", "danger", "safe", "survival", "threat", "exposure"]):
        return MinisterSelection(
            primary="risk_resources",
            secondary=["truth", "discipline"],
            keywords=["risk", "safety", "viability"]
        )
    
    # Relationship/collaboration keywords
    if any(word in topic_lower for word in ["alliance", "partner", "trust", "relationship", "cooperation", "negotiate"]):
        return MinisterSelection(
            primary="diplomacy",
            secondary=["legitimacy", "narrative"],
            keywords=["relationship", "trust", "collaboration"]
        )
    
    # Data/analysis keywords
    if any(word in topic_lower for word in ["data", "metric", "measure", "analyze", "accurate", "knowledge"]):
        return MinisterSelection(
            primary="data",
            secondary=["adaptation", "intelligence"],
            keywords=["data", "analysis", "accuracy"]
        )
    
    # Conflict/competition keywords
    if any(word in topic_lower for word in ["conflict", "competition", "oppose", "compete", "battle", "war"]):
        return MinisterSelection(
            primary="conflict",
            secondary=["war_mode", "power"],
            keywords=["conflict", "competition", "opposition"]
        )
    
    # Opportunity/growth keywords
    if any(word in topic_lower for word in ["opportunity", "growth", "expand", "scale", "innovative", "new"]):
        return MinisterSelection(
            primary="optionality",
            secondary=["psychology", "adaptation"],
            keywords=["opportunity", "innovation", "growth"]
        )
    
    # Default: balanced selection
    return MinisterSelection(
        primary="truth",
        secondary=["timing", "discipline"],
        keywords=["general", "analysis"]
    )


def execute_minister_analysis(minister_module, topic: str, user_input: str, 
                               context: Dict[str, Any]) -> DebateOutput:
    """Execute single minister analysis for meeting discussion."""
    
    try:
        # Analyze with minister module
        output = minister_module.analyze(user_input, context)
        
        # Extract KIS points for synthesis
        kis_points = []
        if output.kis_data:
            # Extract key knowledge items
            if "synthesized_knowledge" in output.kis_data:
                kis_points = output.kis_data["synthesized_knowledge"][:3]  # Top 3
        
        return DebateOutput(
            minister_domain=minister_module.domain,
            stance=output.stance,
            confidence=output.confidence,
            reasoning=output.reasoning,
            kis_points=kis_points,
            red_lines_triggered=[output.red_line] if output.red_line else []
        )
    except Exception as e:
        trace(f"ERROR: Minister {minister_module.domain} analysis failed: {e}")
        return DebateOutput(
            minister_domain=minister_module.domain,
            stance="unable_to_analyze",
            confidence=0.0,
            reasoning=f"Analysis failed: {str(e)}"
        )


def synthesize_meeting_debate(selected_ministers: List[str], 
                               debate_outputs: Dict[str, DebateOutput],
                               user_input: str) -> MeetingSynthesis:
    """Synthesize 2-3 minister debate into shared recommendation."""
    
    # Extract stances
    stances = [output.stance for output in debate_outputs.values()]
    confidence_scores = [output.confidence for output in debate_outputs.values()]
    
    # Calculate consensus strength
    support_count = sum(1 for s in stances if s in ["support", "strongly_support"])
    consensus_strength = support_count / len(stances) if stances else 0.0
    
    # Identify red lines
    red_lines = []
    for output in debate_outputs.values():
        red_lines.extend(output.red_lines_triggered)
    
    # Determine shared recommendation
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    if any(line for line in red_lines):
        shared_recommendation = "caution_red_line_triggered"
        viability_score = 0.3  # Low viability due to red line
        viability_reason = f"Red lines triggered by: {', '.join(set(red_lines))}"
    elif consensus_strength >= 0.75:
        shared_recommendation = "proceed_with_confidence"
        viability_score = min(0.9, avg_confidence)
        viability_reason = f"Strong consensus ({consensus_strength:.0%}) among ministers"
    elif consensus_strength >= 0.5:
        shared_recommendation = "proceed_with_caution"
        viability_score = 0.6
        viability_reason = f"Moderate consensus ({consensus_strength:.0%}), proceed cautiously"
    else:
        shared_recommendation = "escalate_or_research"
        viability_score = 0.4
        viability_reason = f"Low consensus ({consensus_strength:.0%}), requires more analysis"
    
    # Identify opportunities and risks
    opportunities = []
    risks = []
    
    for domain, output in debate_outputs.items():
        if "opportunity" in output.reasoning.lower():
            opportunities.append(f"{domain}: {output.reasoning[:50]}...")
        if "risk" in output.reasoning.lower() or output.red_lines_triggered:
            risks.append(f"{domain}: {output.reasoning[:50]}...")
    
    return MeetingSynthesis(
        topic=user_input[:100],
        selected_ministers=selected_ministers,
        debate_outputs=debate_outputs,
        shared_recommendation=shared_recommendation,
        consensus_strength=consensus_strength,
        key_risks_identified=list(set(risks))[:3],
        key_opportunities=list(set(opportunities))[:3],
        viability_score=viability_score,
        viability_reason=viability_reason,
        prime_confident_ready=(viability_score >= 0.4)  # Ready if minimum viability
    )


def meeting_mode_flow(all_minister_modules: Dict[str, Any],
                     topic: str,
                     user_input: str,
                     context: Dict[str, Any],
                     llm_adapter: Optional[Any] = None) -> Tuple[MeetingSynthesis, bool]:
    """
    Main meeting mode flow - branch in orchestrator.
    
    Returns:
        (synthesis, should_continue_to_prime) - synthesis and decision to proceed to Prime
    """
    
    trace("=== MEETING MODE FLOW INITIATED ===")
    trace(f"Topic: {topic}")
    trace(f"User input: {user_input[:80]}...")
    
    # Step 1: Select relevant ministers
    minister_selection = select_ministers_for_topic(topic, user_input)
    trace(f"Selected ministers: {minister_selection.primary} + {minister_selection.secondary}")
    
    # Step 2: Get minister modules
    selected_minister_names = [minister_selection.primary] + minister_selection.secondary
    selected_modules = []
    
    for name in selected_minister_names:
        if name in all_minister_modules:
            selected_modules.append(all_minister_modules[name])
        else:
            trace(f"WARNING: Minister module '{name}' not found")
    
    if not selected_modules:
        trace("ERROR: No minister modules selected, aborting meeting flow")
        return None, False
    
    # Step 3: Execute parallel minister analysis
    trace(f"Executing analysis for {len(selected_modules)} ministers...")
    debate_outputs = {}
    
    for minister_module in selected_modules:
        output = execute_minister_analysis(
            minister_module, 
            topic, 
            user_input, 
            context
        )
        debate_outputs[minister_module.domain] = output
        trace(f"  - {minister_module.domain}: {output.stance} (confidence: {output.confidence:.2f})")
    
    # Step 4: Synthesize debate
    trace("Synthesizing minister debate...")
    synthesis = synthesize_meeting_debate(
        selected_minister_names,
        debate_outputs,
        user_input
    )
    
    trace(f"Synthesis recommendation: {synthesis.shared_recommendation}")
    trace(f"Viability score: {synthesis.viability_score:.2f}")
    trace(f"Consensus strength: {synthesis.consensus_strength:.0%}")
    
    # Optionally have the LLM evaluate viability more carefully
    if llm_adapter:
        # Build a compact synthesis text for evaluation
        eval_text_parts = [f"Recommendation: {synthesis.shared_recommendation}",
                           f"Reason: {synthesis.viability_reason}"]
        for domain, out in debate_outputs.items():
            eval_text_parts.append(f"{domain}: {out.reasoning[:200]}")
        eval_text = "\n".join(eval_text_parts)

        score, reason = llm_adapter.evaluate_viability(eval_text)
        try:
            synthesis.viability_score = float(score)
        except Exception:
            synthesis.viability_score = synthesis.viability_score
        if reason:
            synthesis.viability_reason = reason

        # Use a slightly higher threshold when LLM evaluates
        should_continue = synthesis.viability_score >= 0.65
    else:
        # Step 5: Determine if ready for Prime Confident (fallback)
        should_continue = synthesis.prime_confident_ready
    
    if should_continue:
        trace("READY FOR PRIME CONFIDENT - passing synthesis for viability check")
    else:
        trace("ESCALATE - low viability, requires leadership review")
    
    return synthesis, should_continue
