# 04_DATA_FLOW.md

# 🔄 Era Project - Data Flow Documentation

**How data moves through the system, from user input to learned wisdom**

---

## Overview

This document traces data flow through three main pipelines:

1. **Decision Pipeline** - User input → Persona response
2. **Learning Pipeline** - Outcome → ML training → Improvement
3. **Memory Pipeline** - Real-time → Validated → Long-term storage

---

## Pipeline 1: Decision Flow

### High-Level Flow

```
User Input
    │
    ▼
┌─────────────────┐
│  Mode Check     │
│  (/mode cmd?)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Get Current Mode│
│ QUICK/WAR/      │
│ MEETING/DARBAR  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Mode Orchestrator          │
│  Routes Decision            │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────────┐
│  QUICK  │ │ WAR/MEETING/     │
│  Mode   │ │ DARBAR           │
│         │ │                  │
│ Direct  │ │ Dynamic Council  │
│ LLM     │ │ ├─ Select Mins   │
│ Response│ │ ├─ Convene       │
│         │ │ ├─ Aggregate     │
│         │ │ └─ Prime Review  │
└────┬────┘ └────────┬─────────┘
     │               │
     └───────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ KIS Ranking    │
    │ (Knowledge     │
    │  Integration)  │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ ML Judgment    │
    │ Prior Applied  │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ Generate       │
    │ Response       │
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │ Display to     │
    │ User           │
    └────────────────┘
```

### Detailed Step-by-Step

#### Step 1: Input Reception
```
Data: User input string
Example: "Should I quit my job to start a company?"

Flow:
  main.py:main() → receives input
  context.py:update_context() → adds to conversation history
```

#### Step 2: Mode Check
```
Data: Input string
Check: Does input start with "/mode"?

If YES:
  mode_orchestrator.py:select_mode() → switch mode
  Return to Step 1

If NO:
  Continue to Step 3
```

#### Step 3: LLM Handshakes (Sensing)
```
Input: User input string
Output: Situation + Constraints + Counterfactuals + Intent

Calls:
  llm_interface.py:run_handshake_sequence()
  
  CALL 1+2 (Merged): Situation + Constraints
    → decision_type: "irreversible"
    → risk_level: "high"
    → time_horizon: "long"
    → irreversibility_score: 0.9
    → fragility_score: 0.7
    
  CALL 3: Counterfactual Sketch
    → Option 1: Quit now (downside: no income)
    → Option 2: Wait 6 months (downside: miss opportunity)
    → Option 3: Start side hustle (downside: burnout)
    
  CALL 4: Intent Detection
    → goal_orientation: "achievement"
    → emotional_pressure: 0.6
    → urgency_bias: "high"
```

#### Step 4: Mode Routing
```
Input: Current mode, domain, user input
Output: Council recommendation (or direct LLM)

Flow:
  mode_orchestrator.py:route_decision()
  
  If QUICK:
    → Skip council
    → Direct LLM call
    → Return response
    
  If WAR/MEETING/DARBAR:
    → dynamic_council.py:select_ministers()
    → Select based on mode + domain
    → Proceed to Step 5
```

#### Step 5: Minister Selection (WAR/MEETING/DARBAR)
```
Input: Mode, domain
Output: List of ministers to convene

Selection Logic:
  WAR: [Risk, Power, Strategy, Technology, Timing] (fixed 5)
  MEETING: 3-5 domain-relevant ministers
  DARBAR: All 18 ministers

Example (MEETING, domain=career):
  Selected: [Career, Risk, Economics, Psychology, Strategy]
```

#### Step 6: Council Convening
```
Input: Selected ministers, user input, context
Output: Minister recommendations + votes

Flow:
  dynamic_council.py:convene_council()
  
  For each minister:
    → Load minister doctrine
    → Query KIS for relevant knowledge
    → Generate recommendation
    → Cast vote (confidence-scored)
    
  Output:
    {
      "recommendations": [...],
      "votes": {...},
      "consensus_strength": 0.75
    }
```

#### Step 7: KIS Ranking
```
Input: Domain, active_domains, user_input
Output: Top-N knowledge entries with scores

Flow:
  knowledge_integration_system.py:synthesize_knowledge()
  
  For each knowledge entry:
    → Compute domain_weight (0.25-1.4)
    → Compute type_weight (0.9-1.1)
    → Compute memory_weight (1.0-8.0)
    → Compute context_weight (0.85-1.4)
    → Compute goal_weight (0.7-1.2)
    → KIS_score = product of all weights
    
  Sort by KIS_score
  Return top 5-10 entries
```

#### Step 8: ML Judgment Prior Application
```
Input: Situation features
Output: Adjusted knowledge type weights

Flow:
  ml_judgment_prior.py:predict_prior()
  
  1. Extract situation features
  2. Compute situation_hash
  3. Look up learned priors for hash
  4. If confidence > 0.6:
       → Return priors
     Else:
       → Return neutral weights
       
  Apply:
    adjusted_KIS = KIS × ml_prior_weight
```

#### Step 9: Aggregation
```
Input: Minister recommendations, KIS results
Output: Aggregated recommendation

Flow:
  dynamic_council.py:aggregate_recommendations()
  
  Mode-specific aggregation:
    WAR: Victory-focused synthesis
    MEETING: Balanced multi-perspective
    DARBAR: Full doctrine-driven deliberation
    
  Output:
    {
      "recommendation": "...",
      "confidence": 0.75,
      "minister_votes": {...},
      "dissenting_opinions": [...]
    }
```

#### Step 10: Prime Confident Review
```
Input: Council recommendation
Output: Approved/rejected/modified recommendation

Flow:
  prime_confident.py:review_recommendation()
  
  Checks:
    → Doctrine alignment
    → Red-line protection
    → Logical consistency
    
  If approved:
    → Return recommendation
  If rejected:
    → Override with alternative
  If modified:
    → Return modified version
```

#### Step 11: Response Generation
```
Input: Final recommendation, mode, context
Output: Natural language response

Flow:
  ollama_runtime.py:generate()
  
  Prompt includes:
    → User input
    → Recommendation
    → Minister input (if council used)
    → Mode framing
    → Doctrine context
    
  Model: qwen3:14b
  Timeout: 30 seconds
```

#### Step 12: Display
```
Input: Response string
Output: Displayed to user

Format:
  N: [MODE] "Response text..."
  
Example:
  N: [MEETING] "Council convenes. Risk Minister expresses
      concern about cash flow. Strategy Minister suggests
      a phased approach..."
```

---

## Pipeline 2: Learning Flow

### High-Level Flow

```
Decision Made
    │
    ▼
┌─────────────────┐
│ Store Episode   │
│ (Episodic Mem)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Record Metrics  │
│ (Performance)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Observe Outcome │
│ (Success/Fail)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Label  │
│ (Type Weights)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Add to Training │
│ (Batch Buffer)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Train Model     │
│ (Every 50)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract Patterns│
│ (Every 100)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Retrain System  │
│ (Every 200)     │
└─────────────────┘
```

### Detailed Step-by-Step

#### Step 1: Episode Storage (Every Turn)
```
Input: Turn data (decision, confidence, outcome)
Output: Episode stored in JSONL

Data Structure:
  {
    "turn_id": 150,
    "timestamp": "2026-02-18T02:30:00Z",
    "domain": "career",
    "mode": "MEETING",
    "user_input": "...",
    "recommendation": "...",
    "confidence": 0.75,
    "minister_votes": {...},
    "council_recommendation": "...",
    "outcome": "success" | "failure",
    "regret_score": 0.0-1.0,
    "consequences": [...]
  }

Storage:
  Memory/YYYY-MM-DD_episodes.jsonl
  (append one line per turn)
```

#### Step 2: Metrics Recording (Every Turn)
```
Input: Turn data, outcome
Output: Updated metrics

Flow:
  performance_metrics.py:record_decision()
  
  Updates:
    → Domain success rate
    → Minister performance
    → Mode stability
    → Feature coverage
    
  Stored in:
    live_metrics.json (in-memory, flushed every 10 turns)
```

#### Step 3: Outcome Observation
```
Input: User reaction, consequence data
Output: Outcome classification

Classification:
  Success: User satisfied, positive consequences
  Failure: User regretted, negative consequences
  
Regret Score:
  0.0 = No regret (perfect outcome)
  0.3 = Mild regret
  0.6 = Moderate regret
  0.8+ = Severe regret
```

#### Step 4: Label Generation
```
Input: Situation features, outcome, regret
Output: Training label (type weight adjustments)

Flow:
  label_generator.py:generate_type_weights()
  
  Logic:
    If failure + irreversibility:
      → warning_weight += 0.2
      → principle_weight += 0.1
      
    If failure + rule-heavy:
      → rule_weight -= 0.15
      
    If success + irreversible:
      → principle_weight += 0.15
      
    If advice + high regret:
      → advice_weight -= 0.2
      
  Clamp all weights to [0.7, 1.3]
  
  Output Label:
    {
      "principle_weight": 1.2,
      "rule_weight": 0.95,
      "warning_weight": 1.15,
      "claim_weight": 1.0,
      "advice_weight": 0.85
    }
```

#### Step 5: Training Sample Accumulation
```
Input: Features + Label
Output: Training sample added to buffer

Data Structure:
  {
    "features": {...},  # 41-dim vector
    "label": {...},     # Type weights
    "situation_hash": "irreversible_high_h",
    "timestamp": "..."
  }

Buffer Size: 50 samples
When full → Trigger training
```

#### Step 6: Model Training (Every 50 Samples)
```
Input: 50 training samples
Output: Updated judgment prior model

Flow:
  ml_judgment_prior.py:train()
  
  Algorithm:
    1. Group samples by situation_hash
    2. For each hash group:
       → Compute average type weights
       → Store as prior for that situation type
    3. Save model to disk
    
  Model Storage:
    ml/models/judgment_prior.json
```

#### Step 7: Pattern Extraction (Every 100 Turns)
```
Input: Episodic memory (100+ episodes)
Output: Identified patterns and clusters

Flow:
  pattern_extraction.py:extract_patterns()
  
  Patterns Detected:
    1. long_failure_streak
       → 3+ consecutive failures
       → Triggers alert
       
    2. high_regret_cluster
       → Multiple high-regret decisions
       → Indicates systemic issue
       
    3. weak_domain_pattern
       → Domain <50% success rate
       → Triggers retraining
       
    4. minister_underperformance
       → Specific minister consistently wrong
       → Triggers minister retraining
       
  Output:
    {
      "patterns": [...],
      "learning_signals": [...],
      "recommendations": [...]
    }
```

#### Step 8: PWM Sync (Every 100 Turns)
```
Input: Episodic memory, Metrics snapshot
Output: Validated facts committed to PWM

Flow:
  pwm_bridge.py:periodic_pwm_sync()
  
  Validation:
    → Check consistency across episodes
    → Verify with metrics
    → Ensure confidence > 0.75
    
  If validated:
    pwm.update_entity(
      entity="john",
      field="risk_tolerance",
      value=0.4,
      confidence=0.85
    )
    
  PWM Storage:
    Entity-attribute graph
    (high-confidence facts only)
```

#### Step 9: System Retraining (Every 200 Turns)
```
Input: Patterns, PWM insights, Metrics
Output: Updated ministers, doctrines, KIS weights

Flow:
  system_retraining.py:retrain_all()
  
  Steps:
    1. Extract success patterns
    2. Update minister confidence formulas
    3. Evolve doctrines from patterns
    4. Rebalance KIS weights
    5. Apply PWM insights
    
  Minister Update:
    For each domain:
      → Identify weak ministers
      → Update confidence formulas
      → Apply learned doctrine
      
  Doctrine Update:
    → Add new principles from patterns
    → Adjust rules based on outcomes
    → Update warnings from failures
```

---

## Pipeline 3: Memory Flow

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY FLOW DIAGRAM                       │
└─────────────────────────────────────────────────────────────┘

Every Turn:
┌──────────────┐
│ Episodic     │ ← Fast, detailed, observed
│ Memory       │   (decision + outcome)
└──────┬───────┘
       │
       │ Aggregate
       ▼
┌──────────────┐
│ Performance  │ ← Medium, statistical
│ Metrics      │   (success rates)
└──────┬───────┘
       │
       │ Validate (100 turns)
       ▼
┌──────────────┐
│ PWM          │ ← Slow, validated, high-confidence
│ (Personal    │   (stable facts about person)
│  World Model)│
└──────────────┘
```

### Tier 1: Episodic Memory (Fast)

**Update Frequency:** Every turn  
**Storage Format:** JSONL  
**Location:** `Memory/YYYY-MM-DD_episodes.jsonl`  
**Purpose:** Pattern detection, mistake prevention  

**Data Flow:**
```
Turn N Complete
    │
    ▼
┌─────────────────────────────────────┐
│ Build Episode Object                │
│ {                                   │
│   turn_id, timestamp, domain,       │
│   mode, user_input, recommendation, │
│   confidence, minister_votes,       │
│   outcome, regret_score,            │
│   consequences                      │
│ }                                   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Append to JSONL File                │
│ Memory/YYYY-MM-DD_episodes.jsonl    │
└─────────────────────────────────────┘
```

**Query Patterns:**
```python
# Find similar episodes
similar = episodic.find_similar_episodes(
    domain="career",
    pattern="quit_without_buffer"
)

# Get recent episodes
recent = episodic.get_recent_episodes(
    count=10,
    domain="finance"
)

# Extract lessons
lessons = episodic.extract_lessons(
    domain="career",
    min_confidence=0.7
)
```

---

### Tier 2: Performance Metrics (Medium)

**Update Frequency:** Every turn (recorded), every 100 turns (aggregated)  
**Storage Format:** JSON  
**Location:** `live_metrics.json`  
**Purpose:** Identify weak domains, guide retraining  

**Data Flow:**
```
Turn N Complete
    │
    ▼
┌─────────────────────────────────────┐
│ Update In-Memory Metrics            │
│ - Domain success rate               │
│ - Minister performance              │
│ - Mode stability                    │
│ - Feature coverage                  │
└────────┬────────────────────────────┘
         │
         │ (Every 10 turns)
         ▼
┌─────────────────────────────────────┐
│ Flush to Disk                       │
│ live_metrics.json                   │
└─────────────────────────────────────┘
         │
         │ (Every 100 turns)
         ▼
┌─────────────────────────────────────┐
│ Aggregate & Analyze                 │
│ - Compute rolling success rates     │
│ - Detect weak domains (<50%)        │
│ - Compute minister adjustments      │
│ - Generate periodic report          │
└─────────────────────────────────────┘
```

**Metrics Structure:**
```json
{
  "domains": {
    "career": {
      "success_rate": 0.67,
      "turn_count": 45,
      "avg_confidence": 0.75,
      "avg_regret": 0.3
    },
    "finance": {
      "success_rate": 0.55,
      "turn_count": 30,
      "avg_confidence": 0.68,
      "avg_regret": 0.4
    }
  },
  "ministers": {
    "risk": {
      "accuracy": 0.72,
      "avg_confidence": 0.8
    },
    "strategy": {
      "accuracy": 0.68,
      "avg_confidence": 0.75
    }
  },
  "modes": {
    "QUICK": {"success_rate": 0.65, "turn_count": 20},
    "WAR": {"success_rate": 0.70, "turn_count": 15},
    "MEETING": {"success_rate": 0.67, "turn_count": 50},
    "DARBAR": {"success_rate": 0.75, "turn_count": 15}
  },
  "overall": {
    "success_rate": 0.67,
    "total_turns": 100,
    "improvement": "+16.7%"
  }
}
```

---

### Tier 3: PWM - Personal World Model (Slow)

**Update Frequency:** Every 100 turns (after validation)  
**Storage Format:** Entity-attribute graph  
**Location:** `data/pwm/entities.json`  
**Purpose:** Stable, high-confidence facts  

**Data Flow:**
```
Turn 100, 200, 300...
    │
    ▼
┌─────────────────────────────────────┐
│ Collect Metrics Snapshot            │
│ - Domain success rates              │
│ - Minister performance              │
│ - Pattern analysis                  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Validate Observations               │
│ - Check consistency                 │
│ - Verify confidence > 0.75          │
│ - Cross-reference episodes          │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Commit Validated Facts to PWM       │
│ pwm.update_entity(                  │
│   entity="john",                    │
│   field="risk_tolerance",           │
│   value=0.4,                        │
│   confidence=0.85                   │
│ )                                   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Generate Actionable Insights        │
│ pwm.generate_actionable_insights()  │
│ → ["John is risk-averse",           │
│    "Prefers email communication",   │
│    "Values work-life balance"]      │
└─────────────────────────────────────┘
```

**PWM Structure:**
```json
{
  "entities": {
    "john": {
      "attributes": {
        "risk_tolerance": {
          "value": 0.4,
          "confidence": 0.85,
          "last_updated": "turn_200",
          "source": "metrics_validation"
        },
        "communication_preference": {
          "value": "email",
          "confidence": 0.9,
          "last_updated": "turn_100",
          "source": "pattern_analysis"
        }
      },
      "relationships": {
        "alice": {
          "type": "spouse",
          "trust_level": 0.8,
          "dynamics": "supportive"
        }
      }
    }
  },
  "timeline": [
    {
      "turn": 100,
      "event": "entity_created",
      "entity": "john"
    },
    {
      "turn": 200,
      "event": "attribute_updated",
      "entity": "john",
      "field": "risk_tolerance",
      "old_value": 0.6,
      "new_value": 0.4
    }
  ]
}
```

---

## Cross-Pipeline Data Flows

### Decision → Learning → Memory

```
Decision Made (Pipeline 1)
    │
    ├─→ Store Episode (Pipeline 3, Tier 1)
    │
    ├─→ Record Metrics (Pipeline 3, Tier 2)
    │
    └─→ Observe Outcome
         │
         ▼
    Generate Label (Pipeline 2)
         │
         ▼
    Train ML Model (Pipeline 2)
         │
         ▼
    Extract Patterns (Pipeline 2)
         │
         ▼
    Retrain System (Pipeline 2)
         │
         ▼
    Update Ministers (affects Pipeline 1)
    Update Doctrines (affects Pipeline 1)
    Update KIS Weights (affects Pipeline 1)
```

### Memory → Decision Enhancement

```
Episodic Memory (Tier 1)
    │
    ├─→ Find Similar Episodes
    │   └─→ Inform current decision
    │
    └─→ Extract Lessons
         └─→ Update doctrines
              └─→ Affect future decisions

Performance Metrics (Tier 2)
    │
    ├─→ Detect Weak Domains
    │   └─→ Trigger retraining
    │
    └─→ Compute Minister Adjustments
         └─→ Update minister confidence
              └─→ Affect voting weights

PWM (Tier 3)
    │
    └─→ Generate Actionable Insights
         └─→ Inform persona responses
              └─→ More personalized advice
```

---

## Data Storage Summary

| Data Type | Format | Location | Update Freq | Size/Turn |
|-----------|--------|----------|-------------|-----------|
| Episodes | JSONL | `Memory/YYYY-MM-DD.jsonl` | Every turn | ~500 bytes |
| Metrics | JSON | `live_metrics.json` | Every 10 turns | ~5 KB |
| ML Model | JSON | `ml/models/judgment_prior.json` | Every 50 samples | ~10 KB |
| PWM | JSON | `data/pwm/entities.json` | Every 100 turns | ~2 KB |
| Patterns | JSON | `Memory/patterns.json` | Every 100 turns | ~1 KB |
| Logs | TXT | `logs/*.log` | Continuous | ~100 bytes/turn |

**Total Storage Growth:** ~600 bytes per turn  
**1000 Turns:** ~600 KB  
**10000 Turns:** ~6 MB

---

## Data Flow Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPLETE DATA FLOW                          │
└─────────────────────────────────────────────────────────────────┘

USER INPUT
    │
    ├───→ [LLM Handshakes] ───→ Situation + Constraints
    │                                  │
    ├───→ [Mode Orchestrator] ──→ Mode Decision
    │                                  │
    ├───→ [Dynamic Council] ───→ Minister Recommendations
    │                                  │
    ├───→ [KIS Engine] ────────→ Knowledge Rankings
    │                                  │
    ├───→ [ML Judgment Prior] ─→ Adjusted Weights
    │                                  │
    └───→ [Prime Confident] ───→ Final Approval
                                     │
                                     ▼
                              PERSONA RESPONSE
                                     │
                                     ├───→ Display to User
                                     │
                                     ├───→ Store Episode ───→ Episodic Memory
                                     │
                                     ├───→ Record Metrics ──→ Performance Metrics
                                     │
                                     └───→ Observe Outcome
                                            │
                                            ├───→ Generate Label
                                            │        │
                                            │        ▼
                                            │   Train ML Model
                                            │        │
                                            │        ▼
                                            │   Update Priors
                                            │
                                            └───→ Extract Patterns (100 turns)
                                                   │
                                                   ├───→ Retrain Ministers (200 turns)
                                                   │
                                                   └───→ Sync PWM (100 turns)
                                                          │
                                                          └───→ Generate Insights
                                                                 │
                                                                 └───→ Inform Future Decisions
```

---

📄 **Next:** [`05_FLOWCHARTS.md`](./05_FLOWCHARTS.md) - Visual diagrams (Mermaid + ASCII)
