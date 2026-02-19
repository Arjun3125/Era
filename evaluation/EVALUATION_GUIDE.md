# Evaluation System - Research-Grade Benchmarking

## Overview

ERA's evaluation framework enables **research-grade statistical validation** of decision quality through:

- ✅ **Frozen Datasets** with SHA256 integrity verification
- ✅ **Isolation Mode** preventing live system contamination
- ✅ **Multi-Seed Runs** (5 seeds) for statistical rigor
- ✅ **Ablation Matrix** measuring component importance
- ✅ **Statistical Validation** with paired t-tests, effect sizes, calibration curves
- ✅ **Model Versioning** tracking all weights and configurations

## Hard Rules

### 1. Dataset Integrity (Non-Negotiable)

```python
if not rubric_engine.verify_dataset_integrity():
    logger.error("❌ DATASET INTEGRITY CHECK FAILED - ABORTING EVALUATION")
    sys.exit(1)
```

**No hash match → abort evaluation. Period.**

### 2. Isolation Mode (Must Be Enabled)

During evaluation:

```python
evaluation_mode = True  # In ml/sovereign_orchestrator.py

# This DISABLES:
❌ episodic_memory.store_episode()
❌ performance_metrics.record_decision()
❌ system_retraining
❌ pwm_sync

# This LOCKS:
🔒 ML model weights
🔒 KIS weights  
🔒 Minister confidence
```

**No writing to live system during benchmark. Period.**

### 3. No Dataset Leakage

The evaluation runner prevents:

```python
❌ Pattern extraction from test scenarios
❌ Retraining on evaluation data
❌ Label generation from eval outcomes
❌ KIS reinforcement from eval results
```

**Training set and test set must be completely separate. Period.**

## Directory Structure

```
evaluation/
├── benchmark_dataset/
│   ├── irreversible.json          # 25 irreversible decision scenarios
│   ├── emotional.json              # 25 emotionally complex scenarios
│   ├── strategic.json              # 25 strategic/long-term scenarios
│   ├── long_horizon.json           # 25 delayed consequence scenarios
│   └── dataset_manifest.json       # SHA256 hashes + integrity metadata
├── scoring/
│   ├── outcome_scorer.py           # Rubric-based scoring
│   ├── regret_scorer.py            # Regret quantification
│   └── rubric_engine.py            # Scenario loading + hash verification
├── evaluation_runner.py            # Main orchestrator
├── stats_engine.py                 # Statistical validation (5 seeds, CI, t-tests, Cohen's d)
└── MODEL_VERSION.json              # Version tracking + configuration snapshot
```

## Scenario Format

Each benchmark scenario includes:

```json
{
  "id": "IRR_001",
  "category": "irreversible",
  "input": "Should I sell my company now or wait?",
  "context": "Company valued at $10M, 80% revenue from one customer, market uncertainty...",
  
  "ground_truth_rubric": {
    "principles_required": [
      "optionality",
      "downside_asymmetry",
      "reversibility",
      "time_value"
    ],
    
    "critical_failure_modes": [
      "ignoring_cashflow",
      "missing_customer_risk",
      "not_considering_timing"
    ],
    
    "acceptable_paths": [
      "sell_with_downside_protection",
      "partial_exit_structure",
      "wait_for_clarity"
    ]
  },
  
  "regret_scale": {
    "catastrophic": 1.0,
    "moderate": 0.5,
    "minimal": 0.1
  }
}
```

## Usage

### 1. Verify Integrity

```python
from evaluation.evaluation_runner import EvaluationRunner

runner = EvaluationRunner()

# HARD RULE: Abort if hashes don't match
if not runner.verify_dataset_integrity():
    sys.exit(1)  # Mandatory abort
```

### 2. Run Baseline (Direct LLM, no council)

```python
def baseline_decision_engine(scenario):
    """Direct LLM approach - no council, no KIS, no ML prior"""
    llm = OllamaRuntime(model='deepseek-r1:8b')
    response = llm.call(scenario["input"])
    return response["decision_path"], response["rationale"]

baseline_results = runner.run_evaluation(
    decision_engine=baseline_decision_engine,
    run_name="baseline"
)
```

### 3. Run Council Approach

```python
def council_decision_engine(scenario):
    """Full council approach with escalation"""
    orchestrator = ModeOrchestrator()
    response = orchestrator.decide(
        scenario["input"],
        evaluation_mode=True  # Isolation mode!
    )
    return response["decision_path"], response["rationale"]

council_results = runner.run_evaluation(
    decision_engine=council_decision_engine,
    run_name="council"
)
```

### 4. Run Ablations

```python
# Measure importance of each component
ablation_results = runner.ablation_analysis(
    decision_engine=council_decision_engine,
    baseline_results=council_results
)

# Output:
# {
#   "no_ministers": {
#     "performance_delta": 0.15,     # 15% drop when ministers disabled
#     "percent_decrease": 8.5,
#     "component_importance": "HIGH"
#   },
#   "no_kis_weighting": {
#     "performance_delta": 0.08,
#     "percent_decrease": 4.2,
#     "component_importance": "MEDIUM"
#   },
#   ...
# }
```

### 5. Compute Statistics

```python
# Paired t-test comparing baseline vs council
comparison = runner.compare_runs("baseline", "council")

# Output:
# {
#   "baseline_mean": 0.62,
#   "comparison_mean": 0.77,
#   "mean_difference": 0.15,
#   "t_statistic": 4.23,
#   "p_value": 0.0012,
#   "significant_at_005": True,
#   "cohens_d": 1.84,  # Large effect size
# }
```

## Integration Points

### 1. Sovereign Orchestrator (`ml/sovereign_orchestrator.py`)

Add evaluation mode flag:

```python
class SovereignOrchestrator:
    def decide(self, user_input, evaluation_mode=False):
        if evaluation_mode:
            # DISABLE live updates
            disable_episodic_memory_store()
            disable_performance_metrics()
            disable_retraining_trigger()
            disable_pwm_sync()
            lock_ml_weights()
            lock_kis_weights()
        
        # Continue with normal decision logic
        return decision_response
```

### 2. Dynamic Council (`persona/council/dynamic_council.py`)

Support ablation flag:

```python
class DynamicCouncil:
    def get_positions(self, user_input, override_disabled=False):
        if self.disabled and not override_disabled:
            return []
        # Normal execution
```

### 3. ML Prior (`ml/judgment/ml_judgment_prior.py`)

Support disabling:

```python
class MLJudgmentPrior:
    def predict_outcome(self, feature_vector):
        if self.disabled:
            return None  # No ML prior
        # Normal execution
```

### 4. KIS (`ml/kis/knowledge_integration_system.py`)

Support neutralizing weights:

```python
class KnowledgeIntegrationSystem:
    def synthesize_knowledge(self, input, domains):
        if self.weights_neutralized:
            # Use uniform weights instead of learned weights
            return self._synthesize_uniform(input, domains)
        # Normal execution
```

### 5. PWM Bridge (`persona/pwm_integration/pwm_bridge.py`)

Support disabling:

```python
class PWMBridge:
    def sync(self, session_data):
        if self.disabled:
            return  # No-op
        # Normal sync
```

## Statistical Methods

### Confidence Intervals

- **Method:** Bootstrap resampling (1000 samples)
- **Confidence Level:** 95%
- **Interpretation:** If we resampled 100 times, the true mean would fall in this range 95 times

### Paired t-Test

- **When:** Comparing baseline vs council on same 100 scenarios
- **Null Hypothesis:** Council approach has same mean score as baseline
- **Effect Size:** Cohen's d (>1.2 = large effect)
- **Interpretation:** p < 0.05 means statistically significant difference

### Calibration (Brier Score)

- **Formula:** Mean squared error between confidence and actual outcome
- **Range:** 0 (perfect) to 1 (worst)
- **Interpretation:** How well does model confidence match actual performance?

### Ablation Effect Size

- **Metric:** Performance delta / pooled std dev
- **Interpretation:** How many standard deviations does performance drop?

## Example Results Output

```json
{
  "model_version": "v1.0.0-baseline",
  "runs": {
    "baseline": {
      "status": "COMPLETED",
      "aggregated_statistics": {
        "overall_mean": 0.62,
        "seed_consistency": "high"
      },
      "confidence_interval": {
        "mean": 0.6183,
        "lower_95": 0.5840,
        "upper_95": 0.6521,
        "effect_size": 0.73
      },
      "outcome_summary": {
        "pass_rate": 0.62,
        "by_category": {
          "irreversible": {"pass_rate": 0.48, "mean_score": 0.51},
          "emotional": {"pass_rate": 0.68, "mean_score": 0.72},
          "strategic": {"pass_rate": 0.64, "mean_score": 0.65},
          "long_horizon": {"pass_rate": 0.68, "mean_score": 0.69}
        }
      }
    },
    "council": {
      "status": "COMPLETED",
      "aggregated_statistics": {
        "overall_mean": 0.77,
        "seed_consistency": "high"
      },
      "confidence_interval": {
        "mean": 0.7712,
        "lower_95": 0.7301,
        "upper_95": 0.8103,
        "effect_size": 1.24
      }
    }
  },
  "comparison": {
    "baseline_vs_council": {
      "mean_difference": 0.15,
      "t_statistic": 4.23,
      "p_value": 0.0012,
      "significant_at_005": true,
      "cohens_d": 1.84
    }
  },
  "ablations": {
    "no_ministers": {"performance_delta": 0.15, "component_importance": "HIGH"},
    "no_kis_weighting": {"performance_delta": 0.08, "component_importance": "MEDIUM"},
    "no_ml_prior": {"performance_delta": 0.05, "component_importance": "MEDIUM"},
    "no_pwm": {"performance_delta": 0.03, "component_importance": "LOW"},
    "no_mode_escalation": {"performance_delta": 0.10, "component_importance": "HIGH"}
  }
}
```

## Key Guarantees

1. **Reproducibility:** Five fixed seeds guarantee exact replication
2. **Isolation:** No contamination of live system during testing
3. **Integrity:** SHA256 hashes prevent data tampering
4. **Validity:** Statistical methods (t-tests, CI, effect sizes) provide rigor
5. **Interpretability:** Ablation matrix shows WHY improvements happen

## This Is Not Optional

Without this framework:

❌ Improvement claims are narrative  
❌ Ablation insight is speculative  
❌ You cannot compare versions  
❌ You cannot publish  
❌ You cannot scale credibly  

With this framework:

✅ Measured council lift  
✅ Measured component importance  
✅ Measured PWM contribution  
✅ Statistical significance  
✅ Confidence intervals  
✅ Effect sizes  
✅ **Research-grade validation**
