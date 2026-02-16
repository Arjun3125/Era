"""
Ministerial Cognitive Architecture (MCA) - Domain-specific decision advisors.

Each Minister loads their doctrine from C:/era/data/doctrine/locked/*.yaml and analyzes
user input through their canonical worldview and mental models. Doctrine includes:
- Core worldview and mental models
- Authority (what they can/cannot do)
- Triggers for speaking vs staying silent
- Known failure patterns
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from .knowledge_engine import synthesize_knowledge
from .doctrine_loader import DoctrineLoader, DoctrinalCanon
from .trace import trace


@dataclass
class MinisterPosition:
    """Output from a Minister's analysis."""
    domain: str
    stance: str  # "support", "oppose", or "neutral"
    confidence: float  # 0-1
    reasoning: str
    red_line_triggered: bool = False
    concerns: Optional[list] = None
    recommendations: Optional[list] = None
    doctrine_applied: bool = False  # Whether doctrine was used in analysis


class Minister(ABC):
    """Base class for domain-specific ministers."""
    
    def __init__(self, domain: str, llm=None):
        self.domain = domain
        self.llm = llm
        # Load doctrine for this minister
        self.doctrine: Optional[DoctrinalCanon] = DoctrineLoader.load(domain)
        # Extract key phrases from canonical worldview for matching
        self.worldview_keywords = []
        if self.doctrine:
            self.worldview_keywords = DoctrineLoader.extract_worldview_keywords(self.doctrine.canon_text)
    
    @abstractmethod
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        """Analyze user input from domain perspective and return position."""
        pass
    
    def _extract_stance_confidence(self, analysis: Dict[str, Any]) -> tuple:
        """Helper to extract stance and confidence from LLM analysis."""
        stance = analysis.get("stance", "neutral").lower()
        if stance not in ["support", "oppose", "neutral"]:
            stance = "neutral"
        confidence = float(analysis.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # Clamp 0-1
        return stance, confidence
    
    def _score_worldview_match(self, user_input: str) -> tuple:
        """
        Score how well user input aligns with this minister's doctrine worldview.
        Returns (stance, confidence, doctrine_applied)
        """
        if not self.doctrine or not self.worldview_keywords:
            return None, None, False
        
        user_input_lower = user_input.lower()
        
        # Count keyword matches
        matches = 0
        for keyword in self.worldview_keywords:
            if keyword in user_input_lower:
                matches += 1
        
        if matches == 0:
            return None, None, False
        
        # Calculate confidence based on match strength
        match_ratio = matches / len(self.worldview_keywords) if self.worldview_keywords else 0
        confidence = min(0.95, 0.5 + (match_ratio * 0.45))  # 0.5-0.95 range
        
        # Stance: If worldview matches, this minister supports it
        stance = "support" if match_ratio > 0.3 else "neutral"
        
        return stance, confidence, True
    
    def _apply_prohibitions(self, stance: str, user_input: str) -> tuple:
        """Apply doctrine prohibitions to moderate stance if needed."""
        if not self.doctrine or not self.doctrine.prohibitions:
            return stance, False
        
        user_input_lower = user_input.lower()
        
        # Check each prohibition
        for prohibition in self.doctrine.prohibitions:
            prohibition_lower = prohibition.lower()
            
            # If this action violates doctrine, oppose it
            if prohibition_lower in user_input_lower or any(word in prohibition_lower for word in user_input_lower.split()):
                return "oppose", True
        
        return stance, False



class MinisterOfAdaptation(Minister):
    """Detects need for change and system evolution."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        """Assess whether change/adaptation is needed in the current situation."""
        reasoning = []
        
        # Try doctrine-based analysis first
        doctrine_stance, doctrine_conf, doctrine_applied = self._score_worldview_match(user_input)
        if doctrine_applied:
            reasoning.append("Doctrine worldview match detected")
            stance = doctrine_stance
            confidence = doctrine_conf
        else:
            # Fallback to heuristic analysis
            domains = context.get("domains", [])
            turn_count = context.get("turn_count", 0)
            
            if domains and turn_count > 5:
                reasoning.append("Pattern persistence detected; adaptation may be needed")
            
            # Get domain-specific knowledge
            try:
                kis = synthesize_knowledge(user_input, active_domains=["adaptation"], domain_confidence=0.8)
                knowledge_items = kis.get("synthesized_knowledge", [])
                has_adaptation_knowledge = len(knowledge_items) > 0
                if has_adaptation_knowledge:
                    reasoning.append("Adaptation knowledge base confirms change signals present")
            except:
                has_adaptation_knowledge = False
            
            stance = "support" if has_adaptation_knowledge else "neutral"
            confidence = 0.7 if has_adaptation_knowledge else 0.4
        
        trace("minister_adaptation", {"stance": stance, "confidence": confidence, "doctrine_used": doctrine_applied})
        
        return MinisterPosition(
            domain="adaptation",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "No clear adaptation signal",
            red_line_triggered=False,
            concerns=["system_stagnation", "decay"] if stance == "support" else [],
            doctrine_applied=doctrine_applied
        )



class MinisterOfConflict(Minister):
    """Assesses adversarial dynamics and negotiation positions."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for conflict language
        conflict_words = {"vs", "against", "opposing", "competing", "threat", "attack", "defensive"}
        has_conflict_language = any(word in user_input.lower() for word in conflict_words)
        
        if has_conflict_language:
            reasoning.append("Adversarial language detected")
            stance = "oppose"  # Conflict minister cautions against escalation
            confidence = 0.8
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_conflict", {"stance": stance, "conflict_language": has_conflict_language})
        
        return MinisterPosition(
            domain="conflict",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "No conflict signal present",
            red_line_triggered=has_conflict_language and "attack" in user_input.lower(),
        )


class MinisterOfDiplomacy(Minister):
    """Evaluates relationship impact and stakeholder considerations."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for stakeholder/relationship language
        relationship_words = {"partner", "stakeholder", "relationship", "trust", "reputation", "ally"}
        has_relationship_language = any(word in user_input.lower() for word in relationship_words)
        
        if has_relationship_language:
            reasoning.append("Stakeholder impact detected")
            stance = "support"  # Diplomacy advocates for relational approaches
            confidence = 0.75
        else:
            stance = "neutral"
            confidence = 0.4
        
        trace("minister_diplomacy", {"stance": stance, "relationship_focus": has_relationship_language})
        
        return MinisterPosition(
            domain="diplomacy",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Generic advice",
            recommendations=["build_consensus", "stakeholder_alignment"] if stance == "support" else []
        )


class MinisterOfData(Minister):
    """Insists on evidence-based reasoning."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for empirical language
        empirical_words = {"data", "evidence", "measure", "test", "metric", "proof", "study"}
        has_empirical_language = any(word in user_input.lower() for word in empirical_words)
        
        # Check for speculative language (opposite)
        speculative_words = {"assume", "probably", "guess", "think", "maybe", "could be"}
        is_speculative = any(word in user_input.lower() for word in speculative_words)
        
        if has_empirical_language:
            stance = "support"
            confidence = 0.85
            reasoning.append("Evidence-based reasoning present")
        elif is_speculative:
            stance = "oppose"
            confidence = 0.7
            reasoning.append("Speculative reasoning without data")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_data", {"stance": stance, "empirical": has_empirical_language, "speculative": is_speculative})
        
        return MinisterPosition(
            domain="data",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Data quality neutral",
            red_line_triggered=is_speculative and not has_empirical_language
        )


class MinisterOfDiscipline(Minister):
    """Ensures consistency and adherence to established principles."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for inconsistency signals
        recent_turns = context.get("recent_turns", [])
        if recent_turns and len(recent_turns) > 3:
            last_input = recent_turns[-1][0].lower() if recent_turns[-1] else ""
            current_input = user_input.lower()
            # Very simple: check if contradicting previous statement
            if ("no" in current_input and "yes" in last_input) or ("never" in current_input and "always" in last_input):
                reasoning.append("Contradiction detected with recent statement")
                stance = "oppose"
                confidence = 0.8
            else:
                stance = "support"
                confidence = 0.6
                reasoning.append("Consistent positioning maintained")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_discipline", {"stance": stance})
        
        return MinisterPosition(
            domain="discipline",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Consistency neutral",
        )


class MinisterOfGrandStrategy(Minister):
    """Thinks in terms of long-term vision and alignment."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for long-term language
        longterm_words = {"future", "vision", "goal", "plan", "strategy", "years", "decade", "legacy"}
        has_longterm_language = any(word in user_input.lower() for word in longterm_words)
        
        if has_longterm_language:
            stance = "support"
            confidence = 0.8
            reasoning.append("Long-term strategic thinking evident")
        else:
            stance = "oppose"
            confidence = 0.6
            reasoning.append("Short-term tactical focus detected; strategy missing")
        
        trace("minister_grand_strategy", {"stance": stance, "longterm": has_longterm_language})
        
        return MinisterPosition(
            domain="grand_strategist",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Strategy alignment neutral",
        )


class MinisterOfIntelligence(Minister):
    """Focuses on information quality and hidden factors."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for awareness of information gaps
        awareness_words = {"unknown", "unclear", "hidden", "uncertain", "risk", "threat", "monitor"}
        has_awareness = any(word in user_input.lower() for word in awareness_words)
        
        if has_awareness:
            reasoning.append("Awareness of information gaps present")
            stance = "support"
            confidence = 0.75
        else:
            reasoning.append("Potential information blindness")
            stance = "oppose"
            confidence = 0.6
        
        trace("minister_intelligence", {"stance": stance, "awareness": has_awareness})
        
        return MinisterPosition(
            domain="intelligence",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Information quality neutral",
            concerns=["information_gaps", "hidden_risks"] if stance == "oppose" else []
        )


class MinisterOfTiming(Minister):
    """Evaluates whether now is the right moment."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for urgency/timing language
        timing_words = {"now", "immediately", "urgent", "delay", "wait", "ready", "soon"}
        has_timing_language = any(word in user_input.lower() for word in timing_words)
        
        urgency_level = 0.5
        if "now" in user_input.lower() or "immediately" in user_input.lower():
            urgency_level = 0.8
        elif "delay" in user_input.lower() or "wait" in user_input.lower():
            urgency_level = 0.3
        
        # Timing minister often advocates for patience
        if urgency_level > 0.7:
            stance = "oppose"  # Caution against hasty action
            confidence = 0.7
            reasoning.append("Excessive urgency detected; urge patience")
        elif urgency_level < 0.4:
            stance = "support"
            confidence = 0.6
            reasoning.append("Adequate preparation time available")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_timing", {"stance": stance, "urgency": urgency_level})
        
        return MinisterPosition(
            domain="timing",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Timing neutral",
        )


class MinisterOfRisk(Minister):
    """Identifies downside scenarios and loss prevention."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        doctrine_applied = False
        
        # Apply prohibitions from doctrine if loaded
        if self.doctrine and self.doctrine.prohibitions:
            for prohibition in self.doctrine.prohibitions:
                if prohibition.lower() in user_input.lower():
                    reasoning.append(f"Doctrine prohibition triggered: {prohibition}")
                    return MinisterPosition(
                        domain="risk",
                        stance="oppose",
                        confidence=0.95,
                        reasoning=" | ".join(reasoning),
                        red_line_triggered=True,
                        concerns=["prohibition_violation"],
                        doctrine_applied=True
                    )
        
        # Check for risk signals
        risk_words = {"risk", "danger", "loss", "failure", "crash", "bankrupt", "catastrophe", "expensive"}
        has_risk_language = any(word in user_input.lower() for word in risk_words)
        
        # Catastrophic/red-line words
        critical_words = {"bankruptcy", "death", "total loss", "irreversible", "extinction"}
        has_critical_risk = any(word in user_input.lower() for word in critical_words)
        
        if has_critical_risk:
            stance = "oppose"
            confidence = 0.95
            reasoning.append("CRITICAL RISK DETECTED")
            red_line = True
        elif has_risk_language:
            stance = "oppose"
            confidence = 0.75
            reasoning.append("Significant risk present")
            red_line = False
        else:
            stance = "support"
            confidence = 0.5
            reasoning.append("Risk profile acceptable")
            red_line = False
        
        trace("minister_risk", {"stance": stance, "critical": has_critical_risk, "doctrine_used": doctrine_applied})
        
        return MinisterPosition(
            domain="risk",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Risk manageable",
            red_line_triggered=red_line,
            concerns=["downside_scenarios", "loss_prevention"] if has_risk_language else [],
            doctrine_applied=doctrine_applied
        )



class MinisterOfPower(Minister):
    """Evaluates capability and leverage positions."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for power/leverage language
        power_words = {"leverage", "pressure", "force", "power", "strength", "weak", "advantage", "position"}
        has_power_language = any(word in user_input.lower() for word in power_words)
        
        if "weak" in user_input.lower() or "weakness" in user_input.lower():
            stance = "oppose"
            confidence = 0.7
            reasoning.append("Power asymmetry unfavorable")
        elif has_power_language:
            stance = "support"
            confidence = 0.6
            reasoning.append("Favorable power dynamics")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_power", {"stance": stance, "power_aware": has_power_language})
        
        return MinisterPosition(
            domain="power",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Power balance neutral",
        )


class MinisterOfPsychology(Minister):
    """Considers human factors and emotional dimensions."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for emotional/psychological language
        psychology_words = {"feel", "emotion", "fear", "trust", "motivation", "belief", "psychology", "mental"}
        has_psychology_language = any(word in user_input.lower() for word in psychology_words)
        
        # Check for denial of emotions
        denial_words = {"don't care", "no emotion", "purely logical", "irrelevant"}
        is_denial = any(word in user_input.lower() for word in denial_words)
        
        if is_denial:
            stance = "oppose"
            confidence = 0.7
            reasoning.append("Human factors being dismissed")
        elif has_psychology_language:
            stance = "support"
            confidence = 0.7
            reasoning.append("Psychological factors acknowledged")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_psychology", {"stance": stance, "psychology_aware": has_psychology_language})
        
        return MinisterPosition(
            domain="psychology",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Psychology neutral",
        )


class MinisterOfTechnology(Minister):
    """Evaluates technical feasibility and capability."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for technical language
        tech_words = {"system", "build", "code", "technical", "platform", "infrastructure", "api", "server"}
        has_tech_language = any(word in user_input.lower() for word in tech_words)
        
        if has_tech_language:
            stance = "support"
            confidence = 0.6
            reasoning.append("Technical approach considered")
        else:
            stance = "oppose"
            confidence = 0.5
            reasoning.append("Technical dimension overlooked")
        
        trace("minister_technology", {"stance": stance, "tech_aware": has_tech_language})
        
        return MinisterPosition(
            domain="technology",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Technology neutral",
        )


class MinisterOfLegitimacy(Minister):
    """Ensures actions align with values and authority."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        doctrine_applied = False
        
        # Check doctrine prohibitions first (e.g., "must not make decisions without sovereign authority")
        if self.doctrine and self.doctrine.prohibitions:
            for prohibition in self.doctrine.prohibitions:
                if prohibition.lower() in user_input.lower():
                    reasoning.append(f"Doctrine violation: {prohibition}")
                    doctrine_applied = True
                    return MinisterPosition(
                        domain="legitimacy",
                        stance="oppose",
                        confidence=0.95,
                        reasoning=" | ".join(reasoning),
                        red_line_triggered=True,
                        doctrine_applied=True
                    )
        
        # Check for legitimacy/authority language
        legit_words = {"authority", "right", "legal", "ethical", "values", "principle", "legitimate", "law"}
        has_legit_language = any(word in user_input.lower() for word in legit_words)
        
        # Check for red flags
        illegal_words = {"illegal", "unethical", "fraud", "corrupt", "steal", "cheat"}
        has_red_flag = any(word in user_input.lower() for word in illegal_words)
        
        if has_red_flag:
            stance = "oppose"
            confidence = 0.95
            reasoning.append("LEGITIMACY RED LINE")
            red_line = True
        elif has_legit_language:
            stance = "support"
            confidence = 0.7
            reasoning.append("Values-aligned approach")
            red_line = False
        else:
            stance = "neutral"
            confidence = 0.5
            red_line = False
        
        trace("minister_legitimacy", {"stance": stance, "red_flag": has_red_flag, "doctrine_used": doctrine_applied})
        
        return MinisterPosition(
            domain="legitimacy",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Legitimacy assumed",
            red_line_triggered=red_line,
            doctrine_applied=doctrine_applied
        )



class MinisterOfTruth(Minister):
    """Prioritizes truth and accurate representation."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        doctrine_applied = False
        
        # Check doctrine prohibitions related to truth
        if self.doctrine and self.doctrine.prohibitions:
            for prohibition in self.doctrine.prohibitions:
                if "truth" in prohibition.lower() or "deception" in prohibition.lower():
                    if any(word in user_input.lower() for word in ["lie", "deceive", "hide", "mislead", "fabricate"]):
                        reasoning.append(f"Doctrine violation: {prohibition}")
                        doctrine_applied = True
                        return MinisterPosition(
                            domain="truth",
                            stance="oppose",
                            confidence=0.9,
                            reasoning=" | ".join(reasoning),
                            red_line_triggered=True,
                            doctrine_applied=True
                        )
        
        # Check for truthfulness indicators
        truth_words = {"true", "fact", "accurate", "verify", "proof", "evidence", "honest"}
        has_truth_language = any(word in user_input.lower() for word in truth_words)
        
        # Check for deception signals
        deception_words = {"lie", "hide", "mislead", "fabricate", "fiction", "false", "deceive"}
        has_deception = any(word in user_input.lower() for word in deception_words)
        
        if has_deception:
            stance = "oppose"
            confidence = 0.9
            reasoning.append("Deception detected")
            red_line = True
        elif has_truth_language:
            stance = "support"
            confidence = 0.8
            reasoning.append("Truth seeking evident")
            red_line = False
        else:
            stance = "neutral"
            confidence = 0.5
            red_line = False
        
        trace("minister_truth", {"stance": stance, "truthful": has_truth_language, "doctrine_used": doctrine_applied})
        
        return MinisterPosition(
            domain="truth",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Truth assumed",
            red_line_triggered=red_line,
            doctrine_applied=doctrine_applied
        )



class MinisterOfNarrative(Minister):
    """Evaluates coherence and story alignment."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for narrative/story language
        narrative_words = {"story", "narrative", "coherent", "consistent", "arc", "plot", "theme", "meaning"}
        has_narrative_language = any(word in user_input.lower() for word in narrative_words)
        
        # Check for contradictions
        recent_turns = context.get("recent_turns", [])
        narrative_consistent = True
        if recent_turns and len(recent_turns) > 2:
            # Simple heuristic: check if recent statements form coherent theme
            recent_text = " ".join([turn[0] for turn in recent_turns[-3:]])
            contradictions = recent_text.lower().count("but") + recent_text.lower().count("however")
            narrative_consistent = contradictions < 3
        
        if not narrative_consistent:
            stance = "oppose"
            confidence = 0.7
            reasoning.append("Narrative contradictions detected")
        elif has_narrative_language:
            stance = "support"
            confidence = 0.7
            reasoning.append("Strong narrative coherence")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_narrative", {"stance": stance, "narrative_consistent": narrative_consistent})
        
        return MinisterPosition(
            domain="narrative",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Narrative neutral",
        )


class MinisterOfSovereign(Minister):
    """Meta-minister: evaluates overall coherence and authority."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for self-awareness and clarity
        sovereign_words = {"I", "my", "decision", "I choose", "I will", "my authority"}
        has_sovereign_language = any(word in user_input.lower() for word in sovereign_words)
        
        if has_sovereign_language:
            stance = "support"
            confidence = 0.8
            reasoning.append("Self-directed action evident")
        else:
            stance = "oppose"
            confidence = 0.6
            reasoning.append("Clarity about agency needed")
        
        trace("minister_sovereign", {"stance": stance})
        
        return MinisterPosition(
            domain="sovereign",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Sovereignty neutral",
        )


class MinisterOfOptionality(Minister):
    """Preserves freedom of action and strategic retreat options."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for commitment/lock-in signals
        commitment_words = {"forever", "never go back", "all-in", "burn bridges", "irreversible"}
        has_commitment_language = any(word in user_input.lower() for word in commitment_words)
        
        # Check for optionality appreciation
        optionality_words = {"option", "exit", "flexibility", "retreat", "alternative", "backup"}
        has_optionality_language = any(word in user_input.lower() for word in optionality_words)
        
        if has_commitment_language and not has_optionality_language:
            stance = "oppose"
            confidence = 0.8
            reasoning.append("Excessive commitment detected; losing optionality")
        elif has_optionality_language:
            stance = "support"
            confidence = 0.8
            reasoning.append("Strategic optionality preserved")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_optionality", {"stance": stance})
        
        return MinisterPosition(
            domain="optionality",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Optionality neutral",
            concerns=["irreversibility", "exit_collapse"] if stance == "oppose" else []
        )


class MinisterOfRiskResources(Minister):
    """Manages resource allocation under uncertainty and scarcity."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for resource awareness
        resource_words = {"budget", "capital", "resources", "money", "time", "energy", "reserves"}
        has_resource_language = any(word in user_input.lower() for word in resource_words)
        
        # Check for resource depletion signals
        depletion_words = {"all", "everything", "out", "empty", "spent", "running out", "shortage"}
        has_depletion = any(word in user_input.lower() for word in depletion_words)
        
        if has_depletion:
            stance = "oppose"
            confidence = 0.8
            reasoning.append("Resource depletion risk detected")
        elif has_resource_language:
            stance = "support"
            confidence = 0.7
            reasoning.append("Resource constraints acknowledged")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_risk_resources", {"stance": stance})
        
        return MinisterPosition(
            domain="risk_resources",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Resource management neutral",
            concerns=["scarcity", "depletion"] if has_depletion else []
        )


class MinisterOfTribunal(Minister):
    """Represents accountability, judgment and consequences."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for accountability language
        accountability_words = {"responsible", "accountable", "consequences", "liable", "fault", "blame"}
        has_accountability = any(word in user_input.lower() for word in accountability_words)
        
        # Check for evasion signals
        evasion_words = {"not my fault", "not responsible", "someone else", "blame others", "deny"}
        has_evasion = any(word in user_input.lower() for word in evasion_words)
        
        if has_evasion:
            stance = "oppose"
            confidence = 0.8
            reasoning.append("Accountability evasion detected")
        elif has_accountability:
            stance = "support"
            confidence = 0.8
            reasoning.append("Accountability acknowledged")
        else:
            stance = "neutral"
            confidence = 0.5
        
        trace("minister_tribunal", {"stance": stance})
        
        return MinisterPosition(
            domain="tribunal",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "Accountability neutral",
            red_line_triggered=has_evasion and not has_accountability
        )


class MinisterOfWarMode(Minister):
    """Evaluates scenarios requiring aggressive action and mobilization."""
    
    def analyze(self, user_input: str, context: Dict[str, Any]) -> MinisterPosition:
        reasoning = []
        
        # Check for conflict/war language
        war_words = {"attack", "defend attack", "mobilize", "aggressive", "enemy", "battle", "survival"}
        has_war_language = any(word in user_input.lower() for word in war_words)
        
        # Check for escalation
        escalation_words = {"escalat", "intensify", "full force", "all hands", "total war"}
        has_escalation = any(word in user_input.lower() for word in escalation_words)
        
        if has_escalation:
            stance = "support"
            confidence = 0.85
            reasoning.append("Escalation scenario active; mobilization required")
        elif has_war_language:
            stance = "support"
            confidence = 0.7
            reasoning.append("Conflict requires aggressive posture")
        else:
            stance = "oppose"  # War minister advocates for peace when not under threat
            confidence = 0.6
            reasoning.append("No immediate threat; prefer diplomatic approaches")
        
        trace("minister_war_mode", {"stance": stance, "escalation": has_escalation})
        
        return MinisterPosition(
            domain="war_mode",
            stance=stance,
            confidence=confidence,
            reasoning=" | ".join(reasoning) if reasoning else "War mode neutral",
        )


# 19 voting ministers (core council)
MINISTERS = {
    "adaptation": MinisterOfAdaptation,
    "conflict": MinisterOfConflict,
    "diplomacy": MinisterOfDiplomacy,
    "data": MinisterOfData,
    "discipline": MinisterOfDiscipline,
    "grand_strategist": MinisterOfGrandStrategy,
    "intelligence": MinisterOfIntelligence,
    "timing": MinisterOfTiming,
    "risk": MinisterOfRisk,
    "power": MinisterOfPower,
    "psychology": MinisterOfPsychology,
    "technology": MinisterOfTechnology,
    "legitimacy": MinisterOfLegitimacy,
    "truth": MinisterOfTruth,
    "narrative": MinisterOfNarrative,
    "sovereign": MinisterOfSovereign,
    "optionality": MinisterOfOptionality,
    "risk_resources": MinisterOfRiskResources,
    "war_mode": MinisterOfWarMode,
}

# Judges: advisory roles that observe but don't vote
JUDGES = {
    "tribunal": MinisterOfTribunal,
}
