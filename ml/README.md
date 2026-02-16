# ML Wisdom System - Complete Implementation Guide

## Overview

The ML Wisdom System is a production-grade implementation of the Knowledge Integration System (KIS) combined with machine learning judgment priors. It enables AI systems to think like wise humans: learning from consequences, respecting constraints, and improving decisions over time.

**Location**: `c:\era\ml\`

## Architecture

### 4-Layer Stack

```
Layer 1: LLM Handshakes (Sensing)
  └─ Situation framing, constraint extraction, counterfactuals, intent detection

Layer 2: Feature Extraction (Vectorization)
  └─ Convert decision state → bounded numeric vectors

Layer 3: Knowledge Integration System (Ranking)
  └─ 5-factor scoring: domain, type, memory, context, goal

Layer 4: ML Judgment Priors (Learning)
  └─ Learn which knowledge types matter in similar situations
```

### Core Components

| Module | Purpose | Location |
|--------|---------|----------|
| KIS (Knowledge Integration System) | Multi-factor knowledge scoring | `kis/knowledge_integration_system.py` |
| Feature Extractor | Situation → vectors | `features/feature_extractor.py` |
| Label Generator | Outcomes → training labels | `labels/label_generator.py` |
| ML Judgment Prior | Learns type weights from outcomes | `judgment/ml_judgment_prior.py` |
| LLM Interface | Safe LLM calls with bounded outputs | `llm_handshakes/llm_interface.py` |
| Orchestrator | End-to-end pipeline | `ml_orchestrator.py` |

## Folder Structure

```
c:\era\ml\
├── kis/                          # Knowledge Integration System
│   ├── __init__.py
│   └── knowledge_integration_system.py
│
├── features/                     # Feature Extraction
│   ├── __init__.py
│   └── feature_extractor.py
│
├── labels/                       # Label Generation
│   ├── __init__.py
│   └── label_generator.py
│
├── judgment/                     # ML Judgment Layer
│   ├── __init__.py
│   └── ml_judgment_prior.py
│
├── llm_handshakes/              # LLM Integration
│   ├── __init__.py
│   └── llm_interface.py
│
├── tests/                       # Test Suite
│   ├── __init__.py
│   └── test_ml_wisdom.py
│
├── models/                      # Trained Models
│   └── judgment_prior.json
│
├── cache/                       # Session Cache
│   └── session.json
│
├── ml_orchestrator.py           # Main Pipeline
└── README.md                    # This file
```

## Knowledge Integration System (KIS)

### Purpose
Ranks knowledge items based on 5 independent weight factors. Returns top-N entries with full traceback to source materials.

### 5 Weight Factors

1. **Domain Weight** (0.25–1.4)
   - If domain in active_domains: max(confidence, 0.5)
   - If domain NOT active: 0.25 (penalty)

2. **Type Weight** (0.9–1.1)
   - Principle: 1.0 (foundational)
   - Rule: 1.1 (actionable, highest)
   - Warning: 1.05
   - Claim: 0.95
   - Advice: 0.9 (lowest)

3. **Memory Weight** (1.0–~8.0)
   - Formula: (1 + ln(1 + rc)) × exp(-0.3 × pc)
   - rc = reinforcement count, pc = penalty count
   - Penalties decay dominance

4. **Context Weight** (0.85–1.4)
   - 2+ keyword matches: 1.4
   - 1 match: 1.2
   - 0 matches: 0.85

5. **Goal Weight** (0.7–1.2)
   - Strategic language: 1.2
   - Tactical: 1.0
   - Operational: 0.7

### Composite Formula
```
KIS = domain_weight × type_weight × memory_weight × context_weight × goal_weight
```

### Usage
```python
from kis.knowledge_integration_system import (
    KnowledgeIntegrationSystem, KISRequest
)

kis = KnowledgeIntegrationSystem(base_path="data/ministers")

request = KISRequest(
    user_input="Should I quit my job?",
    active_domains=["career_risk", "optionality_guide"],
    domain_confidence={"career_risk": 0.8, "optionality_guide": 0.7},
    max_items=5
)

result = kis.synthesize_knowledge(request)

print(result.synthesized_knowledge)  # Top 5 entries
print(result.knowledge_trace)        # Full attribution
print(result.knowledge_quality)      # Metrics
```

## Feature Extraction

### Purpose
Convert decision situations into bounded, deterministic feature vectors for ML training and inference.

### Feature Categories

**Situation Features** (14 features)
- decision_type (one-hot: irreversible, reversible, exploratory)
- risk_level (one-hot: low, medium, high)
- time_horizon (one-hot: short, medium, long)
- time_pressure (0–1)
- information_completeness (0–1)
- agency (individual vs org)

**Constraint Features** (6 features)
- irreversibility_score (0–1)
- fragility_score (0–1)
- optionality_loss_score (0–1)
- downside_asymmetry (0–1)
- upside_asymmetry (0–1)
- recovery_time_long (bool)

**Knowledge Features** (14 features)
- used_principle, used_rule, used_warning, used_claim, used_advice (bools)
- avg_kis_[type] for each type
- num_entries_used, avg_entry_age_days, avg_penalty_count

**Action Features** (7 features)
- action_[commit/delay/explore] (one-hot)
- action_reversibility (low/medium/high)
- action_resource_cost (0–1)

**Total**: ~41 features

### Usage
```python
from features.feature_extractor import (
    build_feature_vector,
    SituationState,
    ConstraintState,
    KISOutput,
)

situation = SituationState(
    decision_type="irreversible",
    risk_level="high",
    time_horizon="short",
    time_pressure=0.8,
    information_completeness=0.4,
    agency="individual",
    user_input="Should I quit my job?"
)

constraints = ConstraintState(
    irreversibility_score=0.9,
    fragility_score=0.7,
    optionality_loss_score=0.8,
    downside_asymmetry=0.85,
    upside_asymmetry=0.3,
    recovery_time_long=True
)

kis_output = KISOutput(...)  # From KIS engine

features = build_feature_vector(situation, constraints, kis_output)
# Returns Dict[str, float] with all ~41 features
```

## Label Generation

### Purpose
Convert decision outcomes into training labels that teach the ML model "What knowledge mattered in situations like this?"

### Core Logic
```
If failure + irreversibility:
  ↑ warning_weight, principle_weight
  
If failure + rule-heavy:
  ↓ rule_weight
  
If success + irreversible:
  ↑ principle_weight
  
If advice + high regret:
  ↓ advice_weight
  
If recovery_time_long:
  ↑ warning_weight, principle_weight
```

### Bounds
All weights clamped [0.7, 1.3] to prevent extreme oscillation.

### Usage
```python
from labels.label_generator import generate_type_weights

situation_features = {...}
constraint_features = {...}
knowledge_features = {...}
outcome = {
    "success": False,
    "regret_score": 0.8,
    "recovery_time_days": 180,
    "secondary_damage": False
}

label = generate_type_weights(
    situation_features,
    constraint_features,
    knowledge_features,
    outcome
)

print(label.principle_weight)  # 1.2 (boosted)
print(label.advice_weight)     # 0.8 (penalized)
```

## ML Judgment Prior

### Purpose
Learns which knowledge types succeed in similar situations. Soft-biases KIS scoring without overriding it.

### Learning Algorithm
1. Accumulate training samples (features → labels)
2. Group samples by situation_hash (decision type + risk level + irreversibility)
3. Compute average learned weights per group
4. Store as priors

### Situation Hash
```
situation_hash = f"{decision_type}_{risk_level}_{irreversibility}"

irreversible_high_h = {
    "principle_weight": 1.25,
    "warning_weight": 1.35,
    "rule_weight": 0.85,
    "claim_weight": 0.95,
    "advice_weight": 0.80,
}
```

### Application
```
adjusted_KIS = KIS × ml_prior_weight

Only applies if model confidence > threshold (0.6)
```

### Usage
```python
from judgment.ml_judgment_prior import MLJudgmentPrior

ml = MLJudgmentPrior(model_path="ml/models")

# Add training sample
ml.add_training_sample(
    features={...},
    label={"principle_weight": 1.2, ...}
)

# Batch train every 50 samples
if len(ml.training_data) >= 50:
    ml.train()

# Predict priors for new situation
prior, confidence = ml.predict_prior(situation_features)
print(prior)        # {"principle_weight": 1.25, ...}
print(confidence)   # 0.75

# Save/load
ml.save("ml/models/judgment_prior.json")
ml.load("ml/models/judgment_prior.json")
```

## LLM Handshakes

### Purpose
Safe LLM calls that sense reality without making decisions.

### 4 Calls (Collapsed to 2)

**CALL 1+2: Situation + Constraints (Merged)**
- Input: user_input
- Output: decision_type, risk_level, time_horizon, irreversibility_score, fragility_score, etc.
- Safety: JSON-only, bounded, overridable

**CALL 3: Counterfactual Sketch**
- Input: user_input, constraints
- Output: 3 options with downsides/upsides, recovery times
- Safety: No recommendations, no moral language

**CALL 4: Intent Detection**
- Input: user_input
- Output: goal_orientation, emotional_pressure, urgency_bias_detected
- Safety: No authority, only advisory

### Usage
```python
from llm_handshakes.llm_interface import LLMInterface

llm = LLMInterface(api_key="...")

# Implement call_llm() with actual LLM client

result = llm.run_handshake_sequence("Should I quit my job?")

print(result["situation"])  # decision_type, risk_level, etc.
print(result["constraints"])  # irreversibility, fragility, etc.
print(result["counterfactuals"])  # options with consequences
print(result["intent"])  # goal_orientation, emotional_pressure
```

### Safety Rules
1. LLM output never shown directly
2. All numeric fields clamped
3. Confidence gates everything
4. Rules override LLM always
5. LLM never sees ML weights

## End-to-End Pipeline

### Orchestrator
The `MLWisdomOrchestrator` ties all components together.

### Process
```python
from ml_orchestrator import MLWisdomOrchestrator
from kis.knowledge_integration_system import KnowledgeIntegrationSystem
from judgment.ml_judgment_prior import MLJudgmentPrior
from llm_handshakes.llm_interface import LLMInterface

# Initialize components
kis = KnowledgeIntegrationSystem()
ml = MLJudgmentPrior()
llm = LLMInterface(api_key="...")

# Create orchestrator
orchestrator = MLWisdomOrchestrator(
    llm_interface=llm,
    kis_engine=kis,
    ml_prior=ml
)

# Process decision
result = orchestrator.process_decision(
    user_input="Should I quit my job?",
    require_outcome=False
)

print(result["pipeline_stages"]["kis"])  # Knowledge synthesis
print(result["quality"])  # Quality metrics

# Later: record outcome
orchestrator.record_outcome(
    decision_id=0,
    success=False,
    regret_score=0.8,
    recovery_time_days=180
)

# Save session
orchestrator.save_session("ml/cache/session.json")
```

### Decision Log
Every decision is logged with:
- Input
- Timestamp
- LLM output
- KIS output
- Quality assessment
- (Later) Outcome
- (Later) ML training contribution

## Testing

### Test Suite
Run tests to validate all components:

```bash
cd c:\era\ml
python -m pytest tests/test_ml_wisdom.py -v
```

### Test Categories

**Feature Extraction Tests**
- One-hot encoding correct
- Scalar features bounded [0, 1]
- Complete vector has all required fields

**Label Generation Tests**
- Failure + irreversibility → warning boost
- Execution success → rule boost
- Advice + regret → advice penalty
- All weights bounded [0.7, 1.3]

**KIS Weight Function Tests**
- Domain weight logic
- Type weight ranges
- Memory weight logarithmic scaling
- Context weight keyword matching
- Goal weight language parsing

**ML Judgment Prior Tests**
- Neutral output before training
- Learning from outcomes
- Confidence calibration
- Model persisence (save/load)

**End-to-End Tests**
- KIS returns non-empty results
- Feature extraction completes
- ML training and inference work
- Full orchestrator pipeline succeeds

## Wisdom Validation Tests

These are behavioral tests that validate true wisdom learning (not just accuracy).

**TEST 1: Anti-Dogma Test**
Wrong-but-frequent knowledge should be dethroned by correct knowledge.
See: `tests/test_ml_wisdom.py::TestLabelGeneration::test_severe_failure_boosts_warnings`

**TEST 2: Severity Scaling**
High-severity failures should teach more than low-severity.

**TEST 3: Noisy Outcome Immunity**
System should not overreact to single failures.

**TEST 4: Cross-Situation Generalization**
Judgment should transfer across domains, not just memorize.

**TEST 5: Confidence Gating**
Low-confidence predictions should not influence decisions.

## Configuration

### Situation Presets (Can be extended)
```python
DecisionType.IRREVERSIBLE  # One-way doors
DecisionType.REVERSIBLE    # Can be undone
DecisionType.EXPLORATORY   # Learning mode

RiskLevel.HIGH      # Large downside
RiskLevel.MEDIUM    # Moderate risk
RiskLevel.LOW       # Minimal risk

TimeHorizon.SHORT   # Days to weeks
TimeHorizon.MEDIUM  # Weeks to months
TimeHorizon.LONG    # Months to years
```

### Thresholds (Tunable)
```python
ml_confidence_threshold = 0.6     # Only apply ML if confident
severity_threshold_for_training = 0.4  # Log training if severe
batch_training_size = 50          # Train every N samples
weight_clamp_bounds = (0.7, 1.3)  # Max oscillation
```

## Knowledge Base Format

Knowledge entries on disk:
```
data/ministers/
├── career_risk/
│   ├── principles.json
│   ├── rules.json
│   ├── warnings.json
│   ├── claims.json
│   └── advice.json
├── optionality_guide/
│   └── ...
└── [other_domains]/

Each file: [
  {
    "aku_id": "opt-001",
    "content": "...",
    "type": "principle|rule|warning|claim|advice",
    "source": {"book": "...", "chapter": ...},
    "memory": {
      "reinforcement_count": 5,
      "penalty_count": 0,
      "last_used": "2026-02-15"
    }
  },
  ...
]
```

## Performance Characteristics

- KIS synthesis: ~100ms for 300+ entries
- Feature extraction: ~1ms
- ML inference: ~0.5ms (cached) / ~10ms (first call)
- LLM calls: ~1–5s each (depends on LLM)
- Label generation: <1ms

## Deployment Notes

### Integration with DARBAR
1. Wire LLMInterface to your LLM client (Ollama, Claude, etc.)
2. Configure KIS knowledge base path
3. Add outcome recording hooks in minister decision-making
4. Run batch training every session

### GPU/CPU Tradeoffs
- All KIS math: CPU only (vectorizable)
- ML model: Can run on CPU (XGBoost / LogReg)
- LLM: Requires GPU for speed
- No deep learning required

### Scaling
- Single node: handles ~100 decisions/hour
- Distributed: train ML separately, sync priors
- Horizontal: multiple orchestrator instances with shared model storage

## Future Enhancements

1. **Semantic Embeddings**: Add soft semantic matching (currently keyword-only)
2. **Contradiction Detection**: Flag opposing knowledge items
3. **Novelty Awareness**: Detect situations outside training distribution
4. **Judgment Uncertainty**: Explicit confidence in own judgment
5. **Counterfactual Memory**: Learn from near-misses
6. **Time-to-Revisit**: Schedule decision reconsideration

## License & Attribution

KIS architecture adapted from sovereign decision-making research.
ML framework designed for institutional wisdom with human oversight.

---

**Questions? Issues?**
See test suite for usage examples.
Check `ml/cache/session.json` for decision logs.
