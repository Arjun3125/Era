# Plan C — Arthashastra Council Protocol
**Date:** 2026-05-18
**Scope:** Implement the full Kautilya/Arthashastra deliberation model into ERA's council pipeline
**Goal:** Every decision goes through: bias detection → power mapping → method classification → structured minister output (Sthiti→Vikalpa→Mata) → stakeholder analysis → capability check → victory definition → sovereign synthesis

---

## Problem

ERA's council is a simplified voting system. The original Pradhan Mandal that inspired it was a multi-stage deliberation protocol with explicit pre-conditions, structured reasoning phases, and post-council checks before the sovereign decided. ERA jumps straight to minister votes, missing 7 stages that made the original system effective.

---

## The Full Enhanced Flow

```
User Input
    ↓
[1] Arishadvarga Detector
    — detect 6 cognitive biases in user's framing
    — if high severity: clean the situation text before it reaches ministers
    ↓
[2] Mandala Analyzer
    — map power positions: who is Ari, Mitra, potential ally, neutral
    — assess relative strength of decision-maker
    ↓
[3] Upaya Classifier
    — assess feasibility of each method: Sama / Dana / Bheda / Danda
    — recommend method priority order
    ↓
[4] Knowledge Synthesis (existing, unchanged)
    ↓
[5] Ministers deliberate — NEW Sthiti→Vikalpa→Mata structure
    — STHITI: facts only, no opinion
    — VIKALPA: all options including uncomfortable ones, labeled by type
    — MATA: recommendation citing Sthiti fact + doctrine principle + minimum acceptable
    ↓
[6] Prakritis Analyst
    — map stakeholder consequences of the council's recommendation
    — identify unintended second-order effects
    ↓
[7] Prabhu Shakti + Utsaha Shakti checks
    — Prabhu: is the decision-maker capable of executing this?
    — Utsaha: can the organization actually do this?
    ↓
[8] Sandhi Synthesis
    — define minimum acceptable outcome, target outcome, stop condition
    — classify settlement type: karyasandhi / vibhaga / kala / uchchhinna
    ↓
[9] Sovereign speak()
    — receives full structured context from all 8 stages
    — CoT synthesis prefix injected before speak() call
```

---

## Components

### 1. Arishadvarga Detector
**File:** `persona/analysis.py` — new function `detect_arishadvarga(llm, situation)`

Detects 6 cognitive distortions in user's framing:
- KAMA: decision enables what user already wanted regardless of merit
- KRODHA: reactive anger driving decision ("betrayed", "unfair", "how dare")
- LOBHA: scope creep beyond core goal
- MOHA: wishful assumptions presented as facts
- MADA: underestimating opposition capability
- MATSARYA: competitive spite ("even if it costs us")

**Output:**
```json
{
  "active_enemies": ["KRODHA", "MOHA"],
  "evidence": {"KRODHA": "phrase X suggests reactive framing"},
  "corrective_injection": "cleaned situation text with emotional language removed",
  "severity": "low|medium|high"
}
```

**Integration:** If `severity == "high"`, `corrective_injection` replaces situation text passed to ministers. Both original and cleaned versions go to sovereign.

### 2. Mandala Analyzer
**File:** `persona/analysis.py` — new function `analyze_mandala(llm, situation)`

Maps power relationships using Kautilya's Rajamandala theory:
- Ari (direct obstacle/opponent)
- Mitra (current assets/allies)
- Ari-Ari (opponent's enemies = potential allies)
- Neutral parties who could be swayed

Assesses: power position (strong/middling/weak), leverage held, leverage faced.

**Output:**
```json
{
  "power_position": "middling",
  "ari": {"name": "...", "strength": 0.7},
  "mitra": [{"name": "...", "reliability": 0.8}],
  "potential_allies": [{"name": "...", "activation_cost": "..."}],
  "leverage_you_hold": "...",
  "leverage_they_hold": "...",
  "recommended_posture": "indirect"
}
```

**Integration:** Injected into minister prompt context as `mandala_context`.

### 3. Upaya Classifier
**File:** `persona/analysis.py` — new function `classify_upaya(llm, situation, mandala)`

Assesses feasibility of 4 methods in hierarchy order:
- Sama (conciliation): feasibility + concrete path
- Dana (incentive): feasibility + what could be offered
- Bheda (divide): feasibility + which fracture lines exist
- Danda (force/direct action): feasibility + what action is available

**Output:**
```json
{
  "sama_feasibility": 0.3,
  "sama_path": "...",
  "dana_feasibility": 0.7,
  "dana_path": "...",
  "bheda_feasibility": 0.5,
  "bheda_path": "...",
  "danda_feasibility": 0.9,
  "danda_path": "...",
  "recommended_upaya": "dana",
  "reason": "..."
}
```

**Integration:** Injected into minister prompt as `upaya_context`. Ministers reason within the method frame.

### 4. Sthiti→Vikalpa→Mata Minister Output
**File:** `persona/council/minister_voice.py`

Replace `_MINISTER_INSTRUCTION` with three-stage structured output.

**New schema:**
```json
{
  "sthiti": ["verifiable fact 1", "verifiable fact 2"],
  "vikalpa": [
    {"id": "V0", "type": "INACTION", "description": "Do nothing. Current trajectory continues. Cost of inaction: X"},
    {"id": "V1", "type": "AGGRESSIVE", "description": "..."},
    {"id": "V2", "type": "DEFENSIVE", "description": "..."},
    {"id": "V3", "type": "LATERAL", "description": "..."}
  ],
  "mata": {
    "recommended_vikalpa": "V2",
    "doctrine_reason": "...",
    "minimum_acceptable": "V3",
    "confidence": 0.85,
    "warning": "...",
    "knowledge_gaps": ["fact we don't know that would change this", "..."],
    "decision_quality": "high|medium|low|defer"
  }
}
```

Vikalpa types: INACTION / AGGRESSIVE / DEFENSIVE / LATERAL / RETREAT / DELAY / HYBRID

**V0 — Inaction is mandatory.** Every minister must enumerate the cost of doing nothing before recommending action. Ministers who recommend action over inaction must explicitly justify why inaction is worse.

**Knowledge gaps:** Ministers explicitly flag missing information that would flip their recommendation. If ≥3 ministers flag the same gap → council output includes `"decision_quality": "defer"` and sovereign recommends information gathering before action.

**Aggregation:** Council engine counts Vikalpa references across all ministers — most-cited option wins even if ministers disagree on which to recommend. This is richer than a stance majority.

### 5. Prakritis Analyst
**File:** `persona/analysis.py` — new function `analyze_prakritis(llm, situation, council_recommendation)`

Maps stakeholder consequences after council deliberates.

**Output:**
```json
{
  "stakeholders": [
    {
      "name": "...",
      "relationship": "ally|neutral|competitor|unknown",
      "impact": "positive|negative|neutral",
      "response_prediction": "...",
      "secondary_effect": "...",
      "risk_level": 0.7
    }
  ],
  "highest_risk_stakeholder": "...",
  "unintended_consequence": "..."
}
```

### 6. Prabhu Shakti + Utsaha Shakti
**File:** `persona/analysis.py` — new functions `check_prabhu_shakti(llm, situation, recommendation)` and `check_utsaha_shakti(llm, situation, recommendation)`

**Prabhu Shakti output:**
```json
{
  "arishadvarga_in_recommendation": ["MADA"],
  "bias_explanation": "...",
  "prabhu_shakti_score": 0.6,
  "recommendation": "Proceed with defensive option only"
}
```

**Utsaha Shakti output:**
```json
{
  "execution_risk": 0.7,
  "critical_assumption": "...",
  "minimum_viable_version": "...",
  "fatal_flaw": "..."
}
```

**Integration:** If `prabhu_shakti_score < 0.5` AND `utsaha_shakti.execution_risk > 0.7` → sovereign is forced to recommend `minimum_viable_version` over council recommendation.

### 7. Sandhi Synthesis
**File:** `persona/analysis.py` — new function `synthesize_sandhi(llm, council_recommendation, shakti_results)`

**Output:**
```json
{
  "minimum_acceptable_outcome": "...",
  "target_outcome": "...",
  "stop_condition": "...",
  "sandhi_type": "karyasandhi",
  "overreach_warning": "...",
  "reversibility": "high|medium|low|irreversible",
  "minimum_confidence_required": 0.85
}
```

**Reversibility gate:** `minimum_confidence_required` scales with reversibility:
- `irreversible` → 0.85 minimum council confidence required
- `low` → 0.75
- `medium` → 0.65
- `high` → 0.55

If average council `mata.confidence` < `minimum_confidence_required` → sovereign is forced to flag: *"Confidence insufficient for a decision of this reversibility. Recommend: gather information first."*

**Integration:** Appended to sovereign context. If `sandhi_type == "uchchhinna"` and `prabhu_shakti_score < 0.6` → sovereign flags overreach.

### 8. Pre-Mortem
**File:** `persona/analysis.py` — new function `run_premortem(llm, situation, council_recommendation)`

Distinct from Utsaha Shakti. Utsaha asks "can we execute?" Pre-mortem assumes perfect execution and asks "what still goes wrong?"

Prompt: *"Assume this plan was executed flawlessly. One year later it has completely failed. Generate 3 specific, realistic failure scenarios — not execution failures, but strategic ones. What did we not see coming?"*

**Output:**
```json
{
  "failure_scenarios": [
    {"scenario": "...", "probability": 0.4, "leading_indicator": "early warning sign to watch for"},
    {"scenario": "...", "probability": 0.3, "leading_indicator": "..."},
    {"scenario": "...", "probability": 0.2, "leading_indicator": "..."}
  ],
  "blind_spot": "The assumption we are most confident about that is most likely wrong"
}
```

**Integration:** Goes to sovereign context. Leading indicators become the "watch for these signs" section of the final recommendation.

### 9. Pratikula (Devil's Advocate)
**File:** `modules/council_execution/engine.py` — new round triggered on high consensus

**Trigger:** After Round 1, if ≥80% of ministers share the same stance → consensus is too clean. Real councils treated high consensus as a warning sign, not confidence.

**Mechanism:**
1. Identify the minister with highest confidence in majority stance → force them to argue the opposing case
2. Identify the weakest minority minister → force them to make the strongest possible case for majority
3. Run both as new `MinisterVoice.deliberate()` calls with explicit instruction: *"You must argue [opposite stance]. Find the strongest possible case. Do not break character — your doctrine must support this position."*
4. Append both outputs to sovereign context as "STRESS TEST ARGUMENTS"

**Integration:** Sovereign sees: original council + stress-test counter-arguments. Forced to address them before recommending.

### 10. Outcome Tracking
**File:** `persona/analysis.py` — new function `record_outcome(session_id, recommendation, outcome)`
**File:** `persona/session_manager.py` — extend to store pending outcomes

After sovereign speaks, ERA logs the recommendation to a pending outcomes store. On the user's **next session**, ERA checks if there are any pending outcomes and asks 2 questions:

1. *"Last time we discussed [situation summary]. Did you follow the recommendation?"* (yes/no/partially)
2. *"What happened?"* (free text)

Maps outcome to which ministers predicted closest → feeds `MinisterConfidenceTracker` with real signal.

**Storage:** `data/outcomes/outcomes.jsonl` — append-only log. Each entry: `{session_id, situation_hash, recommendation_summary, minister_votes, outcome_text, followed: bool, timestamp}`.

**Integration:** `MinisterConfidenceTracker.update_from_outcome(minister_name, domain, was_correct: bool)` — already has the Bayesian update mechanism, just needs real data.

---

## Integration Points (Exact Files)

| Stage | File Modified | Function/Location |
|-------|--------------|-------------------|
| Arishadvarga | `persona/analysis.py` | New: `detect_arishadvarga()` |
| Mandala | `persona/analysis.py` | New: `analyze_mandala()` |
| Upaya | `persona/analysis.py` | New: `classify_upaya()` |
| Minister schema | `persona/council/minister_voice.py` | Replace `_MINISTER_INSTRUCTION` — adds V0 + knowledge_gaps + decision_quality |
| Minister aggregation | `modules/council_execution/engine.py` | `_llm_deliberate()` — new aggregation + knowledge gap counting + Pratikula trigger |
| Prakritis | `persona/analysis.py` | New: `analyze_prakritis()` |
| Prabhu Shakti | `persona/analysis.py` | New: `check_prabhu_shakti()` |
| Utsaha Shakti | `persona/analysis.py` | New: `check_utsaha_shakti()` |
| Sandhi | `persona/analysis.py` | New: `synthesize_sandhi()` — adds reversibility + confidence gate |
| Pre-mortem | `persona/analysis.py` | New: `run_premortem()` |
| Pratikula | `modules/council_execution/engine.py` | New round in `_llm_deliberate()` — triggers on ≥80% consensus |
| Outcome tracking | `persona/analysis.py` + `persona/session_manager.py` | New: `record_outcome()` + pending outcome check on session start |
| Sovereign context | `persona/main.py:582` | Modify `system_context` — includes pre-mortem, reversibility gate, leading indicators |

---

## Non-Goals
- No changes to quick/war mode (keyword path unchanged)
- No changes to ingestion (Plan B)
- No changes to Plan A techniques (those apply on top)
- No new dependencies (all LLM calls via existing `OllamaRuntime.analyze()`)
- No changes to minister YAML doctrine files

---

## Success Criteria
- Every Vikalpa list contains V0 (INACTION) with explicit cost-of-inaction
- `knowledge_gaps` non-empty on ≥50% of deliberations
- `decision_quality == "defer"` triggered when ≥3 ministers flag same missing fact
- Reversibility gate fires on irreversible decisions with avg confidence < 0.85
- Pre-mortem produces ≥3 failure scenarios with leading indicators
- Pratikula round triggers when Round 1 consensus ≥ 80%
- Outcome tracking stores to `data/outcomes/outcomes.jsonl`
- Pending outcome check appears on next session after a decision
- Arishadvarga flags KRODHA/MOHA on emotionally-loaded test inputs
- Upaya classifier recommends Sama or Dana before Danda for non-emergency inputs
- Sovereign speak context includes pre-mortem leading indicators + reversibility warning
- Quick mode unaffected (all new stages bypass on `mode == "quick"`)
