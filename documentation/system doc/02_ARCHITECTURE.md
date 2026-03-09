# 02_ARCHITECTURE.md

# 🏗️ Era Project - System Architecture

**Complete architectural overview with component diagrams and integration points**

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ERA / PERSONA N                                │
│                  Ministerial Cognitive Architecture                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  PERSONA LAYER   │    │   ML LAYER       │    │   HSE LAYER      │
│  (Decision Core) │    │ (Learning/ML)    │    │ (Simulation)     │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                           │                           │
        ├─ Mode Orchestrator        ├─ KIS Engine               ├─ Synthetic Human
        ├─ Ministerial Council      ├─ Feature Extraction       ├─ Stress Injector
        ├─ Prime Confident          ├─ Judgment Priors          ├─ Personality Drift
        ├─ Episodic Memory          ├─ Pattern Extraction       └─ Population Mgr
        └─ Performance Metrics      └─ Sovereign Orchestrator
```

---

## Layer 1: Persona Core

### Purpose
Generate wise, context-aware decisions using ministerial council and mode-based reasoning.

### Components

```
persona/
├── main.py                      # Entry point, conversation loop
├── brain.py                     # High-level decision control
├── ollama_runtime.py            # LLM connection layer
├── context.py                   # Conversation context management
├── state.py                     # System state tracking
├── trace.py                     # Debug tracing
│
├── council/
│   ├── dynamic_council.py       # Mode-aware minister selection
│   └── __init__.py
│
├── modes/
│   ├── mode_orchestrator.py     # 4-mode routing logic
│   ├── __init__.py
│   └── [mode strategies]
│
├── learning/
│   ├── episodic_memory.py       # Turn-by-turn storage
│   ├── performance_metrics.py   # Success rate tracking
│   ├── consequence_engine.py    # Forward simulation
│   ├── confidence_model.py      # Bayesian confidence
│   ├── outcome_feedback_loop.py # Outcome → adjustment
│   └── failure_analysis.py      # Root cause diagnosis
│
├── validation/
│   ├── mode_validator.py        # Mode consistency checks
│   └── identity_validator.py    # Self-contradiction detection
│
├── persistence/
│   └── conversation_arc.py      # Long-term narrative tracking
│
└── pwm_integration/
    └── pwm_bridge.py            # Personal World Model sync
```

### Data Flow

```
User Input
    │
    ▼
┌─────────────────┐
│  Mode Check     │ ← Is this a /mode command?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Get Current Mode│ ← QUICK/WAR/MEETING/DARBAR
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Mode Orchestrator Routes Decision │
│   ├─ Should invoke council?         │
│   ├─ Which ministers?               │
│   ├─ How to frame?                  │
│   └─ How to aggregate?              │
└────────┬────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────────────┐
│  QUICK  │ │ WAR/MEETING/DARBAR   │
│  Mode   │ │ (Council Required)   │
│         │ │                      │
│ Direct  │ │ ┌──────────────────┐ │
│ LLM     │ │ │ Dynamic Council  │ │
│ Response│ │ │ ├─ Select Mins   │ │
│         │ │ │ ├─ Convene       │ │
│         │ │ │ ├─ Aggregate     │ │
│         │ │ │ └─ Prime Review  │ │
│         │ │ └──────────────────┘ │
└────┬────┘ └──────────┬───────────┘
     │                 │
     └────────┬────────┘
              │
              ▼
     ┌────────────────┐
     │ Store Episode  │
     │ Record Metrics │
     └────────┬───────┘
              │
              ▼
     ┌────────────────┐
     │ Display Response│
     └────────────────┘
```

---

## Layer 2: ML Learning System

### Purpose
Learn from outcomes, extract patterns, and improve decision quality over time.

### Components

```
ml/
├── sovereign_orchestrator.py    # 12-system integration hub
├── ml_orchestrator.py           # ML wisdom pipeline
├── system_retraining.py         # Minister retraining logic
├── minister_retraining.py       # Per-minister updates
├── pattern_extraction.py        # Failure cluster detection
├── vector_memory.py             # Vector-based memory
├── reward_shaping.py            # Outcome-based rewards
├── doctrine_update.py           # Doctrine evolution
│
├── kis/                         # Knowledge Integration System
│   └── knowledge_integration_system.py
│
├── features/                    # Feature Extraction
│   └── feature_extractor.py
│
├── labels/                      # Label Generation
│   └── label_generator.py
│
├── judgment/                    # ML Judgment Priors
│   └── ml_judgment_prior.py
│
├── llm_handshakes/              # LLM Sensing Layer
│   └── llm_interface.py
│
├── models/                      # Trained Models
│   └── judgment_prior.json
│
└── cache/                       # Session Cache
    └── session.json
```

### ML Pipeline

```
Decision Made
    │
    ▼
┌─────────────────────────────────────┐
│  LLM Handshakes (Sensing Layer)     │
│  ├─ Situation framing               │
│  ├─ Constraint extraction           │
│  ├─ Counterfactual generation       │
│  └─ Intent detection                │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Feature Extraction                 │
│  Convert situation → 41-dim vector  │
│  ├─ Situation features (14)         │
│  ├─ Constraint features (6)         │
│  ├─ Knowledge features (14)         │
│  └─ Action features (7)             │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  KIS (Knowledge Integration System) │
│  Rank knowledge by 5 factors:       │
│  ├─ Domain weight (0.25-1.4)        │
│  ├─ Type weight (0.9-1.1)           │
│  ├─ Memory weight (1.0-8.0)         │
│  ├─ Context weight (0.85-1.4)       │
│  └─ Goal weight (0.7-1.2)           │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  ML Judgment Prior                  │
│  Apply learned weights based on     │
│  similar past situations            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Outcome Recording                  │
│  Store success/failure, regret      │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Label Generation                   │
│  Convert outcome → training label   │
│  (adjust type weights)              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Model Training (every 50 samples)  │
│  Update judgment prior model        │
└─────────────────────────────────────┘
```

### KIS Weight Formula

```
KIS_score = domain_weight × type_weight × memory_weight × context_weight × goal_weight

Where:
- domain_weight: 0.25-1.4 (based on domain confidence)
- type_weight: 0.9-1.1 (principle=1.0, rule=1.1, advice=0.9)
- memory_weight: (1 + ln(1 + rc)) × exp(-0.3 × pc)
  - rc = reinforcement count
  - pc = penalty count
- context_weight: 0.85-1.4 (keyword matches)
- goal_weight: 0.7-1.2 (strategic language)
```

---

## Layer 3: Human Simulation Environment (HSE)

### Purpose
Provide realistic human simulation for testing, stress-testing, and validation.

### Components

```
hse/
├── human_profile.py             # Synthetic human definition
├── personality_drift.py         # Personality evolution
├── crisis_injector.py           # Crisis scenario injection
├── population_manager.py        # Multi-human management
├── analytics_server.py          # Analytics API
│
└── simulation/
    ├── synthetic_human_sim.py   # Main simulation engine
    ├── human_persona_adapter.py # Human ↔ Persona bridge
    ├── stress_orchestrator.py   # Stress scenario orchestration
    └── bidirectional_simulation.py # Two-way conversation
```

### Simulation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Synthetic Human Simulation Loop                 │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Generate Human  │ ← LLM (llama3.1:8b)
│ Input (Turn N)  │   Based on personality + context
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Persona N       │ ← Mode + Council + Ministers
│ Generates       │
│ Response        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Record Episode  │ ← Store to memory
│ Record Metrics  │ ← Update success rate
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Human  │ ← LLM reacts to response
│ Input (Turn N+1)│
└─────────────────┘
         │
         └─── Repeat for 100-1000 turns
```

### Stress Testing

```
Normal Operation
    │
    ▼
┌─────────────────┐
│ Crisis Injector │ ← Trigger at turn X
│ (e.g., job loss,│
│  health crisis) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Personality     │ ← Increase stress,
│ Drift Engine    │   change behavior
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Measure Persona │ ← Trust, adoption,
│ Response Quality│   coherence under pressure
└─────────────────┘
```

---

## Layer 4: Sovereign Integration

### Purpose
Integrate all 12 cognitive systems into a cohesive orchestration layer.

### The 12 Systems

```
┌─────────────────────────────────────────────────────────────┐
│                  Sovereign Orchestrator                      │
│                                                              │
│  Learning & Memory (4 systems)                               │
│  ├─ 1. EpisodicMemory     → Decision + outcome storage      │
│  ├─ 2. ConsequenceEngine  → Forward ripple simulation       │
│  ├─ 3. BayesianConfidence → Domain confidence tracking      │
│  └─ 4. PerformanceMetrics → Success rate aggregation        │
│                                                              │
│  Feedback & Improvement (2 systems)                          │
│  ├─ 5. OutcomeFeedbackLoop → Outcomes → minister updates    │
│  └─ 6. SystemRetraining    → Pattern extraction + doctrine  │
│                                                              │
│  Validation & Governance (3 systems)                         │
│  ├─ 7. ModeValidator       → Mode consistency enforcement   │
│  ├─ 8. IdentityValidator   → Self-contradiction detection   │
│  └─ 9. ConversationArc     → Long-term narrative tracking   │
│                                                              │
│  Character & Stress (3 systems)                              │
│  ├─ 10. SyntheticHuman     → Persistent human character     │
│  ├─ 11. StressOrchestrator → Compounding crisis chains      │
│  └─ 12. HumanPersonaAdapter → Trust/adoption measurement    │
│                                                              │
│  Reporting                                                   │
│  └─ 13. PerformanceDashboard → Real-time metrics + alerts   │
└─────────────────────────────────────────────────────────────┘
```

### 4-Phase Progression

```
Phase 1: Infrastructure (Turns 0-100)
├─ Initialize EpisodicMemory
├─ Initialize PerformanceMetrics
├─ Initialize SyntheticHuman
└─ Record first 100 turns

Phase 2: Learning Loop (Turns 100-300)
├─ Activate OutcomeFeedbackLoop
├─ Activate ConversationArc
├─ Activate IdentityValidator
└─ Enable failure analysis

Phase 3: Optimization (Turns 300-700)
├─ Activate ModeValidator
├─ Activate FailureAnalysis
├─ Trigger SystemRetraining (every 200 turns)
└─ Extract success patterns

Phase 4: Stress Testing (Turns 700-1000+)
├─ Activate StressScenarioOrchestrator
├─ Measure stress response quality
├─ Monitor trust trajectory
└─ Generate dashboard reports
```

---

## Memory Architecture (Hybrid)

### Three-Tier Design

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID MEMORY ARCHITECTURE                │
└─────────────────────────────────────────────────────────────┘

Tier 1: EPISODIC MEMORY (Fast, Real-Time)
├─ Update: Every turn
├─ Stores: Decision, confidence, outcome, regret, consequences
├─ Purpose: Pattern detection, mistake prevention
├─ Format: JSONL files in Memory/
└─ Query: find_similar_episodes(domain, pattern)

Tier 2: PERFORMANCE METRICS (Medium, Statistical)
├─ Update: Every turn (recorded), every 100 turns (aggregated)
├─ Stores: Success rates, minister performance, weak domains
├─ Purpose: Identify weak features, guide retraining
├─ Format: JSON (live_metrics.json)
└─ Query: compute_domain_performance(), detect_weak_domains()

Tier 3: PWM - PERSONAL WORLD MODEL (Slow, Validated)
├─ Update: Every 100 turns (after validation)
├─ Stores: Validated facts about person/relationships
├─ Purpose: Stable, high-confidence knowledge
├─ Format: Entity-attribute graph
└─ Query: query_entity(entity_id), generate_actionable_insights()

FLOW:
Every Turn → Episodic + Metrics
Every 100 Turns → Validate → PWM Sync
Every 200 Turns → Retrain with PWM insights
```

---

## Integration Points

### Between Layers

```
PERSONA LAYER ←→ ML LAYER
├─ Episodic memory writes → ML reads for patterns
├─ Metrics aggregates → ML uses for training
├─ KIS rankings → Persona uses for decisions
└─ Retraining signals → Persona updates ministers

PERSONA LAYER ←→ HSE LAYER
├─ Synthetic human generates input → Persona responds
├─ Persona response → Synthetic human reacts
├─ Crisis injector → Persona stress tests
└─ Trust metrics → Persona adaptation

ML LAYER ←→ HSE LAYER
├─ Outcome data → ML training labels
├─ Pattern extraction → Crisis scenario design
└─ Performance metrics → Simulation tuning
```

---

## File Dependencies

```
persona/main.py
├─ imports: modes/mode_orchestrator.py
├─ imports: council/dynamic_council.py
├─ imports: learning/episodic_memory.py
├─ imports: learning/performance_metrics.py
├─ imports: ollama_runtime.py
└─ imports: brain.py

ml/sovereign_orchestrator.py
├─ imports: ../persona/learning/*
├─ imports: ../persona/validation/*
├─ imports: ../hse/simulation/*
├─ imports: kis/knowledge_integration_system.py
├─ imports: judgment/ml_judgment_prior.py
└─ imports: features/feature_extractor.py

hse/simulation/synthetic_human_sim.py
├─ imports: ../human_profile.py
├─ imports: ../personality_drift.py
├─ imports: ../../persona/ollama_runtime.py
└─ imports: ../../ml/kis/*
```

---

## Runtime Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RUNTIME FLOW                            │
└─────────────────────────────────────────────────────────────┘

1. INITIALIZATION (Startup)
   ├─ Load environment (.env)
   ├─ Initialize OllamaRuntime (connect to Ollama)
   ├─ Load ministers (18 domain experts)
   ├─ Initialize ModeOrchestrator (4 modes)
   ├─ Initialize EpisodicMemory
   ├─ Initialize PerformanceMetrics
   ├─ Initialize SyntheticHuman (if automated)
   └─ Display mode selection menu

2. MAIN LOOP (Per Turn)
   ├─ Get user input (or generate via synthetic human)
   ├─ Check for /mode command
   ├─ Route through ModeOrchestrator
   ├─ If QUICK: Direct LLM response
   ├─ If WAR/MEETING/DARBAR:
   │   ├─ Select ministers (mode-dependent)
   │   ├─ Convene council
   │   ├─ Aggregate recommendations
   │   └─ Prime Confident review
   ├─ Store episode (episodic memory)
   ├─ Record metrics (performance tracking)
   ├─ Check for pattern extraction (every 100 turns)
   └─ Display response

3. BACKGROUND (Asynchronous)
   ├─ Pattern extraction (every 100 turns)
   ├─ Minister retraining (every 200 turns)
   ├─ PWM sync (every 100 turns)
   ├─ Dashboard updates (every 10 turns)
   └─ Failure analysis (on failures)

4. SHUTDOWN
   ├─ Save episodic memory
   ├─ Save metrics
   ├─ Save ML models
   └─ Graceful thread pool shutdown
```

---

## Component Communication

```
┌──────────────────────────────────────────────────────────────┐
│                    COMMUNICATION PROTOCOLS                    │
└──────────────────────────────────────────────────────────────┘

LLM Calls (Ollama)
├─ Protocol: HTTP POST to localhost:11434/api/generate
├─ Models: llama3.1:8b (user), qwen3:14b (persona)
├─ Timeout: 30 seconds
└─ Fallback: Graceful timeout response

Memory Storage
├─ Format: JSONL (one episode per line)
├─ Location: Memory/YYYY-MM-DD_episodes.jsonl
├─ Sync: Immediate (every turn)
└─ Backup: Manual (user-managed)

Metrics Storage
├─ Format: JSON
├─ Location: live_metrics.json
├─ Sync: Every turn (in-memory), flush every 10 turns
└─ Backup: Manual

ML Models
├─ Format: JSON (judgment priors)
├─ Location: ml/models/judgment_prior.json
├─ Sync: Every 50 training samples
└─ Backup: Manual
```

---

## Security & Safety

```
┌──────────────────────────────────────────────────────────────┐
│                      SAFETY MECHANISMS                       │
└──────────────────────────────────────────────────────────────┘

Red Lines (Protected by All Ministers)
├─ ❌ No fraud/corruption (Legitimacy Minister)
├─ ❌ No deception (Truth/ Ethics Minister)
├─ ❌ No existential harm (Spirituality Minister)
└─ ❌ No self-contradiction (Identity Validator)

Validation Layers
├─ Mode Validator: Catches mode drift
├─ Identity Validator: Catches contradictions
├─ Conversation Arc: Maintains coherence
└─ Prime Confident: Final approval gate

Graceful Degradation
├─ LLM timeout → Fallback response
├─ Council error → Direct LLM
├─ Memory full → Oldest episodes archived
└─ Thread pool → Graceful shutdown
```

---

## Performance Characteristics

| Component | Latency | Frequency |
|-----------|---------|-----------|
| LLM Call (User) | 3-5s | Every turn |
| LLM Call (Persona) | 5-10s | Every turn |
| Council Convening | 10-30s | WAR/MEETING/DARBAR |
| KIS Ranking | ~100ms | Every decision |
| Feature Extraction | ~1ms | Every decision |
| ML Inference | ~0.5ms | Every decision |
| Memory Write | ~5ms | Every turn |
| Pattern Extraction | ~500ms | Every 100 turns |
| Minister Retraining | ~2s | Every 200 turns |

---

## Scaling Considerations

### Current (Single Node)
- Handles ~100 decisions/hour
- Limited by LLM call speed
- Memory grows ~1KB per turn

### Horizontal Scaling
- Multiple orchestrator instances
- Shared ML model storage
- Distributed episodic memory

### Optimization Opportunities
- LLM call batching
- Vector memory for faster retrieval
- GPU acceleration for ML training
- Caching for repeated queries

---

## Next Steps

📄 **Continue Reading:**
- [`03_FILE_REFERENCE.md`](./03_FILE_REFERENCE.md) - Every file explained
- [`04_DATA_FLOW.md`](./04_DATA_FLOW.md) - Data pipelines
- [`05_FLOWCHARTS.md`](./05_FLOWCHARTS.md) - Visual diagrams
