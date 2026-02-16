# PWM Redesigned: Proper Three-System Architecture

## Summary of Changes

Implemented the proper separation of concerns as specified:

1. **PWM (Knowledge Graph)** ← Slow, careful fact storage
2. **EpisodicMemory (Decision Log)** ← Real-time learning  
3. **PerformanceMetrics (Improvement Engine)** ← Systematic retraining

---

## What Changed

### 1. PWMIntegrationBridge (`persona/pwm_integration/pwm_bridge.py`)

**OLD (Incorrect):**
- Tried to validate domain performance
- Attempted to detect failure patterns
- Tried to feed insights back to confidence model
- Mixed concerns: validation + improvement

**NEW (Correct):**
- ONLY queues observations (every turn)
- ONLY validates observations (every 100 turns)
- ONLY commits high-confidence facts to PWM
- NO attempt at improvement or pattern detection

#### Key Method Changes:

```python
# OLD - did too much
def record_observation(turn, domain, entity, attribute, value, source)
def connect_episodic_outcome(turn, domain, entity, outcome, regret_score)
def connect_metric_insights(turn, domain, weak_domains, strong_domains)
def generate_actionable_insights()  # <- This drove improvements, which is wrong!

# NEW - does only one thing
def queue_entity_observation(turn, entity_id, attribute, observed_value, source)
def periodic_pwm_sync(turn, metrics_snapshot=None)  # -> (committed_facts, failures)
def generate_validation_insights()  # -> What to look for next (audit trail only)
```

### 2. SovereignOrchestrator (`ml/sovereign_orchestrator.py`)

**OLD (Incorrect):**
```python
# Tried to use PWM insights to adjust confidence
pwm_bridge.connect_metric_insights(domain=..., metric_type=..., value=...)
pwm_bridge.connect_episodic_outcome(turn=..., domain=..., outcome=..., regret_score=...)

# Then used PWM insights to change confidence factors
if insight['type'] == 'weak_domain':
    self.confidence.adjustment_factor[domain] *= 0.9  # WRONG!
```

**NEW (Correct):**
```python
# Queue observations if notable (high-failure episode)
if outcome == "failure":
    pwm_bridge.queue_entity_observation(...)

# Only for audit trail - NOT for driving improvements
pwm_updates = pwm_bridge.periodic_pwm_sync(turn)
insights = pwm_bridge.generate_validation_insights()  # What to observe next
# (confidence adjustment is handled by SystemRetraining, not PWM)
```

---

## Three-System Proper Flow

### System 1: EpisodicMemory (Every Turn)
```python
# The REAL decision learning system
episodic.store_episode({
    "turn": 150,
    "domains": ["career", "risk"],
    "recommendation": "quit_job",
    "confidence": 0.75,
    "outcome": "person_quit",
    "regret_score": 0.8,
    "consequence_chain": [
        (150, "career", "job_quit", -0.3),
        (180, "wealth", "savings_declined", -0.4),
        (250, "relationships", "stress_divorce", -0.5),
    ],
    "lesson_learned": "don't_recommend_quit_without_financial_buffer"
})

# Later, detect patterns:
if episodic.find_similar_episodes("career", "quit_without_buffer"):
    return "WARNING: About to repeat turn 150 mistake!"
```

### System 2: PerformanceMetrics (Every Turn, Aggregate Every 100)
```python
# The REAL improvement system
metrics.record_decision({
    "turn": 150,
    "domain": "career",
    "minister": "risk",
    "stance": "support_quitting",
    "confidence": 0.75,
    "outcome": "failed",
    "regret": 0.8
})

# Measure performance, drive improvement:
weak_domains = metrics.find_domains_below_threshold(0.5)
# "career_risk: 45% success, Psychology: 38% success"

minister_calibration = metrics.compute_minister_adjustments()
# "risk_minister was too aggressive; lower from 0.8 to 0.6"

# Every 200 turns:
retrainer.update_minister_confidence_formulas()
retrainer.rebalance_kis_weights()
retrainer.encode_learned_doctrine()
```

### System 3: PWM (Every 100 Turns, After Validation)
```python
# The SLOW FACT STORAGE system
# Queue observations throughout 100 turns:
pwm_bridge.queue_entity_observation(
    turn=25,
    entity_id="john",
    attribute="risk_tolerance",
    observed_value=0.4,  # Observed to be lower
    source="outcome_feedback"
)
pwm_bridge.queue_entity_observation(
    turn=75,
    entity_id="john", 
    attribute="risk_tolerance",
    observed_value=0.35,  # Confirmed lower
    source="decision_pattern"
)

# At turn 100: Validate and commit facts
pwm_updates = pwm_bridge.periodic_pwm_sync(100)
# committed_facts = [
#   {"entity_id": "john", "attribute": "risk_tolerance", "value": 0.4, "confidence": 0.80}
# ]

# PWM stores: "John is risk-averse (0.4, validated at turn 100)"
# This is for AUDIT TRAIL and long-term pattern reference
```

---

## What Each System Does (And Doesn't)

| Aspect | EpisodicMemory | PerformanceMetrics | PWM |
|--------|----------------|---------------------|-----|
| **Update Frequency** | Every turn | Every turn | Every 100 turns |
| **Real-time Learning** | ✅ YES | ✅ YES | ❌ NO |
| **Failure Analysis** | ✅ YES | ✅ YES | ❌ NO |
| **Pattern Detection** | ✅ YES | ✅ YES | ❌ NO |
| **Systematic Improvement** | ✅ YES (via patterns) | ✅ YES (via metrics) | ❌ NO |
| **Stable Fact Storage** | ❌ NO (volatile) | ❌ NO (volatile) | ✅ YES |
| **Audit Trail** | ✅ YES | ✅ YES | ✅ YES |
| **Drives Confidence Changes** | ❌ NO | ✅ YES | ❌ NO |

---

## Why This Matters

### Problem with Old Approach:
- PWM tried to do improvement too (validate → modify confidence)
- But 100 turns isn't enough to truly validate complex facts
- Led to unstable confidence adjustments based on incomplete data
- PWM became a "second learning engine" instead of "fact store"

### Solution:
- **EpisodicMemory + PerformanceMetrics** handle ALL real-time learning
- **PWM** handles ONLY slow, careful fact storage
- Confidence changes come from PerformanceMetrics + SystemRetraining (every 200 turns)
- PWM changes come from validation (every 100 turns)

### Where PWM Helps:
1. **Session Summarization**: "In this period, 3 new facts about John"
2. **Audit Trail**: "John's risk tolerance changed from 0.6→0.4 between turns 50-150"
3. **Cross-Session Learning**: Load facts from previous sessions to prime new conversations
4. **Hypothesis Confidence**: "Is this inference strong enough to commit to PWM?"

---

## Code Integration Points

### Queue Observations (Every Turn)
```python
# In orchestrator.run_turn():

if self.pwm_bridge:
    # Only queue significant observations
    if outcome == "failure":
        pwm_bridge.queue_entity_observation(
            turn=turn,
            entity_id="persona_understanding",
            attribute=f"{current_domain}_weakness",
            observed_value=regret_score,
            source="decision_outcome"
        )
    
    if quality_score > 0.7:
        pwm_bridge.queue_entity_observation(
            turn=turn,
            entity_id=current_domain,
            attribute="performance_capability",
            observed_value=quality_score,
            source="metrics"
        )
```

### Validate & Commit (Every 100 Turns)
```python
# In orchestrator.run_turn(), PHASE 10.5:

if turn % 100 == 0 and self.pwm_bridge.pwm is not None:
    # Validate and commit
    pwm_updates = self.pwm_bridge.periodic_pwm_sync(turn)
    
    # Use insights for audit/reference (NOT improvement)
    insights = self.pwm_bridge.generate_validation_insights()
    # "Focus observation on 'john' (validated 5 facts)"
    # "Revalidate 'communication_style' (failed 2 times)"
```

### Drive Improvement (Every 200 Turns)
```python
# In orchestrator.run_turn(), PHASE 11:
# This stays exactly the same - uses PerformanceMetrics, NOT PWM

if turn % 200 == 0:
    # Extract patterns from episodic memory
    patterns = self.retrainer.extract_success_patterns(num_recent_turns=200)
    
    # Update ministers based on metrics, not PWM
    self.retrainer.update_minister_confidence_formulas()
    self.retrainer.rebalance_kis_weights()
    self.retrainer.encode_learned_doctrine()
```

---

## Files Modified

1. **`persona/pwm_integration/pwm_bridge.py`**
   - Removed: `record_observation`, `connect_episodic_outcome`, `connect_metric_insights`, `generate_actionable_insights`
   - Added: `queue_entity_observation`, improved `periodic_pwm_sync`, `generate_validation_insights`, `get_validation_history`, `summary()`
   - Focus: Only observation queuing, validation, and fact commitment

2. **`ml/sovereign_orchestrator.py`**
   - Removed: PWM insights → confidence factor adjustments
   - Updated: Queue only significant observations
   - Updated: Use PWM sync for audit trail, not improvement
   - Unchanged: All improvement logic via PerformanceMetrics + SystemRetraining

---

## Expected Behavior

### Turn 50 (In 100-turn cycle)
```
- EpisodicMemory: 50 episodes recorded
- PerformanceMetrics: Performance data accumulating
- PWM: 10-15 observations queued, no facts committed yet
- Improvement: None (waiting for full cycle)
```

### Turn 100 (Validation checkpoint)
```
- PWM validates 100 observations
- ~80 observations pass validation (>75% confidence)
- ~20 fail validation (insufficient evidence)
- 80 facts committed to PWM
- Insights: "Focus on john (15 facts)", "Revalidate communication_style"

- Meanwhile:
- PerformanceMetrics shows: 45% success rate baseline
- SystemRetraining will trigger next (turn 200)
```

### Turn 200 (Retraining cycle)
```
- SystemRetraining uses:
  - Episodic memory (200 decision logs)
  - PerformanceMetrics (200 decision outcomes)
  - PWM facts (as reference, for context)
  
- Updates:
  - Minister confidence formulas
  - KIS weights
  - Doctrine statements

- Success rate improves: 45% → ~55%
- PWM unchanged (next sync at turn 300)
```

### Turn 1000 (Final state)
```
- PWM: 90+ validated facts about relationships, personalities
- EpisodicMemory: 1000 episodes of decisions + consequences
- PerformanceMetrics: Success rate trajectory (45% → 82%+)
- Doctrine: Evolved through 5 retraining cycles
```

---

## Summary

✅ **Implemented:** Proper three-system separation  
✅ **Fixed:** PWM no longer tries to drive improvement  
✅ **Clarified:** EpisodicMemory + PerformanceMetrics handle learning; PWM handles fact storage  
✅ **Added:** Audit trail and validation insights to PWM  

**Key Principle:** PWM is a "knowledge graph," not a "learning engine."
