# ERA Minister Registry

> **Source**: `modules/council_execution/engine.py` — `NativeCouncil._build_ministers()`
> and `modules/council_router/mode_orchestrator.py` — `ModeStrategy` subclasses.

---

## 1. Overview

The Ministerial Cognitive Architecture (MCA) uses a council of **19 named
ministers**, each with a pre-configured bias, risk sensitivity, and keyword-driven
analysis logic. Ministers produce a stance (`support` / `oppose` / `neutral`),
a confidence score, reasoning text, and an optional red-line trigger.

---

## 2. Complete Minister Registry

| # | Minister Name | Default Bias | Strict on Risk | Domain Focus |
|---|---|---|---|---|
| 1 | `risk` | `oppose` | ✅ Yes | Downside protection, existential risks |
| 2 | `risk_resources` | `neutral` | ✅ Yes | Resource diversification, supply chain |
| 3 | `power` | `support` | ❌ No | Leverage, dominance, aggressive positioning |
| 4 | `grand_strategist` | `support` | ❌ No | Long-term strategy, expansion, partnerships |
| 5 | `technology` | `support` | ❌ No | Technical advantage, infrastructure, reliability |
| 6 | `timing` | `support` | ❌ No | Speed, urgency, strike timing |
| 7 | `optionality` | `support` | ❌ No | Pilots, experiments, reversibility |
| 8 | `data` | `neutral` | ❌ No | Data analysis, measurement, monitoring |
| 9 | `diplomacy` | `neutral` | ❌ No | Relationship management, negotiation |
| 10 | `psychology` | `neutral` | ❌ No | Behavioral analysis, emotional intelligence |
| 11 | `legitimacy` | `neutral` | ✅ Yes | Compliance, fraud detection, transparency |
| 12 | `conflict` | `oppose` | ❌ No | Conflict analysis, adversarial framing |
| 13 | `truth` | `neutral` | ❌ No | Honesty, deception detection |
| 14 | `discipline` | `support` | ❌ No | Consistency, follow-through |
| 15 | `intelligence` | `neutral` | ❌ No | Information gathering, analysis |
| 16 | `narrative` | `neutral` | ❌ No | Communication strategy, framing |
| 17 | `sovereign` | `support` | ❌ No | User agency, autonomy protection |
| 18 | `adaptation` | `support` | ❌ No | Flexibility, pivot capability |
| 19 | `war_mode` | `support` | ❌ No | Aggressive execution, competitive focus |

**Minister Aliases** (from `_MINISTER_ALIASES`):

| Alias | Resolves To |
|---|---|
| `resource`, `resources`, `risk_resource` | `risk_resources` |
| `grand_strategy`, `grandstrategy` | `grand_strategist` |
| `optional` | `optionality` |
| `sovereignty` | `sovereign` |

---

## 3. Minister Analysis Logic

### `_NativeMinister.analyze(user_input, context)` → `Dict`

Each minister runs a deterministic keyword-scoring analysis:

```python
def analyze(self, user_input: str, context: Mapping[str, Any]) -> Dict[str, Any]:
    # 1. Extract option text if present ("option: ...")
    # 2. Read domains from context
    # 3. Score keywords:
    urgency   = keyword_score(text, SPEED_KEYWORDS)
    risk_score = keyword_score(text, RISK_KEYWORDS)
    uncertainty = keyword_score(text, UNCERTAINTY_KEYWORDS)

    # 4. Determine stance based on bias + scores
    # 5. Compute confidence
    # 6. Return {stance, confidence, reasoning, red_line_triggered}
```

### Keyword Sets

**Risk Keywords** (`_NATIVE_RISK_KEYWORDS`):
```
risk, loss, bankrupt, legal, irreversible, debt, downside
```

**Speed Keywords** (`_NATIVE_SPEED_KEYWORDS`):
```
urgent, deadline, immediately, now, fast
```

**Uncertainty Keywords** (`_NATIVE_UNCERTAINTY_KEYWORDS`):
```
uncertain, unknown, ambiguous, guess
```

### Stance Determination Rules

| Condition | Resulting Stance |
|---|---|
| `strict_on_risk` AND `risk_score >= 0.25` | `oppose` |
| `risk` domain AND risk minister AND `risk_score >= 0.15` | `oppose` |
| `urgency >= 0.25` AND minister ∈ {timing, technology, grand_strategist} | `support` |
| `uncertainty >= 0.35` | `neutral` |
| None of the above | Uses minister's default `bias` |

### Option-Based Override

When user input contains `"option: <text>"`, ministers check for domain-specific
support/oppose terms:

**Support Terms by Minister**:

| Minister | Support Terms |
|---|---|
| `risk` | contain, patch, audit, shut, mitigate, harden, pause, halt, stop |
| `risk_resources` | diversify, backup, buffer, stockpile, dual-source |
| `grand_strategist` | expand, acquire, partner, launch, enter, differentiate, growth |
| `timing` | launch now, immediately, move fast, now |
| `technology` | reliability, infrastructure, stability, platform |
| `legitimacy` | disclose, transparent, audit, compliance, communicate, open |
| `truth` | disclose, transparent, communicate, open |
| `optionality` | pilot, beta, limited, experiment, pause, delay |
| `data` | monitor, measure, analyze, report, review |
| `power` | aggressive, attack, price cut, dominate |

**Oppose Terms by Minister**:

| Minister | Oppose Terms |
|---|---|
| `risk` | ignore, deny, do nothing, monitor only, release, ship, launch |
| `legitimacy` | deny, quiet, cover, ignore, dismiss |
| `truth` | deny, quiet, cover, dismiss |
| `timing` | delay, pause, wait |
| `power` | retreat, exit, abandon, withdraw |

### Confidence Calculation

```python
if stance == "support":
    confidence = 0.65 + urgency * 0.2
elif stance == "oppose":
    confidence = 0.65 + risk_score * 0.25
else:  # neutral
    confidence = 0.55
# Clamped to [0.0, 1.0]
```

### Red Line Trigger

```python
red_line_triggered = (strict_on_risk AND risk_score >= 0.35)
```

Only ministers with `strict_on_risk=True` can trigger red lines:
- `risk`
- `risk_resources`
- `legitimacy`

---

## 4. Ministers Per Mode

### Quick Mode — 0 ministers
No council invoked. Direct LLM response.

### War Mode — 5 ministers
```python
["risk", "power", "grand_strategist", "technology", "timing"]
```
Frame: "How do we WIN?"

### Meeting Mode — 3–5 ministers (dynamic)

Selected based on domain detection:

| Detected Domain | Ministers Selected (top 2) |
|---|---|
| `career` | grand_strategist, psychology |
| `financial` | risk, optionality |
| `relationships` | diplomacy, psychology |
| `health` | psychology, timing |
| `strategy` | grand_strategist, intelligence |
| `power` | power, diplomacy |
| `ethics` | legitimacy, truth |
| `innovation` | technology, grand_strategist |

`risk` is **always included** as a sanity check. Capped at 5 ministers total.

### Darbar Mode — 18 ministers (full council)
```python
["adaptation", "conflict", "diplomacy", "data", "discipline",
 "grand_strategist", "intelligence", "timing", "risk", "power",
 "psychology", "technology", "legitimacy", "truth", "narrative",
 "resources", "optionality", "sovereign"]
```
Frame: Full doctrine-driven deliberation with red-line enforcement.

---

## 5. Consensus Aggregation Per Mode

### War Mode
```python
war_alignment = support_count / total_ministers
ethical_override_allowed = False  # NEVER
```

### Meeting Mode
```python
consensus_quality = "high" if abs(support - oppose) >= total * 0.6 else "mixed"
support_ratio = support_count / total
```

### Darbar Mode
```python
consensus_strength = support_count / total
requires_prime_confident_review = len(red_line_concerns) > 0
```
