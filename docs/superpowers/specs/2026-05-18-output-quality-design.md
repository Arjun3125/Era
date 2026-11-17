# Plan A — Output Quality Enhancement
**Date:** 2026-05-18
**Scope:** Model-agnostic quality improvements to minister deliberation and sovereign synthesis
**Goal:** Ministers reliably produce valid structured JSON with real reasoning; sovereign final answer feels decisive and coherent — independent of which Ollama model is running

---

## Problem

ERA's quality is currently coupled to model capability:
- `_MINISTER_INSTRUCTION` goes straight to JSON with no reasoning scaffold
- Bad JSON falls back to keyword inference silently (confidence=0.5, no citation)
- Model randomness is unmitigated — one call per minister
- Sovereign `speak()` receives a raw council summary with no synthesis guidance

---

## Architecture

```
MinisterVoice.deliberate()
├── _MINISTER_INSTRUCTION  ← CoT scratchpad + few-shot example
├── _deliberate_consistent(n=3)  ← 3 parallel samples via analyze_async()
│   └── majority vote on stance, highest confidence breaks ties
├── _parse_with_retry()  ← 1 retry call on JSON parse failure
└── _validate()  ← confidence calibration (lazy reasoning penalty)

NativePrimeDecider / sovereign
└── CoT synthesis prompt injected before speak() call
```

---

## Components

### 1. Minister Prompt — `persona/council/minister_voice.py`

**Change:** `_MINISTER_INSTRUCTION` constant

Add a two-step structure:
- `STEP 1 — Think:` scratchpad prompting the model to reason before committing
- One static gold few-shot example showing correct JSON output
- Scratchpad text is never parsed — only the JSON block is extracted

```
STEP 1 — Think (do not output this):
- What is the core tension in this situation?
- Which knowledge entries directly apply?
- What would your doctrine demand?

STEP 2 — Output ONLY valid JSON:
{ ... }

EXAMPLE (follow this format exactly):
{
  "stance": "oppose",
  "reasoning": "Entry 2 shows execution risk exceeds reserves. Doctrine demands we never commit without fallback.",
  "confidence": 0.82,
  "warning": "Resource depletion crosses red-line threshold",
  "knowledge_cited": "2, 4"
}
```

### 2. Self-Consistency — `persona/council/minister_voice.py`

**New method:** `_deliberate_consistent(user_input, context, knowledge_entries, n=3)`

- Fires `n` parallel `analyze_async()` futures (uses existing `OllamaRuntime.analyze_async()`)
- Collects results, extracts `stance` from each
- Majority vote determines winning stance; ties broken by highest `confidence`
- Returns the winning result object

**Called from:** Council execution engine instead of `deliberate()` directly

**n=3** is the default; configurable via `MINISTER_CONSISTENCY_SAMPLES` env var.

### 3. Structured Retry — `persona/council/minister_voice.py`

**Change:** `_parse()` method

On fallback to keyword inference (indicator: `confidence == 0.5` and `knowledge_cited == ""`):
- Fire one correction call: `"Your output was not valid JSON. Output ONLY the JSON object, no explanation, no markdown fences."`
- Parse result; if still fails, keep keyword fallback
- Max 1 retry — no loop

### 4. Confidence Calibration — `persona/council/minister_voice.py`

**Change:** `_validate()` static method

Post-parse penalties (applied in order, cumulative):
- `len(doctrine_reason) < 25` → cap confidence at `0.4` (lazy/empty reasoning)
- `knowledge_cited == ""` and knowledge entries were available → `confidence *= 0.85`
- `knowledge_gaps == []` and knowledge entries were available → `confidence *= 0.90` (minister who doesn't flag any gaps is overconfident)
- `vikalpa` has no INACTION/V0 option → `confidence *= 0.80` (minister who ignores inaction is biased toward action)
- `decision_quality == "defer"` → sovereign is blocked from action recommendation regardless of confidence

These penalties flow into `MinisterConfidenceTracker` Bayesian weights, compounding over time. A minister who consistently skips gaps and ignores inaction will have progressively lower weight in votes.

### 5. Sovereign CoT Synthesis

**Change:** Prime decision engine or sovereign speak call site

Before `speak()`, prepend structured council summary:
```
Council voted: {support} support, {oppose} oppose, {neutral} neutral (of {total}).
Avg confidence: {avg_confidence:.2f}
Key warnings raised: {warnings_list}

Think step by step about the final recommendation, then respond to the user.
```

This gives even weak `speak_model` a structured scaffold to synthesize rather than hallucinate.

---

## Files Changed

| File | Change |
|------|--------|
| `persona/council/minister_voice.py` | Prompt rewrite, `_deliberate_consistent()`, `_parse_with_retry()`, `_validate()` calibration |
| `modules/council_execution/engine.py` (meeting/darbar paths) | Call `_deliberate_consistent()` instead of `deliberate()` |
| `persona/main.py:582` — `build_system_context()` result | Append CoT synthesis prefix to `system_context` before `speak()` call |

---

## Non-Goals

- No changes to `OllamaRuntime` (analyze_async already exists)
- No changes to ingestion, embeddings, or knowledge retrieval (Plan B)
- No changes to minister YAML doctrines
- No new dependencies

---

## Success Criteria

- Minister JSON parse failure rate drops to <5% on llama3.1:8b
- Reasoning field consistently ≥25 chars with knowledge citations
- Sovereign response references minister stances and specific warnings
- No regression in quick-mode (keyword-only path bypasses all of the above)
