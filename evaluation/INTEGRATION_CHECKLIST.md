# Evaluation System Integration Checklist

## Overview

The evaluation framework is now in place (`evaluation/`). To make it **operational**, certain modifications to the existing ERA codebase are required to support:

1. **Evaluation Mode** - Isolation flag in main orchestrator
2. **Ablation Support** - Runtime component disabling
3. **Data Leakage Prevention** - Prevent live system updates during eval

---

## Required Code Modifications

### ✅ ALREADY IN PLACE
- `evaluation/` directory structure created
- Scoring engines (outcome, regret) implemented
- Statistics engine (t-tests, CI, effect sizes) implemented
- Rubric engine (scenario loading + hash verification) implemented
- Main evaluation runner with ablation matrix implemented
- MODEL_VERSION.json for versioning
- Sample benchmark scenarios (starting with irreversible.json)

### 🔧 NEEDED MODIFICATIONS

#### 1. **ml/sovereign_orchestrator.py**
Add evaluation mode flag and isolation guards.

**What to modify:**

```python
# Add to __init__
self.evaluation_mode = False
self.isolation_mode = False

# Modify decide() method
def decide(self, user_input, context=None, evaluation_mode=False):
    # Set isolation mode if evaluation_mode=True
    if evaluation_mode:
        self.evaluation_mode = True
        self._enable_isolation_mode()
    
    # ... normal decision logic ...
    
    # At end, check if should store
    if not self.evaluation_mode:
        episodic_memory.store_episode(...)
        performance_metrics.record_decision(...)

def _enable_isolation_mode(self):
    """Disable all live system updates"""
    self.evaluation_mode = True
    # Will cascade to:
    #   - episodic_memory.evaluation_mode = True
    #   - performance_metrics.evaluation_mode = True
    #   - ml_retraining.evaluation_mode = True
    #   - pwm_sync.evaluation_mode = True
```

**Impact:** Medium - adds one flag + conditional guards

---

#### 2. **persona/learning/episodic_memory.py**
Skip storing episodes during evaluation.

**What to modify:**

```python
class EpisodicMemory:
    def __init__(self):
        self.evaluation_mode = False  # Add flag
    
    def store_episode(self, episode_data):
        if self.evaluation_mode:
            return  # No-op during evaluation
        
        # Normal storage logic
        self.episodes.append(episode_data)
```

**Impact:** Low - adds one flag + return guard

---

#### 3. **ml/metrics/performance_metrics.py**
Skip recording decisions during evaluation.

**What to modify:**

```python
class PerformanceMetrics:
    def __init__(self):
        self.evaluation_mode = False  # Add flag
    
    def record_decision(self, decision_record):
        if self.evaluation_mode:
            return  # No-op during evaluation
        
        # Normal recording logic
        self.metrics.append(decision_record)
```

**Impact:** Low - adds one flag + return guard

---

#### 4. **ml/judgment/ml_judgment_prior.py**
Support disabling ML prior for ablation.

**What to modify:**

```python
class MLJudgmentPrior:
    def __init__(self):
        self.disabled = False  # Add ablation flag
    
    def predict_outcome(self, feature_vector):
        if self.disabled:
            return None  # No ML prior when ablated
        
        # Normal prediction logic
        return self.model.predict(feature_vector)
```

**Impact:** Low - adds one flag + conditional return

---

#### 5. **ml/kis/knowledge_integration_system.py**
Support neutralizing KIS weights for ablation.

**What to modify:**

```python
class KnowledgeIntegrationSystem:
    def __init__(self):
        self.weights_neutralized = False  # Add ablation flag
    
    def synthesize_knowledge(self, input_text, active_domains):
        if self.weights_neutralized:
            # Use uniform weights instead of learned weights
            return self._synthesize_uniform(input_text, active_domains)
        
        # Normal KIS logic
        return self._synthesize_with_weights(...)

def _synthesize_uniform(self, input_text, domains):
    """KIS with uniform domain weights (ablation mode)"""
    uniform_weight = 1.0 / len(domains) if domains else 0
    # ... compute KIS with uniform weight ...
```

**Impact:** Medium - adds flag + alternate code path

---

#### 6. **persona/council/dynamic_council.py**
Support disabling council for ablation.

**What to modify:**

```python
class DynamicCouncil:
    def __init__(self):
        self.disabled = False  # Add ablation flag
    
    def get_positions(self, user_input, context=None, override_disabled=False):
        if self.disabled and not override_disabled:
            return []  # No ministers when ablated
        
        # Normal council logic
        positions = [...]
        return positions
```

**Impact:** Low - adds one flag + early return

---

#### 7. **persona/pwm_integration/pwm_bridge.py**
Support disabling PWM sync for ablation.

**What to modify:**

```python
class PWMBridge:
    def __init__(self):
        self.disabled = False  # Add ablation flag
    
    def sync(self, session_data):
        if self.disabled:
            return  # No-op when ablated
        
        # Normal PWM sync logic
        self.pwm.update(session_data)
```

**Impact:** Low - adds one flag + return guard

---

#### 8. **persona/modes/mode_orchestrator.py**
Add baseline mode (direct LLM) and support forcing specific modes.

**What to modify:**

```python
class ModeOrchestrator:
    BASELINE_MODE = "BASELINE"  # Add new mode
    
    def decide(self, user_input, context=None, force_mode=None):
        # Support forcing a specific mode (for ablation)
        if force_mode:
            mode = force_mode
        else:
            mode = self.select_mode(user_input, context)
        
        if mode == self.BASELINE_MODE:
            return self._baseline_decision(user_input)  # Direct LLM
        elif mode == "QUICK":
            return self._quick_decision(user_input)
        # ... etc ...

def _baseline_decision(self, user_input):
    """Direct LLM approach - no council, no KIS, no ML prior, no memory"""
    llm = OllamaRuntime(model=self.speak_model)
    response = llm.call({
        "prompt": user_input,
        "system": "You are a thoughtful decision advisor. Provide your best reasoning."
    })
    return {
        "mode": "BASELINE",
        "decision": response["text"],
        "council_involved": False,
        "kis_involved": False,
        "ml_prior_used": False
    }
```

**Impact:** Medium - adds new mode + baseline logic

---

#### 9. **ml/retraining/retraining_loop.py** (if exists)
Skip retraining during evaluation.

**What to modify:**

```python
class RetrainingLoop:
    def __init__(self):
        self.evaluation_mode = False  # Add flag
    
    def trigger_retraining(self, episode_data):
        if self.evaluation_mode:
            return  # No retraining during evaluation
        
        # Normal retraining logic
        self._retrain_model(episode_data)
```

**Impact:** Medium (if retraining loop exists)

---

## Implementation Priority

### Phase 1 (CRITICAL)
- [ ] ml/sovereign_orchestrator.py - evaluation_mode flag + isolation guards
- [ ] persona/learning/episodic_memory.py - skip storing
- [ ] persona/council/dynamic_council.py - disable for ablation

### Phase 2 (IMPORTANT)
- [ ] ml/judgment/ml_judgment_prior.py - disable for ablation
- [ ] ml/kis/knowledge_integration_system.py - neutralize weights for ablation
- [ ] persona/pwm_integration/pwm_bridge.py - disable for ablation

### Phase 3 (NICE-TO-HAVE)
- [ ] persona/modes/mode_orchestrator.py - add BASELINE_MODE
- [ ] ml/metrics/performance_metrics.py - skip recording (low priority)
- [ ] ml/retraining/retraining_loop.py - skip retraining (if exists)

---

## Testing After Implementation

After making modifications, verify isolation works:

```python
from evaluation.evaluation_runner import EvaluationRunner

runner = EvaluationRunner()
assert runner.verify_dataset_integrity()
runner.enable_isolation_mode()

# Run a test evaluation
results = runner.run_evaluation(
    decision_engine=baseline_engine,
    run_name="test_baseline"
)

assert results["status"] == "COMPLETED"
assert results["outcome_summary"]["total_scenarios"] > 0
```

---

## Files That DON'T Need Changes

- `persona/state.py` - State management is OK
- `persona/session_manager.py` - Session logic is OK
- `persona/domain_detector.py` - Domain detection is OK
- `persona/trace.py` - Tracing is OK (evaluation_mode doesn't affect it)
- All test files - They can call evaluation_runner directly
- `data/` - Benchmark data is separate from operational data

---

## Key Principle

**Every modification adds exactly ONE flag that, when True, causes a function to become a no-op.**

This means:

✅ Easy to implement  
✅ Easy to test  
✅ Easy to revert  
✅ No complex logic changes  
✅ Forward-compatible with future features

---

## Status

| File | Phase | Status |
|------|-------|--------|
| ml/sovereign_orchestrator.py | 1 | ⏳ NEEDED |
| persona/learning/episodic_memory.py | 1 | ⏳ NEEDED |
| persona/council/dynamic_council.py | 1 | ⏳ NEEDED |
| ml/judgment/ml_judgment_prior.py | 2 | ⏳ NEEDED |
| ml/kis/knowledge_integration_system.py | 2 | ⏳ NEEDED |
| persona/pwm_integration/pwm_bridge.py | 2 | ⏳ NEEDED |
| persona/modes/mode_orchestrator.py | 3 | ⏳ NEEDED |
| Evaluation framework | - | ✅ COMPLETE |

---

**Next:** Make Phase 1 modifications, then run integration tests.
