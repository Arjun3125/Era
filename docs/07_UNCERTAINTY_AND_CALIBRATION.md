# ERA Uncertainty & Calibration

> **Source**: `modules/uncertainty/`, `modules/council_router/mode_orchestrator.py`

---

## 1. Uncertainty Framework

ERA actively measures, models, and calibrates uncertainty across the pipeline. 
Rather than blindly trusting minister confidences or LLM logits, the system computes 
composite risk scores and calibrates probabilities to ensure reliable decision-making.

---

## 2. Composite Uncertainty Signals

The `ModeOrchestrator` relies on an `UncertaintyPolicyConfig` to dynamically adjust 
modes (e.g., escalating from `meeting` to `darbar` mode) based on uncertainty.

The composite uncertainty score $U$ is calculated based on three factors:

1. **Policy Entropy ($H$)**: How divided the council is.
2. **Value Variance ($V$)**: How much the confidence scores vary among ministers.
3. **Dissent Level ($D$)**: The strength of the opposing minority.

These metrics are managed via the `RiskModel` (`modules/uncertainty/risk_model.py`):

```python
class RiskModel:
    policy_weight: float = 0.4
    value_weight: float = 0.3
    dissent_weight: float = 0.3
```

**Score Calculation**:
```
Risk = (0.4 * PolicyEntropy) + (0.3 * ValueVariance) + (0.3 * DissentLevel)
```

---

## 3. Calibration Metrics

ERA implements standard probabilistic calibration metrics to evaluate how closely 
the predicted confidence matches actual outcome accuracy (`modules/uncertainty/metrics.py`).

### Expected Calibration Error (ECE)
Partitions predictions into $N$ bins (default 10) based on confidence.
Calculates the weighted average of the absolute difference between average accuracy 
and average confidence in each bin.

$$ ECE = \sum_{m=1}^{M} \frac{|B_m|}{n} |acc(B_m) - conf(B_m)| $$

### Brier Score
Measures the mean squared difference between predicted probability and actual outcome 
(1 for correct, 0 for incorrect).

$$ BS = \frac{1}{N} \sum_{t=1}^{N} (f_t - o_t)^2 $$

---

## 4. Temperature Scaling Calibration

To correct overconfident or underconfident models, ERA implements Temperature Scaling 
(`modules/uncertainty/calibration.py`).

### Mechanism
```python
def calibrate(self, confidence: float) -> float:
    t = max(1e-3, float(self.temperature))
    logit = log(confidence / (1.0 - confidence))
    scaled = logit / t
    return 1.0 / (1.0 + exp(-scaled))
```

### Fitting
The `fit_temperature` function optimizes the temperature parameter $T$ by performing a 
grid search (from $0.5$ to $5.0$) to minimize the Negative Log-Likelihood (NLL) against 
a set of ground-truth labels.

The calibrated temperature can be saved to and loaded from a JSON file.

---

## 5. Mode Escalation Protocol

`ModeOrchestrator.apply_uncertainty_control` uses the computed uncertainty signals:

1. Calculate Composite Uncertainty $U$.
2. If $U \geq$ `escalation_threshold` (e.g., $0.65$):
    - Escalate to `darbar` mode (full council).
3. If $U \leq$ `deepen_threshold` (e.g., $0.35$):
    - Allow rapid progression.
4. Set `require_human_feedback = True` if uncertainty remains unacceptably high.
