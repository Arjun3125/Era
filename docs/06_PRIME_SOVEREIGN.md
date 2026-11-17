# ERA Sovereign & Prime Decision Logic

> **Source**: `sovereign/prime_confident.py`, `sovereign/doctrine_loader.py`,
> `modules/prime_decision/engine.py`

---

## 1. Identity & Role

**PrimeConfident** (identified internally as "N") serves as the final,
authoritative decision layer in the ERA pipeline. Its stated purpose is to act
as a "mirror with teeth" — preventing the Sovereign (the user) from self-deception,
especially under conditions of emotion, fatigue, or urgency.

Unlike the council ministers, which represent fragmented perspectives (Risk,
Power, Timing), Prime is the **synthesis point**.

---

## 2. Doctrine Enforcement

Prime operates strictly according to constraints loaded from YAML via
`DoctrineLoader` (`C:/era/data/doctrine/locked/n.yaml`).

### Core Worldview
- **Pattern Recurrence**: "Most damaging mistakes repeat with different justifications."
- **Emotional Distortion**: Recognizes when actions are driven by emotional relief rather than problem-solving.
- **Self-Deception Prevention**: Protects the Sovereign from rationalized sabotage.

### Self-Constraints (Prohibitions)
Prime enforces the following upon *itself*:
1. **Never decide alone**: Must validate against the council's consensus.
2. **Never moralize**: Must focus exclusively on consequences, not right vs. wrong.
3. **Never seek obedience**: Recommendations only; it must not usurp the Sovereign's agency.

---

## 3. Execution Logic

The `decide()` function in `PrimeConfident` operates as a filter cascade:

### Step 1: Constraint Verification
```python
def _apply_doctrine_constraints(council_rec):
```
Checks if the council's reasoning violates Prime's core constraints.
- **Trigger**: e.g., Finding moralizing terms (`should`, `evil`, `sin`) in reasoning.
- **Outcome**: Returns `{final_outcome: defer}`.

### Step 2: Emotional Distortion Detection
```python
def _analyze_emotional_distortion(council_rec):
```
Identifies decisions driven by urgency or emotional relief rather than grounded logic.
- **Trigger**: `avg_confidence > 0.7` AND `consensus_strength < 0.3`.
  (A high-confidence decision masking deep council disagreement implies emotional override).
- **Outcome**: Returns `{final_outcome: defer}` with a specific warning.

### Step 3: Pattern Recurrence Detection
```python
def _detect_pattern_recurrence(council_rec):
```
Identifies repeated self-sabotage logic.
- **Trigger**: Counting excessive rationalization terms (`but`, `however`, `despite`) > 2.
- **Outcome**: Returns `{final_outcome: defer}` with a specific warning.

### Step 4: Final Consensus Evaluation
If all constraints pass, Prime evaluates the council outcome:

**Outcome: `consensus_reached`**
- If `recommendation == support` AND `confidence >= risk_threshold`: `accept`
- Else: `defer`

**Outcome: `bounded_risk_tradeoff`**
- If Risk Minister `red_line_triggered`: `reject` (Fatal constraint).
- If Risk Minister `stance == oppose` AND `confidence >= risk_threshold`: `defer`.
- If overall `avg_confidence >= risk_threshold`: `accept_with_mitigation`.
- Else: `defer`

---

## 4. LLM Assessment Augmentation

After making the deterministic decision, Prime optionally uses an `llm_adapter` to
generate a final qualitative assessment:
- **Input**: Council recommendation, reasoning, and per-minister stances/confidences.
- **Output**: Generates a qualitative `score` and `reason` injected into the final payload as `llm_assessment`.
- **Failure**: Fails gracefully, logging to `persona.trace` without interrupting the decision pipeline.

---

## 5. Integration in Pipeline

In the `DecisionPipelineEngine`, **Stage 8** (`PrimeDecisionEngine`) is responsible for:
1. Validating and normalizing the output from Stage 7.
2. Handling explicit bypass conditions (e.g., `baseline` or `quick` mode, where Prime logic is bypassed).
3. Invoking `PrimeConfident.decide()`.
4. Formatting the result into the `DecisionContract` to pass to Stage 9 (Packaging).
