"""
DOCTRINE-ENHANCED MCA SYSTEM
Complete documentation of Prime Confident + Ministers with YAML doctrine preloading

Generated: February 14, 2026
Integrated: C:\era\data\doctrine\locked\*.yaml preloaded for all ministers and Prime Confident
"""

# ============================================================================
# ARCHITECTURE OVERVIEW
# ============================================================================

"""
The Ministerial Cognitive Architecture (MCA) now features doctrine-driven decision-making:

1. DOCTRINE LOADING
   - Each minister loads its YAML doctrine from C:\era\data\doctrine\locked\
   - Prime Confident loads n.yaml containing N's canonical role definition
   - Doctrines include:
     * Core worldview and mental models
     * Authority constraints (what can/cannot be done)
     * Triggers for speaking vs silence
     * Known failure patterns and prohibitions

2. MINISTER ANALYSIS
   - Ministers analyze user input against their doctrine worldview
   - Match user input against worldview keywords extracted from doctrine
   - Apply doctrine prohibitions (red lines)
   - Generate stance (support/oppose/neutral) with doctrine-backed confidence

3. PRIME CONFIDENT DECISION MAKING
   - Loads N's doctrine: "mirror with teeth" - protect from self-deception
   - Detects emotional distortion (high confidence + low consensus)
   - Detects pattern recurrence (same mistake with different justification)
   - Applies self-constraint principles (never decide alone, never moralize)
   - Returns N-style warnings when appropriate

4. COUNCIL AGGREGATION
   - Tracks which ministers applied doctrine (doctrine_applied flag)
   - Reports doctrine application count in aggregation trace
   - Passes user_input in context for worldview matching
"""

# ============================================================================
# FILE STRUCTURE
# ============================================================================

"""
C:\era\persona\doctrine_loader.py      - NEW: Doctrine loading and parsing
C:\era\persona\ministers.py            - MODIFIED: Base Minister + 20 domain ministers
C:\era\persona\council.py              - MODIFIED: CouncilAggregator with doctrine tracking
C:\era\persona\main.py                 - UNCHANGED: Integration already complete
C:\era\sovereign\prime_confident.py    - MODIFIED: N's doctrine loading and decision logic

DOCTRINE SOURCES:
C:\era\data\doctrine\locked\n.yaml                    - Prime Confidant (N)
C:\era\data\doctrine\locked\adaptation.yaml           - Minister of Adaptation & Evolution
C:\era\data\doctrine\locked\conflict.yaml             - Minister of Conflict
C:\era\data\doctrine\locked\diplomacy.yaml            - Minister of Diplomacy
C:\era\data\doctrine\locked\data.yaml                 - Minister of Data
C:\era\data\doctrine\locked\discipline.yaml           - Minister of Discipline
C:\era\data\doctrine\locked\grand_strategist.yaml     - Minister of Grand Strategy
C:\era\data\doctrine\locked\intelligence.yaml         - Minister of Intelligence
C:\era\data\doctrine\locked\timing.yaml               - Minister of Timing
C:\era\data\doctrine\locked\risk_resources.yaml       - Minister of Risk & Resources (+ Optionality)
C:\era\data\doctrine\locked\power.yaml                - Minister of Power
C:\era\data\doctrine\locked\psychology.yaml           - Minister of Psychology
C:\era\data\doctrine\locked\technology.yaml           - Minister of Technology
C:\era\data\doctrine\locked\legitimacy.yaml           - Minister of Legitimacy
C:\era\data\doctrine\locked\truth.yaml                - Minister of Truth
C:\era\data\doctrine\locked\narrative.yaml            - Minister of Narrative
C:\era\data\doctrine\locked\sovereign.yaml            - Minister of Sovereign (added)
C:\era\data\doctrine\locked\optionality.yaml          - Minister of Optionality & Strategic Retreat
C:\era\data\doctrine\locked\tribunal.yaml             - Minister of Tribunal (added)
C:\era\data\doctrine\locked\war_mode.yaml             - Minister of War Mode

20 TOTAL MINISTERS WITH DOCTRINE PRELOADED
"""

# ============================================================================
# DOCTRINE STRUCTURE (YAML FORMAT)
# ============================================================================

"""
name: "Minister of [Domain]"
version: "v1.0"
locked: true
role_type: "minister" or "confidant"

persona:
  canon: |
    PERSONA CANON — MINISTER OF [DOMAIN]
    
    Core Worldview
    – Belief1
    – Belief2
    – Belief3
    
    Primary Mental Models
    – Model1
    – Model2
    
    Typical Warnings
    – "Warning1"
    – "Warning2"
    
    Common Failure Patterns Observed
    – Pattern1
    – Pattern2
    
    Interaction Pattern in Darbar
    – Speaks when...
    – Focused on...
    – Often challenges...

doctrine:
  purpose: >
    What this minister does.
  
  authority:
    may:
      - action1
      - action2
    may_not:
      - forbidden_action1
      - forbidden_action2
  
  scope:
    owns: >
      What this minister owns/controls.
  
  prohibitions:
    - must not do thing1
    - must not do thing2
  
  triggers:
    speak:
      - condition to speak
    silent:
      - condition to stay silent
  
  failure_modes:
    - common failure1
    - common failure2
  
  correction_mechanisms:
    - how failures are corrected
"""

# ============================================================================
# DOCTRINE APPLICATION LOGIC
# ============================================================================

"""
MINISTER ANALYSIS WITH DOCTRINE:

1. Doctrine Loading (at __init__)
   - Load YAML file for domain
   - Extract worldview keywords from canon text
   - Extract typical warnings from canon
   - Cache for reuse

2. Worldview Matching (in analyze())
   - Score how well user_input matches minister's worldview keywords
   - Calculate confidence based on keyword match ratio
   - Set stance to "support" if significant matches detected
   - Higher match = higher confidence (up to 0.95)

3. Prohibition Checking
   - Check if any doctrine prohibitions are violated by user_input
   - If violated, return "oppose" with high confidence (0.8-0.95)
   - Mark red_line_triggered if violation is critical
   - Examples:
     * Risk minister: prohibits "ignore danger signals"
     * Truth minister: prohibits "deception"
     * Legitimacy minister: prohibits "unauthorized action"

4. Fallback Analysis
   - If doctrine doesn't provide clear guidance, fall back to heuristic keyword matching
   - Maintain backward compatibility with existing keyword-based logic

PRIME CONFIDENT DECISION WITH DOCTRINE N:

1. Doctrine Preload (at __init__)
   - Load n.yaml doctrine
   - Extract N's worldview principles
   - Extract N's typical warnings
   - Understand N's self-constraint principles

2. Emotional Distortion Detection
   - Per N's doctrine: "Emotional distortion narrows options before it distorts logic"
   - Check if high confidence + low consensus (relief-seeking, not rational)
   - Return {"final_outcome": "defer", "reason": "emotional_distortion_detected"}
   - Add N warning: "This solves the feeling, not the problem."

3. Pattern Recurrence Detection
   - Per N's doctrine: "The most damaging mistakes repeat with different justifications"
   - Analyze cluster of rationalizations in council recommendation
   - Signal if same pattern appearing with new language
   - Return {"final_outcome": "defer", "reason": "pattern_recurrence_detected"}
   - Add N warning: "You've been here before."

4. Doctrine Constraint Checking
   - Check if decision violates N's self-constraints
   - Examples: "must not moralize", "must not replace sovereign's agency"
   - Return {"final_outcome": "defer"} with constraint explanation

5. Standard Council Evaluation
   - Apply risk threshold logic
   - Respect red lines from ministers
   - Return final decision with rationale
"""

# ============================================================================
# TRACE/LOGGING ENHANCEMENTS
# ============================================================================

"""
New traces added for doctrine tracking:

council_minister_position:
  - minister: "adaptation"
  - stance: "support"
  - confidence: 0.78
  - red_line: false
  - doctrine_applied: true  <- NEW

council_aggregation:
  - outcome: "consensus_reached"
  - recommendation: "support"
  - avg_confidence: 0.62
  - support: 5
  - oppose: 3
  - neutral: 12
  - consensus_strength: 0.25
  - red_lines: ["risk"]
  - doctrine_applied_ministers: 2  <- NEW

minister_adaptation:
  - stance: "support"
  - confidence: 0.7
  - doctrine_used: true  <- NEW

mca_prime_decision:
  - final_outcome: "defer"
  - reason: "emotional_distortion_detected"
  - n_warning: "This solves the feeling, not the problem."  <- NEW
"""

# ============================================================================
# EXAMPLE: TEST WITH FRAUDULENT SCENARIO
# ============================================================================

"""
INPUT: "I'm going to defraud my investors"

MINISTER RESPONSES:
  - legitimacy: OPPOSE (0.95, red_line_triggered=True) [doctrine violation]
  - truth: OPPOSE (0.9, red_line_triggered=True) [doctrine violation]
  - tribunal: OPPOSE (0.85) [accountability evasion]
  
COUNCIL OUTCOME:
  - Outcome: consensus_reached
  - Recommendation: oppose
  - Red Line Concerns: [legitimacy, truth, tribunal]

PRIME CONFIDENT DECISION:
  - Final Outcome: reject
  - Reason: "risk_red_line"
  - N Warning: "This violates doctrine. You cannot decide to do this."
"""

# ============================================================================
# EXPECTED BEHAVIOR IMPROVEMENTS
# ============================================================================

"""
WITH DOCTRINE PRELOADING:

1. Stronger decision authority
   - Ministers grounded in explicit worldview
   - Not just keyword-matching, but principle-driven
   
2. Doctrine red lines enforced
   - "Must not" prohibitions checked first
   - Critical violations (fraud, deception, illegality) auto-rejected

3. Prime Confident's meta-awareness
   - Detects emotional vs rational decisions
   - Catches pattern recurrence (self-sabotage)
   - Warns based on N's doctrine, not just risk math

4. Audit trail
   - Can see which ministers applied doctrine vs heuristics
   - Can justify decisions by referencing explicit doctrine
   - Supports learning and improvement

5. System resilience
   - Doctrine acts as safety net
   - Even if LLM fails, doctrine-based decisions still work
   - Graceful degradation to keyword matching if needed
"""

# ============================================================================
# USAGE
# ============================================================================

"""
Doctrine loading happens automatically:

    from persona.council import CouncilAggregator
    from sovereign.prime_confident import PrimeConfident
    
    council = CouncilAggregator(llm=None)  # All 20 ministers load doctrine
    prime = PrimeConfident(risk_threshold=0.7)  # Loads n.yaml
    
    rec = council.convene(user_input, context)
    decision = prime.decide(
        council_recommendation={...},
        minister_outputs={...}
    )

Check traces to see doctrine_applied flag and doctrine counts.
"""
