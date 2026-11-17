# ERA Arthashastra Council Protocol

> **Status:** Designed — see `docs/superpowers/specs/2026-05-18-arthashastra-council-design.md`
> **Implementation:** `docs/superpowers/plans/2026-05-18-arthashastra-council.md` (Tasks 1–12)

---

## 1. Origin and Rationale

ERA's council of ministers is modeled on **Kautilya's Arthashastra** (~300 BCE) — the operational manual of Chandragupta Maurya's empire, and the governing doctrine of Ashoka's **Pradhan Mandal** (council of ministers).

The original system was not a voting mechanism. It was a structured deliberation protocol with explicit pre-conditions, staged reasoning, and post-council checks before the sovereign acted. ERA's current implementation captures the voting structure but misses 9 critical stages that made the original effective.

This document describes the full protocol ERA is being upgraded to implement.

---

## 2. The Original vs ERA Current

| Dimension | Ashoka's Pradhan Mandal | ERA Current | ERA After Protocol |
|-----------|------------------------|-------------|-------------------|
| Pre-deliberation | Spy chief briefed all ministers first | None | Arishadvarga + Mandala + Upaya |
| Minister output | Sthiti → Vikalpa → Mata (3 stages) | Single stance vote | Full 3-stage JSON |
| Inaction option | Always on the table | Never listed | V0 forced in every Vikalpa |
| High consensus | Treated as a warning (groupthink) | Treated as confidence | Pratikula fires ≥80% |
| Knowledge gaps | Explicitly surfaced | Silent | `knowledge_gaps` field |
| Post-council | Capability + feasibility check | None | Prabhu/Utsaha Shakti |
| Victory definition | Defined before action | None | Sandhi synthesis |
| Reversibility | Scaled confidence bar | Uniform | Reversibility gate |
| Pre-mortem | Standard practice | None | `run_premortem()` |
| Outcome tracking | Ministers evaluated on results | Partially (Bayesian weights) | Full outcome loop |

---

## 3. The 9-Stage Pre/Post Protocol

### Full Enhanced Flow

```
User Input
    ↓
┌─────────────────────────────────────────────────────────┐
│  PRE-DELIBERATION (3 LLM calls)                         │
│                                                          │
│  [1] ARISHADVARGA DETECTOR                               │
│      Detect 6 cognitive biases in user's framing:       │
│      KAMA / KRODHA / KRODHA / LOBHA / MOHA / MADA /    │
│      MATSARYA                                            │
│      If high severity → clean situation text            │
│      before ministers see it                             │
│                                                          │
│  [2] MANDALA ANALYZER                                    │
│      Map power relationships:                            │
│      Ari (opponent) / Mitra (allies) /                  │
│      Potential allies (Ari-Ari) / Neutrals              │
│      Assess: strong / middling / weak position          │
│      Recommend: direct / indirect / alliance / delay    │
│                                                          │
│  [3] UPAYA CLASSIFIER                                    │
│      Assess feasibility of 4 methods in order:          │
│      Sama (conciliate) → Dana (incentivize) →           │
│      Bheda (divide) → Danda (force)                     │
│      Recommend method + concrete path                   │
└─────────────────────────────────────────────────────────┘
    ↓  (Arishadvarga + Mandala + Upaya injected as context)
┌─────────────────────────────────────────────────────────┐
│  KNOWLEDGE SYNTHESIS                                     │
│  (existing KIS engine — unchanged)                      │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  MINISTER DELIBERATION (parallel LLM calls)             │
│                                                          │
│  [4] STHITI → VIKALPA → MATA (per minister)             │
│                                                          │
│  STHITI: Facts only. Zero opinion. No adjectives        │
│  implying judgment. Verifiable truth only.              │
│                                                          │
│  VIKALPA: ALL options including uncomfortable ones.     │
│  V0 (INACTION) is MANDATORY — first option always.     │
│  Types: INACTION / AGGRESSIVE / DEFENSIVE /             │
│         LATERAL / RETREAT / DELAY / HYBRID              │
│                                                          │
│  MATA: Recommendation citing one Sthiti fact +          │
│  one doctrine principle. Flags knowledge_gaps.          │
│  Rates decision_quality: high/medium/low/defer          │
│                                                          │
│  Self-consistency: 3 parallel samples, majority vote    │
│  (Plan A enhancement)                                   │
│                                                          │
│  Pratikula: If ≥80% consensus → devil's advocate        │
│  assigned to argue opposing case at maximum strength    │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  POST-DELIBERATION (4 LLM calls)                        │
│                                                          │
│  [5] PRAKRITIS ANALYST                                   │
│      Map stakeholder consequences:                       │
│      Who benefits? Who loses? Who watches?              │
│      Who was not considered but affected?               │
│      Highest-risk stakeholder. Unintended consequence.  │
│                                                          │
│  [6] PRABHU SHAKTI                                       │
│      Is the decision-maker capable of executing this?   │
│      Check Arishadvarga in the recommendation itself:   │
│      Are we recommending to punish (KRODHA)?            │
│      Overextend (LOBHA)? Assume (MOHA)?                 │
│      Score 0.0–1.0. Flag if < 0.5.                     │
│                                                          │
│  [7] UTSAHA SHAKTI                                       │
│      Can the organization actually execute this?        │
│      Critical assumption. Fatal flaw.                   │
│      Minimum viable version.                            │
│      Execution risk 0.0–1.0.                            │
│                                                          │
│  [8] PRE-MORTEM                                          │
│      Assume perfect execution. One year later: failed.  │
│      3 strategic failure scenarios + leading indicators │
│      Blind spot: most confident assumption most         │
│      likely to be wrong                                 │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  SYNTHESIS (1 LLM call)                                  │
│                                                          │
│  [9] SANDHI SYNTHESIS                                    │
│      Define victory before acting:                       │
│      Minimum acceptable / Target / Stop condition       │
│      Type: karyasandhi (goal) / vibhaga (partition) /   │
│            kala (time-bound) / uchchhinna (total)       │
│      Reversibility: irreversible → 0.85 confidence bar  │
│                                                          │
│  REVERSIBILITY GATE:                                     │
│      If avg minister confidence < min_confidence_req →  │
│      sovereign CANNOT recommend action                  │
│      Must recommend: "gather more information first"    │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  SOVEREIGN SPEAK                                         │
│      Receives full structured context:                  │
│      • Bias alerts (Arishadvarga findings)              │
│      • Power position + recommended method              │
│      • Capability scores (Prabhu + Utsaha)             │
│      • Victory definition + stop condition              │
│      • Pre-mortem scenarios + leading indicators        │
│      • Pratikula stress-test counter-arguments          │
│      • Reversibility gate warning if triggered          │
│                                                          │
│      CoT synthesis prefix before speak():               │
│      "Think step by step integrating all of the above. │
│      Then respond to the user."                         │
└─────────────────────────────────────────────────────────┘
    ↓
    Response
    ↓
┌─────────────────────────────────────────────────────────┐
│  OUTCOME TRACKING                                        │
│      Decision logged to data/outcomes/outcomes.jsonl    │
│      Next session: "Did you follow the recommendation?" │
│      "What happened?"                                   │
│      Maps outcome → MinisterConfidenceTracker updates   │
└─────────────────────────────────────────────────────────┘
```

---

## 4. The Arthashastra Concepts Mapped to Code

### 4.1 Arishadvarga (6 Internal Enemies)

Kautilya documented that most strategic failures are caused by the decision-maker's own psychology contaminating the decision — not external enemies.

| Enemy | Sanskrit | Modern Equivalent | Detection Signal |
|-------|----------|------------------|-----------------|
| KAMA | काम | Motivated reasoning | Decision enables what was already wanted |
| KRODHA | क्रोध | Reactive aggression | "Betrayed", "unfair", urgency without cause |
| LOBHA | लोभ | Scope creep / greed | Taking more than the goal requires |
| MOHA | मोह | Wishful thinking | Assumptions presented as facts |
| MADA | मद | Overconfidence | Underestimating opposition capability |
| MATSARYA | मत्सर्य | Competitive spite | "Even if it costs us, they lose more" |

**Implementation:** `persona/analysis.py:detect_arishadvarga(llm, situation)` — runs BEFORE ministers deliberate. High severity → situation is cleaned before being passed to council.

### 4.2 Rajamandala (Circle of Powers)

Kautilya mapped 12 concentric rings of powers around any decision-maker. Key insight: your enemy's enemy is your natural ally.

```
Ari (direct opponent)
  → Mitra (your ally)
    → Ari-Mitra (enemy's ally = also your enemy)
      → Mitra-Mitra (ally's ally)
        → Ari-Ari (enemy's enemy = potential ally)
```

**Implementation:** `persona/analysis.py:analyze_mandala(llm, situation)` — maps power relationships, assesses leverage, recommends posture.

### 4.3 Saptanga (7 Pillars of State) → ERA Ministers

| Pillar | Kautilya's Term | ERA Minister |
|--------|----------------|-------------|
| King's will | Swami | sovereign (Prime Confident) |
| Treasury | Kosha | risk_resources |
| Military | Danda | conflict, war_mode |
| Alliances | Mitra | diplomacy |
| Territory/People | Janapada | legitimacy |
| Defense | Durga | optionality |
| Intelligence | Shatru/Mahamatyapasarpa | intelligence ⚠ (partially missing) |

### 4.4 Upayas (4 Methods of Action)

Real councils classified decisions by METHOD before deliberating on specifics.

```
Sama (conciliation) → Try first — always
  ↓ if fails
Dana (incentivize) → Offer future benefit
  ↓ if fails
Bheda (divide) → Identify fracture lines in opposition
  ↓ if fails or impossible
Danda (force) → Direct confrontation — last resort
```

Kautilya: "A king who jumps to Danda without exhausting the first three is WEAK — he reveals he has no subtlety."

**Implementation:** `persona/analysis.py:classify_upaya(llm, situation, mandala)` — output injected into every minister's prompt.

### 4.5 Sthiti → Vikalpa → Mata (3-Stage Minister Output)

The most critical structural change. Ministers CANNOT collapse observation with opinion.

```
STHITI: "Resource commitment is locked. Deadline is 30 days. Opposition has legal standing."
        (Facts only. No adjectives implying judgment.)

VIKALPA: "V0: Do nothing [INACTION] — cost: deadline passes, resource wasted.
          V1: Full immediate launch [AGGRESSIVE]
          V2: Partial rollout with reserves [DEFENSIVE]
          V3: Pause and reassess in 2 weeks [RETREAT]"
          (All options. Uncomfortable ones included.)

MATA: "Recommend V2. Sthiti fact 3 (legal standing) + doctrine: never commit without cover.
       Minimum acceptable: V3. Confidence: 0.82.
       Knowledge gaps: regulatory timeline unknown."
```

**Why this makes councils lethal:** 80% of strategic arguments are actually about facts disguised as strategy debates. Forcing Sthiti separates what IS from what TO DO.

### 4.6 Pratikula (Devil's Advocate)

Kautilya treated high consensus as a WARNING, not confidence. When ministers agree too easily, they are serving themselves (avoiding the king's displeasure), not the king.

**Trigger:** ≥80% consensus after Round 1
**Mechanism:** Strongest supporter assigned to argue the opposing case at maximum strength. Sovereign sees both the consensus AND the stress-tested counter-argument.

### 4.7 Sandhi Types (Settlement Classifications)

| Type | Sanskrit | When to Use |
|------|----------|------------|
| Karyasandhi | कार्यसन्धि | Goal-achieved peace — stop when objective met |
| Vibhaga | विभाग | Partition — divide the contested resource |
| Kala | काल | Time-bound truce — buy time to regroup |
| Uchchhinna | उच्छिन्न | Total victory or total defeat — high stakes |

Most mistakes: pursuing Uchchhinna when Karyasandhi was achievable and sufficient.

---

## 5. Mode Behavior

| Mode | Arthashastra Stages Active |
|------|--------------------------|
| `quick` | NONE — keyword path, unchanged |
| `war` | NONE — keyword path, unchanged |
| `meeting` | All 9 stages (3 pre + 5 ministers + 4 post) |
| `darbar` | All 9 stages + Round 2 peer challenge + Pratikula |

---

## 6. LLM Call Budget

For `meeting` mode with Arthashastra protocol:

| Stage | Calls | Notes |
|-------|-------|-------|
| Arishadvarga | 1 | Pre-deliberation |
| Mandala | 1 | Pre-deliberation |
| Upaya | 1 | Pre-deliberation |
| 5 ministers × 3 samples | 15 | Self-consistency (Plan A) |
| Prakritis | 1 | Post-deliberation |
| Prabhu Shakti | 1 | Post-deliberation |
| Utsaha Shakti | 1 | Post-deliberation |
| Pre-mortem | 1 | Post-deliberation |
| Sandhi | 1 | Synthesis |
| Speak | 1 | Sovereign |
| **Total** | **24** | vs 5 in current meeting mode |

For `darbar` mode (18 ministers × 3 samples × 2 rounds + Pratikula × 2):
- ~115 calls vs 36 current

Latency trade-off is intentional: ERA is a decision tool, not a chatbot.

---

## 7. Data Flow Changes

### New Context Object Added to Council Result

```python
council_result["arthashastra"] = {
    "arishadvarga": {
        "active_enemies": ["KRODHA"],
        "severity": "medium",
        "corrective_injection": "cleaned situation text",
        "original_situation": "original with emotional framing",
    },
    "mandala": {
        "power_position": "middling",
        "ari": {"name": "...", "strength": 0.7},
        "mitra": [...],
        "recommended_posture": "indirect",
    },
    "upaya": {
        "recommended_upaya": "dana",
        "dana_path": "offer revenue share deal",
        "reason": "incentive most viable",
    },
    "pratikula": {
        "triggered": True,
        "consensus_ratio": 0.87,
        "devil_advocate_output": {...},  # MinisterVoice output
    },
}
```

### New Minister Output Schema

```python
# Before (current)
{
    "stance": "oppose",
    "reasoning": "...",
    "confidence": 0.75,
    "warning": "...",
    "knowledge_cited": "1, 3"
}

# After (Arthashastra protocol)
{
    "sthiti": ["fact 1", "fact 2", "fact 3"],
    "vikalpa": [
        {"id": "V0", "type": "INACTION", "description": "Do nothing. Cost: X"},
        {"id": "V1", "type": "AGGRESSIVE", "description": "..."},
        {"id": "V2", "type": "DEFENSIVE", "description": "..."},
        {"id": "V3", "type": "RETREAT", "description": "..."},
    ],
    "mata": {
        "recommended_vikalpa": "V2",
        "doctrine_reason": "Sthiti fact 2 + doctrine principle",
        "minimum_acceptable": "V3",
        "confidence": 0.82,
        "warning": "...",
        "knowledge_gaps": ["unknown regulatory timeline", "competitor position unclear"],
        "decision_quality": "medium",
    }
}
```

### Outcome Tracking Schema

**File:** `data/outcomes/outcomes.jsonl` (append-only)

```python
{
    "session_id": "session_abc123",
    "situation_hash": "sha256_of_situation_text",
    "recommendation_summary": "Proceed with defensive option V2",
    "minister_votes": {"risk": "V3", "grand_strategist": "V2", ...},
    "outcome_text": "We followed V2. Market share held stable.",
    "followed": true,
    "timestamp": "2026-05-18T15:30:00+00:00"
}
```

---

## 8. Files Changed by This Protocol

| File | Change Type | What Changes |
|------|------------|-------------|
| `persona/analysis.py` | Extend | +10 new functions |
| `persona/council/minister_voice.py` | Rewrite | Prompt + schema + parse + validate |
| `modules/council_execution/engine.py` | Extend | Pre-stages + Pratikula + enriched payload |
| `persona/main.py` | Extend | Post-stages + outcome loop + sovereign context |
| `persona/session_manager.py` | Extend | Pending outcome tracking |
| `data/outcomes/outcomes.jsonl` | New | Append-only outcome log |
| `data/outcomes/pending_decisions.json` | New | Pending outcome requests |

---

## 9. Confidence Penalty System (Plan A Integration)

Ministers who skip structural requirements lose confidence weight cumulatively:

| Missing | Penalty |
|---------|---------|
| `doctrine_reason` < 25 chars | Cap at 0.40 |
| No `knowledge_cited` (when entries available) | × 0.85 |
| No `knowledge_gaps` (when entries available) | × 0.90 |
| No V0 INACTION in Vikalpa | × 0.80 |
| `decision_quality == "defer"` | Blocks sovereign action |

These penalties compound and feed into `MinisterConfidenceTracker` Bayesian weights. Ministers who consistently skip gaps and ignore inaction have progressively lower vote weight.
