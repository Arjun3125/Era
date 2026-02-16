# HYBRID MEMORY ARCHITECTURE GUIDE

## The Three-System Approach

### System 1: EpisodicMemory (Real-Time)
**Purpose**: Track decisions, outcomes, consequences, patterns
**Update Frequency**: Every turn
**Stores**:
- Decision made (with confidence, mode, minister votes)
- Outcome achieved
- Consequence chain (immediate → delayed effects)
- Regret score
- Lessons learned

**Example**:
```python
episodic.store_episode({
    "turn": 150,
    "decision": "recommend quitting job",
    "confidence": 0.75,
    "outcome": "person quit",
    "consequences": [
        ("turn 150", "career", "job_quit", -0.3),
        ("turn 180", "wealth", "savings_declined", -0.4),
        ("turn 250", "relationships", "stress_divorce", -0.5),
    ]
})

# Later: Detect if about to repeat this mistake
similar = episodic.find_similar_episodes("career", "quit_without_buffer")
if similar:
    print("WARNING: About to repeat turn 150 disaster!")
```

---

### System 2: PerformanceMetrics (Real-Time → Aggregated)
**Purpose**: Track what's working, identify weak features, guide retraining
**Update Frequency**: Every turn (recorded), every 100 turns (aggregated)
**Tracks**:
- Success rate by domain
- Minister performance
- Mode stability
- Feature coverage
- Failure clusters

**Example**:
```python
metrics.record_decision(
    turn=150,
    domain="career",
    minister="risk",
    stance="recommend_quitting",
    confidence=0.75,
    outcome="failed",
    regret=0.8
)

# Every 100 turns: Analyze
weak = metrics.detect_weak_domains(threshold=0.5)
# Output: ["career_risk: 45% success", "psychology: 38% success"]

adjustments = metrics.compute_minister_adjustments()
# Output: "risk_minister was too aggressive; adjust multiplier 0.8 → 0.6"
```

---

### System 3: PWM (Slow, Validated)
**Purpose**: Store stable facts about people/relationships
**Update Frequency**: Every 100 turns (after validation)
**Stores**:
- Entity attributes ("John is risk-averse", confidence 0.85)
- Relationship dynamics ("Alice-Bob trust: 0.6 → 0.8")
- Timeline of changes
- Audit trail (what changed and why)

**Example**:
```python
# BEFORE: Don't update directly every turn
# pwm.update_entity("john", "risk_tolerance", 0.4)  # ❌ Too fast

# AFTER: Validate through episodic/metrics first
episodic.store_episode(...)
metrics.record_decision(...)

# THEN (every 100 turns): Commit validated facts
pwm_bridge.periodic_pwm_sync(turn=150, metrics_snapshot={...})

pwm.update_entity(
    entity_id="john",
    field="risk_tolerance",
    old_value=0.6,
    new_value=0.4,  # Based on failure analysis + metrics
    confidence=0.85  # Only commits high-confidence facts
)
```

---

## Flow: Decision → Learning → Validation → Commitment

```
Turn 150:
┌─────────────────────────────────────────────────────────────┐
│ PERSONA GENERATES DECISION: "quit your job"                 │
└────────────────┬────────────────┬────────────────────────────┘
                 │                │
         ┌───────▼────────┐   ┌───▼────────────────┐
         │  EpisodicMemory│   │ PerformanceMetrics │
         │  stores:       │   │ records:           │
         │  - decision    │   │ - attempt          │
         │  - confidence  │   │ - domain           │
         │  - mode        │   │ - outcome          │
         └────────────────┘   └────────────────────┘
                 │
         Turn 180: HUMAN REGRETS
                 │
         ┌───────▼────────────────────┐
         │ EpisodicMemory stores:      │
         │ - outcome: "failure"        │
         │ - regret: 0.8               │
         │ - consequence: savings down │
         └──────────┬──────────────────┘
                    │
Turn 100/200/300:   │
VALIDATION CYCLE    │
         ┌──────────▼──────────────────┐
         │ PWMBridge analyzes:         │
         │ - Is failure consistent?    │
         │ - Does metrics confirm?     │
         │ - Confidence > 0.75?        │
         └──────────┬──────────────────┘
                    │
         ┌──────────▼──────────────────────┐
         │ IF VALIDATED:                   │
         │ pwm.update_entity(              │
         │   "john",                       │
         │   "risk_tolerance",             │
         │   0.4,  ← Updated from 0.6      │
         │   confidence=0.85               │
         │ )                               │
         └─────────────────────────────────┘
```

---

## Integration with SovereignOrchestrator

The orchestrator now has three responsibilities:

### 1. Every Turn (Already doing this)
```python
# Record to episodic memory
episodic.store_episode(turn, domain, decision, confidence, outcome, consequences)

# Record to metrics
metrics.record_decision(turn, domain, decision, confidence, outcome)
```

### 2. Every 100 Turns (NEW: PWM sync)
```python
# After metrics aggregation, validate and commit to PWM
metrics_snapshot = {
    "wealth": {"success_rate": 0.68},
    "career": {"success_rate": 0.55},
    ...
}

pwm_bridge.periodic_pwm_sync(turn=100, metrics_snapshot=metrics_snapshot)

# Now PWM contains validated facts about the person
pwm_insights = pwm_bridge.generate_actionable_insights()
# Returns: ["John is risk-averse", "Alice prefers email", ...]
```

### 3. Every 200 Turns (Retraining with PWM insights)
```python
# Use PWM facts to improve future decisions
retrainer.update_minister_confidence_formulas(
    domain=current_domain,
    pwm_insights=pwm_insights  # ← NEW: Feed PWM facts
)

# Update doctrine based on what we learned
retrainer.encode_learned_doctrine(
    episodic_lessons=episodic_lessons,
    pwm_validated_facts=pwm_facts
)
```

---

## What Each System Answers

| Question | Answer Source |
|----------|----------------|
| "What happened in turn 150?" | EpisodicMemory ← Fast, detailed |
| "Is career domain performing well?" | PerformanceMetrics ← Real-time aggregation |
| "Was that mistake repeated?" | EpisodicMemory.find_similar_episodes() |
| "Should we adjust Risk minister?" | PerformanceMetrics.compute_adjustments() |
| "What do we KNOW about John?" | PWM ← Validated facts only |
| "Is John risk-averse or aggressive?" | PWM (after 100-turn validation) |
| "What if we retrain based on lessons?" | Retrainer uses all three |

---

## Code Example: Full Cycle

```python
from persona.pwm_integration.pwm_bridge import PWMIntegrationBridge

# Initialize the bridge
pwm_bridge = PWMIntegrationBridge(
    pwm=pwm,                    # Personal World Model
    episodic_memory=episodic,   # Decision/outcome log
    metrics=metrics,            # Performance tracker
    confidence_model=confidence # Domain confidence
)

# Main loop
for turn in range(1, 1000):
    
    # 1. Every turn: Generate persona response
    persona_response = generate_response(...)
    
    # 2. Every turn: Record to episodic + metrics
    episodic.store_episode(turn, domain, response, outcome, consequences)
    metrics.record_decision(turn, domain, response, outcome)
    
    # 3. Every turn: Record observations for PWM
    # (Inferences about the person, not yet committed)
    if outcome == "failure" and regret > 0.7:
        pwm_bridge.record_observation(
            turn, domain, entity="john",
            attribute="risk_tolerance",
            value=0.35,
            source="failure_inference"
        )
    
    # 4. Every 100 turns: Validate and commit to PWM
    if turn % 100 == 0:
        metrics_snapshot = metrics.compute_domain_performance()
        pwm_bridge.periodic_pwm_sync(turn, metrics_snapshot)
        
        # Now use validated facts
        insights = pwm_bridge.generate_actionable_insights()
        print(f"PWM Insights: {insights}")
    
    # 5. Every 200 turns: Retrain with all sources
    if turn % 200 == 0:
        episodic_lessons = episodic.extract_lessons()
        retrainer.update_doctrine(
            episodic_lessons=episodic_lessons,
            pwm_facts=pwm.query_all_entities()
        )
```

---

## Summary: What Each System Is For

| System | Update Freq | Confidence | Use Case |
|--------|-------------|------------|----------|
| **Episodic** | Every turn | High (observed) | Pattern detection, mistake prevention |
| **Metrics** | Every turn (agg 100) | Medium (statistical) | Identify weak features, guide retraining |
| **PWM** | Every 100 turns | High (validated) | Store stable facts, inform long-term decisions |

**Key Rule**: 
- Episodic and Metrics are **fast, real-time, high-volume**
- PWM is **slow, validated, high-confidence facts only**
- PWM receives updates ONLY from Metrics after validation

This is how fast learning systems feed into slow, stable knowledge stores.
