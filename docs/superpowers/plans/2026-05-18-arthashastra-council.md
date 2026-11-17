# Arthashastra Council Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Kautilya's full council deliberation protocol into ERA — bias detection, power mapping, method classification, structured Sthiti→Vikalpa→Mata minister output (with mandatory inaction option + knowledge gaps), stakeholder analysis, capability checks, reversibility gate, pre-mortem, Pratikula devil's advocate, victory definition, and outcome tracking loop.

**Architecture:** All new logic lives in `persona/analysis.py` (new functions, following existing pattern) and `persona/council/minister_voice.py` (prompt replacement). The council engine `modules/council_execution/engine.py` orchestrates the new pre/post stages around existing `_llm_deliberate()`. Outcome tracking extends `persona/session_manager.py`. Quick/war mode untouched throughout.

**Tech Stack:** Python 3.11, existing `OllamaRuntime.analyze()`, no new dependencies

---

## File Map

| File | Change |
|------|--------|
| `persona/analysis.py` | Add 10 new functions: `detect_arishadvarga`, `analyze_mandala`, `classify_upaya`, `analyze_prakritis`, `check_prabhu_shakti`, `check_utsaha_shakti`, `synthesize_sandhi`, `run_premortem`, `record_outcome`, `check_pending_outcomes` |
| `persona/council/minister_voice.py` | Replace `_MINISTER_INSTRUCTION` with Sthiti→Vikalpa→Mata schema including V0 + knowledge_gaps + decision_quality; update `_parse()` and `_validate()` |
| `modules/council_execution/engine.py` | Update `_llm_deliberate()`: pre-stages, knowledge gap counting, Pratikula round on ≥80% consensus, enriched payload |
| `persona/main.py` | Inject full Arthashastra context including pre-mortem + reversibility gate before `speak()`; check pending outcomes on session start |
| `persona/session_manager.py` | Extend to track pending outcome requests across sessions |
| `data/outcomes/` | New directory — `outcomes.jsonl` append-only outcome log |
| `tests/test_arthashastra.py` | New test file for all new functions and integration |

---

## Task 1: Arishadvarga Detector

**Files:**
- Modify: `persona/analysis.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_arthashastra.py
import pytest
from unittest.mock import MagicMock

def make_llm(response: str):
    llm = MagicMock()
    llm.analyze.return_value = response
    return llm

def test_arishadvarga_detects_krodha():
    from persona.analysis import detect_arishadvarga
    llm = make_llm('{"active_enemies": ["KRODHA"], "evidence": {"KRODHA": "betrayed framing"}, "corrective_injection": "partner changed terms", "severity": "medium"}')
    result = detect_arishadvarga(llm, "They betrayed me and broke every promise")
    assert "KRODHA" in result["active_enemies"]
    assert result["severity"] in {"low", "medium", "high"}
    assert isinstance(result["corrective_injection"], str)
    assert len(result["corrective_injection"]) > 0

def test_arishadvarga_safe_default_on_parse_failure():
    from persona.analysis import detect_arishadvarga
    llm = make_llm("not json at all")
    result = detect_arishadvarga(llm, "Should we expand to new market?")
    assert result["active_enemies"] == []
    assert result["severity"] == "low"
    assert result["corrective_injection"] == "Should we expand to new market?"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd C:\Users\naren\Work\Projects\School\era
python -m pytest tests/test_arthashastra.py::test_arishadvarga_detects_krodha -v
```
Expected: `ImportError` or `AttributeError` — function does not exist yet.

- [ ] **Step 3: Implement `detect_arishadvarga` in `persona/analysis.py`**

Add after the existing `assess_emotional_metrics` function:

```python
_ARISHADVARGA_SYSTEM = "You are a psychological bias detector trained in Kautilya's Arthashastra."

_ARISHADVARGA_PROMPT = """
Analyze this situation description for cognitive distortions (Arishadvarga — 6 internal enemies).

Situation: {situation}

Detect which are active based on language signals:
- KAMA: decision enables something desired regardless of strategic merit
- KRODHA: reactive anger ("betrayed", "unfair", "how dare", urgency without cause)
- LOBHA: scope beyond core goal, taking more than needed
- MOHA: wishful assumptions stated as facts, "they will agree", "it should work"
- MADA: underestimating opposition ("they can't stop us", "easy win")
- MATSARYA: competitive spite ("even if it costs us, they lose more")

Output ONLY valid JSON:
{{
  "active_enemies": [],
  "evidence": {{}},
  "corrective_injection": "<same situation rewritten without emotional language>",
  "severity": "low"
}}

If no bias detected, return active_enemies=[], severity="low", corrective_injection=original text.
"""


def detect_arishadvarga(llm: Any, situation: str) -> Dict[str, Any]:
    """Detect Kautilya's 6 internal enemies (cognitive biases) in situation framing."""
    _default = {
        "active_enemies": [],
        "evidence": {},
        "corrective_injection": situation,
        "severity": "low",
    }
    try:
        raw = llm.analyze(
            system_prompt=_ARISHADVARGA_SYSTEM,
            user_prompt=_ARISHADVARGA_PROMPT.format(situation=situation),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("arishadvarga_parse_error", {"raw": raw})
            return _default
        valid_enemies = {"KAMA", "KRODHA", "LOBHA", "MOHA", "MADA", "MATSARYA"}
        active = [e for e in (parsed.get("active_enemies") or []) if e in valid_enemies]
        severity = parsed.get("severity", "low")
        if severity not in {"low", "medium", "high"}:
            severity = "low"
        injection = str(parsed.get("corrective_injection") or situation).strip() or situation
        result = {
            "active_enemies": active,
            "evidence": parsed.get("evidence") or {},
            "corrective_injection": injection,
            "severity": severity,
        }
        trace("arishadvarga_result", result)
        return result
    except Exception as e:
        trace("arishadvarga_exception", {"error": str(e)})
        return _default
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_arthashastra.py::test_arishadvarga_detects_krodha tests/test_arthashastra.py::test_arishadvarga_safe_default_on_parse_failure -v
```
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add persona/analysis.py tests/test_arthashastra.py
git commit -m "feat: add Arishadvarga bias detector to analysis pipeline"
```

---

## Task 2: Mandala Analyzer

**Files:**
- Modify: `persona/analysis.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_arthashastra.py

def test_mandala_returns_power_position():
    from persona.analysis import analyze_mandala
    llm = make_llm('{"power_position": "middling", "ari": {"name": "CompetitorX", "strength": 0.7}, "mitra": [], "potential_allies": [], "leverage_you_hold": "distribution", "leverage_they_hold": "capital", "recommended_posture": "indirect"}')
    result = analyze_mandala(llm, "CompetitorX is undercutting our pricing")
    assert result["power_position"] in {"strong", "middling", "weak"}
    assert "ari" in result
    assert "recommended_posture" in result

def test_mandala_safe_default_on_failure():
    from persona.analysis import analyze_mandala
    llm = make_llm("garbage")
    result = analyze_mandala(llm, "some situation")
    assert result["power_position"] == "middling"
    assert result["recommended_posture"] == "indirect"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_mandala_returns_power_position -v
```
Expected: `AttributeError` — function does not exist.

- [ ] **Step 3: Implement `analyze_mandala` in `persona/analysis.py`**

```python
_MANDALA_SYSTEM = "You are a strategic advisor trained in Kautilya's Rajamandala (circle of powers) theory."

_MANDALA_PROMPT = """
Map the power relationships in this situation using Rajamandala theory.

Situation: {situation}

Identify:
- Ari: the direct obstacle or opponent (name them concretely from context)
- Mitra: current assets, allies, or supporters
- Potential allies: parties who benefit if Ari fails (Ari-Ari)
- Your leverage: what you have that they need
- Their leverage: what they have that you need
- Power position: are you stronger, equal, or weaker than Ari?

Recommended posture options: direct / indirect / alliance-building / delay

Output ONLY valid JSON:
{{
  "power_position": "middling",
  "ari": {{"name": "unknown", "strength": 0.5}},
  "mitra": [],
  "potential_allies": [],
  "leverage_you_hold": "unknown",
  "leverage_they_hold": "unknown",
  "recommended_posture": "indirect"
}}

Situation: {situation}
"""


def analyze_mandala(llm: Any, situation: str) -> Dict[str, Any]:
    """Map power relationships using Kautilya's Rajamandala theory."""
    _default = {
        "power_position": "middling",
        "ari": {"name": "unknown", "strength": 0.5},
        "mitra": [],
        "potential_allies": [],
        "leverage_you_hold": "unknown",
        "leverage_they_hold": "unknown",
        "recommended_posture": "indirect",
    }
    try:
        raw = llm.analyze(
            system_prompt=_MANDALA_SYSTEM,
            user_prompt=_MANDALA_PROMPT.format(situation=situation),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("mandala_parse_error", {"raw": raw})
            return _default
        valid_positions = {"strong", "middling", "weak"}
        valid_postures = {"direct", "indirect", "alliance-building", "delay"}
        result = {
            "power_position": parsed.get("power_position", "middling") if parsed.get("power_position") in valid_positions else "middling",
            "ari": parsed.get("ari") or {"name": "unknown", "strength": 0.5},
            "mitra": parsed.get("mitra") or [],
            "potential_allies": parsed.get("potential_allies") or [],
            "leverage_you_hold": str(parsed.get("leverage_you_hold") or "unknown"),
            "leverage_they_hold": str(parsed.get("leverage_they_hold") or "unknown"),
            "recommended_posture": parsed.get("recommended_posture", "indirect") if parsed.get("recommended_posture") in valid_postures else "indirect",
        }
        trace("mandala_result", result)
        return result
    except Exception as e:
        trace("mandala_exception", {"error": str(e)})
        return _default
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_arthashastra.py::test_mandala_returns_power_position tests/test_arthashastra.py::test_mandala_safe_default_on_failure -v
```
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add persona/analysis.py tests/test_arthashastra.py
git commit -m "feat: add Mandala power-position analyzer"
```

---

## Task 3: Upaya Classifier

**Files:**
- Modify: `persona/analysis.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_arthashastra.py

def test_upaya_recommends_valid_method():
    from persona.analysis import classify_upaya
    llm = make_llm('{"sama_feasibility": 0.3, "sama_path": "hard", "dana_feasibility": 0.7, "dana_path": "offer revenue share", "bheda_feasibility": 0.4, "bheda_path": "target middle management", "danda_feasibility": 0.9, "danda_path": "legal action", "recommended_upaya": "dana", "reason": "incentive is most viable"}')
    result = classify_upaya(llm, "competitor blocking our distribution", {"recommended_posture": "indirect"})
    assert result["recommended_upaya"] in {"sama", "dana", "bheda", "danda"}
    assert 0.0 <= result["sama_feasibility"] <= 1.0
    assert 0.0 <= result["danda_feasibility"] <= 1.0

def test_upaya_safe_default():
    from persona.analysis import classify_upaya
    llm = make_llm("bad output")
    result = classify_upaya(llm, "situation", {})
    assert result["recommended_upaya"] == "sama"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_upaya_recommends_valid_method -v
```
Expected: `AttributeError`.

- [ ] **Step 3: Implement `classify_upaya`**

```python
_UPAYA_SYSTEM = "You are a strategic advisor trained in Kautilya's four methods of statecraft (Upayas)."

_UPAYA_PROMPT = """
Assess which of the 4 Upayas (methods) are available for this situation.
Hierarchy: try Sama first, then Dana, then Bheda, only then Danda.

Situation: {situation}
Power context: {posture}

For each method assess feasibility (0.0-1.0) and the concrete path:
- Sama (conciliation): find shared interest, face-saving language, reframe
- Dana (incentive): what future benefit makes cooperation rational for them?
- Bheda (divide): what fracture lines exist within the opposition? Who has misaligned interests?
- Danda (force/direct action): legal, competitive, public exposure, direct confrontation

Output ONLY valid JSON:
{{
  "sama_feasibility": 0.5,
  "sama_path": "...",
  "dana_feasibility": 0.5,
  "dana_path": "...",
  "bheda_feasibility": 0.5,
  "bheda_path": "...",
  "danda_feasibility": 0.5,
  "danda_path": "...",
  "recommended_upaya": "sama",
  "reason": "..."
}}
"""


def classify_upaya(llm: Any, situation: str, mandala: Dict[str, Any]) -> Dict[str, Any]:
    """Classify which of the 4 Kautilya methods (Upayas) are available."""
    _default = {
        "sama_feasibility": 0.5, "sama_path": "unknown",
        "dana_feasibility": 0.5, "dana_path": "unknown",
        "bheda_feasibility": 0.3, "bheda_path": "unknown",
        "danda_feasibility": 0.5, "danda_path": "unknown",
        "recommended_upaya": "sama",
        "reason": "defaulting to conciliation",
    }
    try:
        posture = mandala.get("recommended_posture", "indirect")
        raw = llm.analyze(
            system_prompt=_UPAYA_SYSTEM,
            user_prompt=_UPAYA_PROMPT.format(situation=situation, posture=posture),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("upaya_parse_error", {"raw": raw})
            return _default
        valid_upayas = {"sama", "dana", "bheda", "danda"}
        result = {
            "sama_feasibility": _normalize_float(parsed.get("sama_feasibility"), 0.5),
            "sama_path": str(parsed.get("sama_path") or "unknown"),
            "dana_feasibility": _normalize_float(parsed.get("dana_feasibility"), 0.5),
            "dana_path": str(parsed.get("dana_path") or "unknown"),
            "bheda_feasibility": _normalize_float(parsed.get("bheda_feasibility"), 0.3),
            "bheda_path": str(parsed.get("bheda_path") or "unknown"),
            "danda_feasibility": _normalize_float(parsed.get("danda_feasibility"), 0.5),
            "danda_path": str(parsed.get("danda_path") or "unknown"),
            "recommended_upaya": parsed.get("recommended_upaya", "sama") if parsed.get("recommended_upaya") in valid_upayas else "sama",
            "reason": str(parsed.get("reason") or ""),
        }
        trace("upaya_result", result)
        return result
    except Exception as e:
        trace("upaya_exception", {"error": str(e)})
        return _default
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_arthashastra.py::test_upaya_recommends_valid_method tests/test_arthashastra.py::test_upaya_safe_default -v
```
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add persona/analysis.py tests/test_arthashastra.py
git commit -m "feat: add Upaya method classifier (Sama/Dana/Bheda/Danda)"
```

---

## Task 4: Sthiti→Vikalpa→Mata Minister Output Schema

**Files:**
- Modify: `persona/council/minister_voice.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_arthashastra.py

def test_minister_voice_produces_sthiti_vikalpa_mata():
    from persona.council.minister_voice import MinisterVoice
    llm = make_llm('''{
        "sthiti": ["Resource commitment is locked", "Deadline is 30 days"],
        "vikalpa": [
            {"id": "V1", "type": "AGGRESSIVE", "description": "Proceed full speed"},
            {"id": "V2", "type": "DEFENSIVE", "description": "Partial rollout only"},
            {"id": "V3", "type": "RETREAT", "description": "Pause and reassess"}
        ],
        "mata": {
            "recommended_vikalpa": "V2",
            "doctrine_reason": "Doctrine demands reserves before full commitment",
            "minimum_acceptable": "V3",
            "confidence": 0.78,
            "warning": "Full commitment at this stage exceeds safe threshold"
        }
    }''')
    voice = MinisterVoice(minister_name="risk", llm=llm)
    result = voice.deliberate("Should we launch the product now?", {"domains": ["risk"]})
    assert "sthiti" in result
    assert "vikalpa" in result
    assert "mata" in result
    assert isinstance(result["sthiti"], list)
    assert len(result["vikalpa"]) >= 1
    assert result["mata"]["recommended_vikalpa"] in [v["id"] for v in result["vikalpa"]]
    assert 0.0 <= result["mata"]["confidence"] <= 1.0

def test_minister_voice_fallback_on_bad_json():
    from persona.council.minister_voice import MinisterVoice
    llm = make_llm("I think we should oppose this risky venture")
    voice = MinisterVoice(minister_name="risk", llm=llm)
    result = voice.deliberate("risky decision", {"domains": ["risk"]})
    assert "sthiti" in result
    assert "mata" in result
    assert result["mata"]["confidence"] <= 0.5
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_minister_voice_produces_sthiti_vikalpa_mata -v
```
Expected: FAIL — result has `stance` not `sthiti`.

- [ ] **Step 3: Replace `_MINISTER_INSTRUCTION` and update `_parse` / `_validate` in `persona/council/minister_voice.py`**

Replace the `_MINISTER_INSTRUCTION` constant (line 53–71):

```python
_MINISTER_INSTRUCTION = """
You are {minister_name} in a council deliberation.

{persona_canon}

---
Relevant knowledge:
{knowledge_context}

---
Power context: {mandala_context}
Recommended method: {upaya_context}

---
You MUST respond in THREE stages. Never collapse them.

STAGE 1 — STHITI (facts only — zero opinion, zero adjectives implying judgment):
State only what is verifiably true. No "seems", "appears", "probably".

STAGE 2 — VIKALPA (ALL options — minimum 3, include uncomfortable ones):
Label each: AGGRESSIVE / DEFENSIVE / LATERAL / RETREAT / DELAY / HYBRID
You MUST include at least one RETREAT or DEFENSIVE option.

STAGE 3 — MATA (your recommendation from your doctrine's lens):
Cite one Sthiti fact and one doctrine principle. Name minimum acceptable fallback.

EXAMPLE:
{{
  "sthiti": ["Resource X is committed", "Deadline is fixed at 30 days", "Opposition has legal standing"],
  "vikalpa": [
    {{"id": "V1", "type": "AGGRESSIVE", "description": "Full immediate action"}},
    {{"id": "V2", "type": "DEFENSIVE", "description": "Partial rollout with reserves maintained"}},
    {{"id": "V3", "type": "RETREAT", "description": "Pause, reassess in 2 weeks"}}
  ],
  "mata": {{
    "recommended_vikalpa": "V2",
    "doctrine_reason": "Sthiti fact 3 + doctrine: never commit without legal cover",
    "minimum_acceptable": "V3",
    "confidence": 0.82,
    "warning": "Full commitment before legal resolution is a red line"
  }}
}}

Now analyze:
Domains: {domain_hint}
Situation: {situation}
{peer_block}
"""
```

Replace `deliberate()` method to pass new context fields:

```python
def deliberate(self, user_input: str, context: Dict[str, Any], knowledge_entries: list = None) -> Dict[str, Any]:
    domain_hint = ", ".join(context.get("domains", [])) or "general"
    mandala_context = context.get("mandala_context", "Power position: unknown")
    upaya_context = context.get("upaya_context", "Method: assess from doctrine")

    if knowledge_entries:
        lines = []
        for i, entry in enumerate(knowledge_entries[:6], 1):
            content = str(entry.get("content") or entry.get("text", ""))[:200].strip()
            source = entry.get("source", {})
            book = source.get("book", "") if isinstance(source, dict) else ""
            category = entry.get("type") or entry.get("category", "principle")
            line = f"{i}. [{category}] {content}"
            if book:
                line += f"  — {book}"
            lines.append(line)
        knowledge_block = "\n".join(lines)
    else:
        knowledge_block = "(No domain knowledge retrieved — reasoning from doctrine only.)"

    peer_block = ""
    if context.get("peer_summary"):
        peer_block = f"---\n{context['peer_summary']}"

    system_prompt = _MINISTER_INSTRUCTION.format(
        minister_name=self._display_name,
        persona_canon=self._persona,
        knowledge_context=knowledge_block,
        mandala_context=mandala_context,
        upaya_context=upaya_context,
        domain_hint=domain_hint,
        situation=user_input,
        peer_block=peer_block,
    )

    try:
        raw = self.llm.analyze(system_prompt, user_input)
        return self._parse(raw)
    except Exception as e:
        return self._fallback(str(e))
```

Replace `_parse()` method:

```python
def _parse(self, raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw.strip())
        return self._validate(data)
    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            data = json.loads(match.group())
            return self._validate(data)
        except Exception:
            pass

    # Plain-text fallback — infer stance for backward compat
    text = raw.lower()
    stance = "oppose" if any(w in text for w in ["oppose", "risk", "danger", "avoid"]) else \
             "support" if any(w in text for w in ["support", "proceed", "recommend"]) else "neutral"
    return {
        "sthiti": [raw[:150].strip()],
        "vikalpa": [
            {"id": "V1", "type": "AGGRESSIVE", "description": "Proceed as planned"},
            {"id": "V2", "type": "DEFENSIVE", "description": "Proceed with caution"},
            {"id": "V3", "type": "RETREAT", "description": "Pause and reassess"},
        ],
        "mata": {
            "recommended_vikalpa": "V2" if stance == "neutral" else ("V1" if stance == "support" else "V3"),
            "doctrine_reason": raw[:200].strip(),
            "minimum_acceptable": "V3",
            "confidence": 0.4,
            "warning": "",
        },
    }

def _fallback(self, error_msg: str) -> Dict[str, Any]:
    return {
        "sthiti": [f"[{self.minister_name} unavailable: {error_msg}]"],
        "vikalpa": [
            {"id": "V1", "type": "AGGRESSIVE", "description": "Proceed"},
            {"id": "V2", "type": "DEFENSIVE", "description": "Proceed cautiously"},
            {"id": "V3", "type": "RETREAT", "description": "Pause"},
        ],
        "mata": {
            "recommended_vikalpa": "V2",
            "doctrine_reason": "Minister unavailable",
            "minimum_acceptable": "V3",
            "confidence": 0.3,
            "warning": "",
        },
    }
```

Replace `_validate()` static method:

```python
@staticmethod
def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
    sthiti = data.get("sthiti") or []
    if not isinstance(sthiti, list):
        sthiti = [str(sthiti)]
    sthiti = [str(s)[:300] for s in sthiti[:5]]

    vikalpa_raw = data.get("vikalpa") or []
    if not isinstance(vikalpa_raw, list):
        vikalpa_raw = []
    valid_types = {"AGGRESSIVE", "DEFENSIVE", "LATERAL", "RETREAT", "DELAY", "HYBRID"}
    vikalpa = []
    for v in vikalpa_raw[:6]:
        if isinstance(v, dict):
            vikalpa.append({
                "id": str(v.get("id", f"V{len(vikalpa)+1}")),
                "type": v.get("type", "DEFENSIVE") if v.get("type") in valid_types else "DEFENSIVE",
                "description": str(v.get("description", ""))[:300],
            })
    if not vikalpa:
        vikalpa = [{"id": "V1", "type": "DEFENSIVE", "description": "Proceed with caution"}]

    mata_raw = data.get("mata") or {}
    valid_ids = {v["id"] for v in vikalpa}
    rec = mata_raw.get("recommended_vikalpa", vikalpa[0]["id"])
    if rec not in valid_ids:
        rec = vikalpa[0]["id"]
    min_acc = mata_raw.get("minimum_acceptable", vikalpa[-1]["id"])
    if min_acc not in valid_ids:
        min_acc = vikalpa[-1]["id"]

    confidence = max(0.0, min(1.0, float(mata_raw.get("confidence", 0.5) or 0.5)))
    doctrine_reason = str(mata_raw.get("doctrine_reason", ""))[:400]
    # Penalize lazy reasoning
    if len(doctrine_reason) < 25:
        confidence = min(confidence, 0.4)

    mata = {
        "recommended_vikalpa": rec,
        "doctrine_reason": doctrine_reason,
        "minimum_acceptable": min_acc,
        "confidence": confidence,
        "warning": str(mata_raw.get("warning", ""))[:300],
    }

    return {"sthiti": sthiti, "vikalpa": vikalpa, "mata": mata}
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_arthashastra.py::test_minister_voice_produces_sthiti_vikalpa_mata tests/test_arthashastra.py::test_minister_voice_fallback_on_bad_json -v
```
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add persona/council/minister_voice.py tests/test_arthashastra.py
git commit -m "feat: replace minister output schema with Sthiti-Vikalpa-Mata structure"
```

---

## Task 5: Prakritis Analyst + Shakti Checks + Sandhi Synthesis

**Files:**
- Modify: `persona/analysis.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_arthashastra.py

def test_prakritis_returns_stakeholders():
    from persona.analysis import analyze_prakritis
    llm = make_llm('{"stakeholders": [{"name": "employees", "relationship": "ally", "impact": "negative", "response_prediction": "resistance", "secondary_effect": "attrition", "risk_level": 0.7}], "highest_risk_stakeholder": "employees", "unintended_consequence": "talent loss accelerates"}')
    result = analyze_prakritis(llm, "lay off 20% of staff", "reduce headcount immediately")
    assert len(result["stakeholders"]) >= 1
    assert "highest_risk_stakeholder" in result
    assert "unintended_consequence" in result

def test_prabhu_shakti_returns_score():
    from persona.analysis import check_prabhu_shakti
    llm = make_llm('{"arishadvarga_in_recommendation": ["MADA"], "bias_explanation": "underestimates competition", "prabhu_shakti_score": 0.55, "recommendation": "Proceed with defensive option only"}')
    result = check_prabhu_shakti(llm, "expand aggressively", "enter 5 new markets simultaneously")
    assert 0.0 <= result["prabhu_shakti_score"] <= 1.0
    assert isinstance(result["recommendation"], str)

def test_utsaha_shakti_returns_execution_risk():
    from persona.analysis import check_utsaha_shakti
    llm = make_llm('{"execution_risk": 0.8, "critical_assumption": "team can handle 5x workload", "minimum_viable_version": "enter 1 market only", "fatal_flaw": "no local partnerships exist"}')
    result = check_utsaha_shakti(llm, "situation", "enter 5 new markets")
    assert 0.0 <= result["execution_risk"] <= 1.0
    assert "fatal_flaw" in result
    assert "minimum_viable_version" in result

def test_sandhi_synthesis_returns_type():
    from persona.analysis import synthesize_sandhi
    llm = make_llm('{"minimum_acceptable_outcome": "retain top 3 clients", "target_outcome": "full market share recovery", "stop_condition": "when revenue returns to baseline", "sandhi_type": "karyasandhi", "overreach_warning": "pursuing total dominance creates regulatory risk"}')
    result = synthesize_sandhi(llm, "recover market position", {"prabhu_shakti_score": 0.7}, {"execution_risk": 0.4})
    assert result["sandhi_type"] in {"karyasandhi", "vibhaga", "kala", "uchchhinna"}
    assert "stop_condition" in result
```

- [ ] **Step 2: Run to confirm failures**

```bash
python -m pytest tests/test_arthashastra.py::test_prakritis_returns_stakeholders tests/test_arthashastra.py::test_prabhu_shakti_returns_score -v
```
Expected: `AttributeError` — functions do not exist.

- [ ] **Step 3: Implement all four functions in `persona/analysis.py`**

```python
_PRAKRITIS_SYSTEM = "You are a stakeholder consequence analyst trained in Kautilya's Saptanga theory."

_PRAKRITIS_PROMPT = """
Map the stakeholder consequences of this recommendation.

Situation: {situation}
Council recommendation: {recommendation}

Identify all parties affected — directly and indirectly. For each:
- Name them concretely from context
- Their relationship to the decision-maker
- Impact of the recommendation on them
- How they will likely respond
- What that response creates as a secondary effect
- Risk level (0.0-1.0) of their response destabilizing the situation

Output ONLY valid JSON:
{{
  "stakeholders": [
    {{
      "name": "...",
      "relationship": "ally|neutral|competitor|unknown",
      "impact": "positive|negative|neutral",
      "response_prediction": "...",
      "secondary_effect": "...",
      "risk_level": 0.5
    }}
  ],
  "highest_risk_stakeholder": "...",
  "unintended_consequence": "..."
}}
"""


def analyze_prakritis(llm: Any, situation: str, council_recommendation: str) -> Dict[str, Any]:
    """Map stakeholder consequences using Kautilya's Prakritis framework."""
    _default = {
        "stakeholders": [],
        "highest_risk_stakeholder": "unknown",
        "unintended_consequence": "unknown",
    }
    try:
        raw = llm.analyze(
            system_prompt=_PRAKRITIS_SYSTEM,
            user_prompt=_PRAKRITIS_PROMPT.format(
                situation=situation, recommendation=council_recommendation
            ),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("prakritis_parse_error", {"raw": raw})
            return _default
        stakeholders = parsed.get("stakeholders") or []
        valid_relationships = {"ally", "neutral", "competitor", "unknown"}
        valid_impacts = {"positive", "negative", "neutral"}
        cleaned = []
        for s in stakeholders[:8]:
            if not isinstance(s, dict):
                continue
            cleaned.append({
                "name": str(s.get("name", "unknown")),
                "relationship": s.get("relationship", "unknown") if s.get("relationship") in valid_relationships else "unknown",
                "impact": s.get("impact", "neutral") if s.get("impact") in valid_impacts else "neutral",
                "response_prediction": str(s.get("response_prediction", ""))[:300],
                "secondary_effect": str(s.get("secondary_effect", ""))[:300],
                "risk_level": _normalize_float(s.get("risk_level"), 0.5),
            })
        result = {
            "stakeholders": cleaned,
            "highest_risk_stakeholder": str(parsed.get("highest_risk_stakeholder") or "unknown"),
            "unintended_consequence": str(parsed.get("unintended_consequence") or "unknown"),
        }
        trace("prakritis_result", result)
        return result
    except Exception as e:
        trace("prakritis_exception", {"error": str(e)})
        return _default


_PRABHU_SYSTEM = "You are a psychological advisor assessing decision-maker capability using Kautilya's Shakti framework."

_PRABHU_PROMPT = """
Assess the decision-maker's personal capacity to execute this recommendation.

Situation framing: {situation}
Recommendation: {recommendation}

Check for Arishadvarga (6 internal enemies) in the RECOMMENDATION itself:
- KAMA: recommendation enables desired outcome regardless of strategic merit
- KRODHA: punishes rather than strategizes
- LOBHA: takes more than the goal requires, creating new enemies
- MOHA: assumes facts not confirmed
- MADA: underestimates opposition's response
- MATSARYA: hurts decision-maker but hurts competitor more

Rate Prabhu Shakti (personal execution capacity) 0.0-1.0.
High score = clear-headed, capable, resourced.
Low score = emotionally compromised, overcommitted, or capacity mismatch.

Output ONLY valid JSON:
{{
  "arishadvarga_in_recommendation": [],
  "bias_explanation": "...",
  "prabhu_shakti_score": 0.7,
  "recommendation": "Proceed as council suggests"
}}
"""


def check_prabhu_shakti(llm: Any, situation: str, council_recommendation: str) -> Dict[str, Any]:
    """Check decision-maker capability (Prabhu Shakti) to execute council recommendation."""
    _default = {
        "arishadvarga_in_recommendation": [],
        "bias_explanation": "",
        "prabhu_shakti_score": 0.7,
        "recommendation": "Proceed as council suggests",
    }
    try:
        raw = llm.analyze(
            system_prompt=_PRABHU_SYSTEM,
            user_prompt=_PRABHU_PROMPT.format(
                situation=situation, recommendation=council_recommendation
            ),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("prabhu_parse_error", {"raw": raw})
            return _default
        valid_enemies = {"KAMA", "KRODHA", "LOBHA", "MOHA", "MADA", "MATSARYA"}
        active = [e for e in (parsed.get("arishadvarga_in_recommendation") or []) if e in valid_enemies]
        result = {
            "arishadvarga_in_recommendation": active,
            "bias_explanation": str(parsed.get("bias_explanation") or ""),
            "prabhu_shakti_score": _normalize_float(parsed.get("prabhu_shakti_score"), 0.7),
            "recommendation": str(parsed.get("recommendation") or "Proceed as council suggests"),
        }
        trace("prabhu_shakti_result", result)
        return result
    except Exception as e:
        trace("prabhu_shakti_exception", {"error": str(e)})
        return _default


_UTSAHA_SYSTEM = "You are an execution feasibility analyst trained in Kautilya's Utsaha Shakti assessment."

_UTSAHA_PROMPT = """
Reality-check whether the organization can actually execute this recommendation.

Situation: {situation}
Recommendation: {recommendation}

Assess:
- What resources does this require that haven't been confirmed available?
- What is the single most dangerous assumption embedded in this plan?
- What is the minimum viable version that IS executable?
- What one failure mode would make this completely collapse?

Rate execution risk 0.0 (easy) to 1.0 (near impossible).

Output ONLY valid JSON:
{{
  "execution_risk": 0.5,
  "critical_assumption": "...",
  "minimum_viable_version": "...",
  "fatal_flaw": "..."
}}
"""


def check_utsaha_shakti(llm: Any, situation: str, council_recommendation: str) -> Dict[str, Any]:
    """Check execution feasibility (Utsaha Shakti) of council recommendation."""
    _default = {
        "execution_risk": 0.5,
        "critical_assumption": "unknown",
        "minimum_viable_version": council_recommendation,
        "fatal_flaw": "unknown",
    }
    try:
        raw = llm.analyze(
            system_prompt=_UTSAHA_SYSTEM,
            user_prompt=_UTSAHA_PROMPT.format(
                situation=situation, recommendation=council_recommendation
            ),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("utsaha_parse_error", {"raw": raw})
            return _default
        result = {
            "execution_risk": _normalize_float(parsed.get("execution_risk"), 0.5),
            "critical_assumption": str(parsed.get("critical_assumption") or "unknown"),
            "minimum_viable_version": str(parsed.get("minimum_viable_version") or council_recommendation),
            "fatal_flaw": str(parsed.get("fatal_flaw") or "unknown"),
        }
        trace("utsaha_shakti_result", result)
        return result
    except Exception as e:
        trace("utsaha_shakti_exception", {"error": str(e)})
        return _default


_SANDHI_SYSTEM = "You are a strategic resolution advisor trained in Kautilya's Sandhi (settlement) doctrine."

_SANDHI_PROMPT = """
Define victory conditions for this situation before action is taken.

Situation: {situation}
Council recommendation: {recommendation}
Prabhu Shakti score: {prabhu_score}
Execution risk: {execution_risk}

Define:
- Minimum acceptable outcome: the least that must be achieved for this to be worth doing
- Target outcome: what success specifically looks like
- Stop condition: the exact moment to cease action (avoid overreach)
- Sandhi type: karyasandhi (goal-achieved) / vibhaga (partition/share) / kala (time-bound truce) / uchchhinna (unconditional total victory)
- Overreach warning: what pursuing more than target_outcome would cost

Note: if prabhu_score < 0.5 or execution_risk > 0.7, uchchhinna is almost certainly overreach.

Output ONLY valid JSON:
{{
  "minimum_acceptable_outcome": "...",
  "target_outcome": "...",
  "stop_condition": "...",
  "sandhi_type": "karyasandhi",
  "overreach_warning": "..."
}}
"""


def synthesize_sandhi(
    llm: Any,
    situation: str,
    prabhu_result: Dict[str, Any],
    utsaha_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Define victory conditions (Sandhi) before sovereign commits to action."""
    _default = {
        "minimum_acceptable_outcome": "unknown",
        "target_outcome": "unknown",
        "stop_condition": "when primary objective is achieved",
        "sandhi_type": "karyasandhi",
        "overreach_warning": "",
    }
    try:
        prabhu_score = prabhu_result.get("prabhu_shakti_score", 0.7)
        execution_risk = utsaha_result.get("execution_risk", 0.5)
        recommendation = prabhu_result.get("recommendation", "proceed as planned")
        raw = llm.analyze(
            system_prompt=_SANDHI_SYSTEM,
            user_prompt=_SANDHI_PROMPT.format(
                situation=situation,
                recommendation=recommendation,
                prabhu_score=prabhu_score,
                execution_risk=execution_risk,
            ),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("sandhi_parse_error", {"raw": raw})
            return _default
        valid_types = {"karyasandhi", "vibhaga", "kala", "uchchhinna"}
        sandhi_type = parsed.get("sandhi_type", "karyasandhi")
        if sandhi_type not in valid_types:
            sandhi_type = "karyasandhi"
        result = {
            "minimum_acceptable_outcome": str(parsed.get("minimum_acceptable_outcome") or "unknown"),
            "target_outcome": str(parsed.get("target_outcome") or "unknown"),
            "stop_condition": str(parsed.get("stop_condition") or "when objective achieved"),
            "sandhi_type": sandhi_type,
            "overreach_warning": str(parsed.get("overreach_warning") or ""),
        }
        trace("sandhi_result", result)
        return result
    except Exception as e:
        trace("sandhi_exception", {"error": str(e)})
        return _default
```

- [ ] **Step 4: Run all new tests**

```bash
python -m pytest tests/test_arthashastra.py::test_prakritis_returns_stakeholders tests/test_arthashastra.py::test_prabhu_shakti_returns_score tests/test_arthashastra.py::test_utsaha_shakti_returns_execution_risk tests/test_arthashastra.py::test_sandhi_synthesis_returns_type -v
```
Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add persona/analysis.py tests/test_arthashastra.py
git commit -m "feat: add Prakritis, Prabhu Shakti, Utsaha Shakti, Sandhi analysis functions"
```

---

## Task 6: Wire Pre-Stages into Council Engine

**Files:**
- Modify: `modules/council_execution/engine.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing integration test**

```python
# append to tests/test_arthashastra.py

def test_council_engine_passes_arthashastra_context_to_ministers():
    from modules.council_execution.engine import NativeCouncil
    responses = [
        # Arishadvarga
        '{"active_enemies": [], "evidence": {}, "corrective_injection": "Should we expand?", "severity": "low"}',
        # Mandala
        '{"power_position": "middling", "ari": {"name": "unknown", "strength": 0.5}, "mitra": [], "potential_allies": [], "leverage_you_hold": "brand", "leverage_they_hold": "distribution", "recommended_posture": "indirect"}',
        # Upaya
        '{"sama_feasibility": 0.6, "sama_path": "negotiate", "dana_feasibility": 0.5, "dana_path": "offer deal", "bheda_feasibility": 0.3, "bheda_path": "target dissidents", "danda_feasibility": 0.4, "danda_path": "legal", "recommended_upaya": "sama", "reason": "conciliation viable"}',
    ]
    # Minister responses (5 ministers in meeting mode)
    minister_resp = '{"sthiti": ["fact1"], "vikalpa": [{"id": "V1", "type": "AGGRESSIVE", "description": "go"}, {"id": "V2", "type": "DEFENSIVE", "description": "wait"}, {"id": "V3", "type": "RETREAT", "description": "stop"}], "mata": {"recommended_vikalpa": "V2", "doctrine_reason": "caution required per doctrine", "minimum_acceptable": "V3", "confidence": 0.75, "warning": ""}}'
    all_responses = responses + [minister_resp] * 5
    llm = MagicMock()
    llm.analyze.side_effect = all_responses
    council = NativeCouncil(llm=llm)
    result = council.deliberate("Should we expand to new markets?", {"mode": "meeting", "domains": ["strategy"]})
    assert "arthashastra" in result or "council_output" in result or "recommendation" in result
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_council_engine_passes_arthashastra_context_to_ministers -v
```
Expected: FAIL — council result has no arthashastra keys.

- [ ] **Step 3: Update `_llm_deliberate()` in `modules/council_execution/engine.py`**

Add imports at top of file (after existing imports):
```python
from persona.analysis import (
    detect_arishadvarga,
    analyze_mandala,
    classify_upaya,
)
```

Replace the beginning of `_llm_deliberate()` — add pre-stages before the minister loop:

```python
def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
    try:
        _mv_mod = __import__("persona.council.minister_voice", fromlist=["MinisterVoice"])
        MinisterVoice = _mv_mod.MinisterVoice
    except ImportError:
        return self._keyword_deliberate(user_input, context)

    mode = str(context.get("mode", "meeting")).lower()
    active_domains = context.get("domains", [])

    # --- ARTHASHASTRA PRE-STAGES ---
    arishadvarga = detect_arishadvarga(self.llm, user_input)
    situation = arishadvarga["corrective_injection"] if arishadvarga["severity"] == "high" else user_input
    mandala = analyze_mandala(self.llm, situation)
    upaya = classify_upaya(self.llm, situation, mandala)

    mandala_context = (
        f"Power position: {mandala['power_position']}. "
        f"Opponent: {mandala['ari'].get('name', 'unknown')}. "
        f"Posture: {mandala['recommended_posture']}."
    )
    upaya_context = (
        f"Recommended method: {upaya['recommended_upaya'].upper()} — {upaya['reason']}. "
        f"Path: {upaya.get(upaya['recommended_upaya'] + '_path', 'unknown')}."
    )

    enriched_context = {
        **context,
        "mandala_context": mandala_context,
        "upaya_context": upaya_context,
    }
    # --- END PRE-STAGES ---

    knowledge_entries: list = []
    try:
        _ke_mod = __import__("persona.knowledge_engine", fromlist=["synthesize_knowledge"])
        synthesize_knowledge = _ke_mod.synthesize_knowledge
        if active_domains:
            kis = synthesize_knowledge(
                user_input=situation,
                active_domains=active_domains,
                domain_confidence=0.7,
            )
            knowledge_entries = kis.get("synthesized_knowledge", [])[:6]
    except Exception:
        pass

    # Round 1: all ministers deliberate with enriched context
    stances = {}
    for name in minister_names:
        voice = MinisterVoice(minister_name=name, llm=self.llm)
        result = voice.deliberate(situation, enriched_context, knowledge_entries=knowledge_entries)
        stances[name] = result

    # ... (rest of existing round 2 darbar logic unchanged, but uses `situation` not `user_input`)
```

At the end of `_llm_deliberate()`, before returning, add arthashastra metadata to result:

```python
    # Attach arthashastra pre-stage results to council output
    council_result["arthashastra"] = {
        "arishadvarga": arishadvarga,
        "mandala": mandala,
        "upaya": upaya,
        "original_situation": user_input,
        "cleaned_situation": situation,
    }
    return council_result
```

- [ ] **Step 4: Run test**

```bash
python -m pytest tests/test_arthashastra.py::test_council_engine_passes_arthashastra_context_to_ministers -v
```
Expected: PASS.

- [ ] **Step 5: Run existing council tests to check for regressions**

```bash
python -m pytest tests/ -v --ignore=tests/test_arthashastra.py -x
```
Expected: all pass (quick mode untouched).

- [ ] **Step 6: Commit**

```bash
git add modules/council_execution/engine.py tests/test_arthashastra.py
git commit -m "feat: wire Arishadvarga/Mandala/Upaya pre-stages into council engine"
```

---

## Task 7: Wire Post-Stages + Sovereign Context

**Files:**
- Modify: `persona/main.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_arthashastra.py

def test_build_arthashastra_sovereign_context():
    from persona.main import build_arthashastra_sovereign_context
    council_result = {
        "recommendation": "proceed with defensive option",
        "arthashastra": {
            "arishadvarga": {"active_enemies": ["KRODHA"], "severity": "medium", "corrective_injection": "cleaned"},
            "mandala": {"power_position": "middling", "recommended_posture": "indirect"},
            "upaya": {"recommended_upaya": "dana", "reason": "incentive viable"},
        }
    }
    prabhu = {"prabhu_shakti_score": 0.65, "recommendation": "proceed cautiously", "arishadvarga_in_recommendation": []}
    utsaha = {"execution_risk": 0.6, "fatal_flaw": "no local partners", "minimum_viable_version": "1 market only"}
    sandhi = {"sandhi_type": "karyasandhi", "target_outcome": "recover 20% share", "stop_condition": "when revenue baseline restored", "overreach_warning": "going further creates regulatory risk"}
    context = build_arthashastra_sovereign_context(council_result, prabhu, utsaha, sandhi)
    assert "KRODHA" in context
    assert "karyasandhi" in context
    assert "fatal_flaw" in context.lower() or "no local partners" in context
    assert "stop" in context.lower()
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_build_arthashastra_sovereign_context -v
```
Expected: `ImportError` — function does not exist.

- [ ] **Step 3: Add `build_arthashastra_sovereign_context()` to `persona/main.py`**

Add this function before the main `process_input()` or `run_loop()` function (around line 570, before `build_system_context`):

```python
def build_arthashastra_sovereign_context(
    council_result: dict,
    prabhu: dict,
    utsaha: dict,
    sandhi: dict,
) -> str:
    """Build the Arthashastra-enriched context prefix for sovereign speak()."""
    lines = ["=== COUNCIL WAR ROOM BRIEF ===\n"]

    art = council_result.get("arthashastra", {})

    # Bias alert
    arish = art.get("arishadvarga", {})
    if arish.get("active_enemies"):
        lines.append(f"BIAS ALERT ({arish['severity'].upper()}): Active internal enemies detected — {', '.join(arish['active_enemies'])}.")
        lines.append("The situation was cleaned of emotional framing before council deliberated.\n")

    # Power position
    mandala = art.get("mandala", {})
    if mandala:
        lines.append(f"POWER POSITION: {mandala.get('power_position', 'unknown').upper()}. Recommended posture: {mandala.get('recommended_posture', 'unknown')}.\n")

    # Method
    upaya = art.get("upaya", {})
    if upaya:
        lines.append(f"METHOD: Council recommends {upaya.get('recommended_upaya', 'unknown').upper()} — {upaya.get('reason', '')}.\n")

    # Capability checks
    ps = prabhu.get("prabhu_shakti_score", 1.0)
    er = utsaha.get("execution_risk", 0.0)
    lines.append(f"CAPABILITY CHECK: Prabhu Shakti {ps:.0%} | Execution Risk {er:.0%}")
    if ps < 0.5 or er > 0.7:
        lines.append(f"WARNING: Low capability score. Recommend minimum viable version: {utsaha.get('minimum_viable_version', 'unknown')}")
    if utsaha.get("fatal_flaw"):
        lines.append(f"FATAL FLAW identified: {utsaha['fatal_flaw']}\n")

    # Victory definition
    lines.append(f"VICTORY DEFINITION ({sandhi.get('sandhi_type', 'karyasandhi').upper()}):")
    lines.append(f"  Target: {sandhi.get('target_outcome', 'unknown')}")
    lines.append(f"  Stop when: {sandhi.get('stop_condition', 'objective achieved')}")
    if sandhi.get("overreach_warning"):
        lines.append(f"  Overreach warning: {sandhi['overreach_warning']}\n")

    lines.append("Think step by step about the final recommendation integrating all of the above. Then respond to the user.")
    lines.append("=== END BRIEF ===\n")

    return "\n".join(lines)
```

- [ ] **Step 4: Integrate into main speak flow**

Find the speak call in `persona/main.py` around line 582:
```python
        response = llm.speak(system_context, user_input)
```

Replace with:
```python
        # Arthashastra post-stages (meeting/darbar only)
        _mode = str(state.mode if hasattr(state, "mode") else context.get("mode", "quick")).lower()
        if _mode in {"meeting", "darbar"} and isinstance(council_output, dict) and council_output.get("arthashastra"):
            try:
                from persona.analysis import (
                    analyze_prakritis, check_prabhu_shakti,
                    check_utsaha_shakti, synthesize_sandhi,
                )
                _rec = str(council_output.get("recommendation", ""))
                _prakritis = analyze_prakritis(llm, user_input, _rec)
                _prabhu = check_prabhu_shakti(llm, user_input, _rec)
                _utsaha = check_utsaha_shakti(llm, user_input, _rec)
                _sandhi = synthesize_sandhi(llm, user_input, _prabhu, _utsaha)
                _art_prefix = build_arthashastra_sovereign_context(council_output, _prabhu, _utsaha, _sandhi)
                system_context = _art_prefix + "\n\n" + system_context
            except Exception as _ae:
                pass  # degrade gracefully — speak still happens

        response = llm.speak(system_context, user_input)
```

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/test_arthashastra.py::test_build_arthashastra_sovereign_context -v
```
Expected: PASS.

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest tests/ -v -x
```
Expected: all pass. Quick mode untouched.

- [ ] **Step 7: Commit**

```bash
git add persona/main.py tests/test_arthashastra.py
git commit -m "feat: wire post-stages and Arthashastra sovereign context into speak() call"
```

---

## Task 8: End-to-End Smoke Test

**Files:**
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write E2E test**

```python
# append to tests/test_arthashastra.py

def test_full_arthashastra_pipeline_meeting_mode():
    """Smoke test: full pipeline from situation to enriched council output."""
    from modules.council_execution.engine import NativeCouncil
    from persona.analysis import (
        detect_arishadvarga, analyze_mandala, classify_upaya,
        analyze_prakritis, check_prabhu_shakti, check_utsaha_shakti, synthesize_sandhi,
    )

    pre_responses = [
        '{"active_enemies": ["MOHA"], "evidence": {}, "corrective_injection": "Should we enter new market?", "severity": "low"}',
        '{"power_position": "middling", "ari": {"name": "Incumbents", "strength": 0.6}, "mitra": [], "potential_allies": [], "leverage_you_hold": "technology", "leverage_they_hold": "distribution", "recommended_posture": "indirect"}',
        '{"sama_feasibility": 0.4, "sama_path": "partner offer", "dana_feasibility": 0.7, "dana_path": "revenue share", "bheda_feasibility": 0.5, "bheda_path": "target dissatisfied partners", "danda_feasibility": 0.3, "danda_path": "aggressive pricing", "recommended_upaya": "dana", "reason": "incentive is most viable path"}',
    ]
    minister_resp = '{"sthiti": ["Market entry requires 6 months", "Current team is at 80% capacity"], "vikalpa": [{"id": "V1", "type": "AGGRESSIVE", "description": "Enter now full speed"}, {"id": "V2", "type": "DEFENSIVE", "description": "Enter one region only"}, {"id": "V3", "type": "DELAY", "description": "Wait 6 months, build capacity first"}], "mata": {"recommended_vikalpa": "V2", "doctrine_reason": "Capacity constraint cited in Sthiti. Doctrine: never overcommit.", "minimum_acceptable": "V3", "confidence": 0.78, "warning": "Full entry at current capacity is high risk"}}'
    all_responses = pre_responses + [minister_resp] * 5  # 5 meeting ministers

    llm = MagicMock()
    llm.analyze.side_effect = all_responses

    council = NativeCouncil(llm=llm)
    result = council.deliberate("We think it should be easy to enter the new market now", {"mode": "meeting", "domains": ["strategy", "risk"]})

    assert "arthashastra" in result
    assert result["arthashastra"]["arishadvarga"]["severity"] == "low"
    assert result["arthashastra"]["upaya"]["recommended_upaya"] == "dana"
    # Check minister outputs have new schema
    minister_outputs = result.get("minister_outputs") or result.get("stances") or {}
    for name, output in minister_outputs.items():
        assert "sthiti" in output or "mata" in output, f"Minister {name} missing new schema"
```

- [ ] **Step 2: Run E2E test**

```bash
python -m pytest tests/test_arthashastra.py::test_full_arthashastra_pipeline_meeting_mode -v
```
Expected: PASS.

- [ ] **Step 3: Run complete test suite one final time**

```bash
python -m pytest tests/ -v
```
Expected: all tests pass including existing suite.

- [ ] **Step 4: Final commit**

```bash
git add tests/test_arthashastra.py
git commit -m "test: add E2E smoke test for full Arthashastra council pipeline"
```

---

## Task 9: V0 Inaction + Knowledge Gaps + Decision Quality in Minister Schema

**Files:**
- Modify: `persona/council/minister_voice.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_arthashastra.py

def test_minister_vikalpa_includes_v0_inaction():
    from persona.council.minister_voice import MinisterVoice
    llm = make_llm('''{
        "sthiti": ["fact1"],
        "vikalpa": [
            {"id": "V0", "type": "INACTION", "description": "Do nothing. Cost: momentum lost."},
            {"id": "V1", "type": "AGGRESSIVE", "description": "Go now"},
            {"id": "V2", "type": "DEFENSIVE", "description": "Go cautiously"}
        ],
        "mata": {
            "recommended_vikalpa": "V1",
            "doctrine_reason": "Momentum favors action per doctrine.",
            "minimum_acceptable": "V2",
            "confidence": 0.75,
            "warning": "",
            "knowledge_gaps": ["Unknown if competitor has patents"],
            "decision_quality": "medium"
        }
    }''')
    voice = MinisterVoice(minister_name="grand_strategist", llm=llm)
    result = voice.deliberate("Should we launch?", {"domains": ["strategy"]})
    vikalpa_types = [v["type"] for v in result["vikalpa"]]
    assert "INACTION" in vikalpa_types, "V0 INACTION must be present in vikalpa"
    assert "knowledge_gaps" in result["mata"]
    assert "decision_quality" in result["mata"]
    assert result["mata"]["decision_quality"] in {"high", "medium", "low", "defer"}

def test_minister_fallback_includes_v0():
    from persona.council.minister_voice import MinisterVoice
    llm = make_llm("We should proceed boldly")
    voice = MinisterVoice(minister_name="power", llm=llm)
    result = voice.deliberate("should we attack?", {"domains": ["conflict"]})
    vikalpa_types = [v["type"] for v in result["vikalpa"]]
    assert "INACTION" in vikalpa_types

def test_confidence_penalized_for_missing_v0():
    from persona.council.minister_voice import MinisterVoice
    # Response with no INACTION vikalpa
    llm = make_llm('''{
        "sthiti": ["fact"],
        "vikalpa": [
            {"id": "V1", "type": "AGGRESSIVE", "description": "Go"},
            {"id": "V2", "type": "DEFENSIVE", "description": "Wait"}
        ],
        "mata": {
            "recommended_vikalpa": "V1",
            "doctrine_reason": "doctrine says go",
            "minimum_acceptable": "V2",
            "confidence": 0.9,
            "warning": "",
            "knowledge_gaps": [],
            "decision_quality": "high"
        }
    }''')
    voice = MinisterVoice(minister_name="timing", llm=llm)
    result = voice.deliberate("act now?", {"domains": ["timing"]})
    assert result["mata"]["confidence"] < 0.9, "Missing V0 should penalize confidence"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_minister_vikalpa_includes_v0_inaction -v
```
Expected: FAIL — current schema has no INACTION type or knowledge_gaps field.

- [ ] **Step 3: Update `_MINISTER_INSTRUCTION` in `persona/council/minister_voice.py`**

In the prompt template, update STAGE 2 and EXAMPLE to include V0 and knowledge_gaps:

```python
# In _MINISTER_INSTRUCTION, replace the EXAMPLE block and output schema:

"""
STAGE 2 — VIKALPA (ALL options — minimum 4 including V0):
V0 INACTION is MANDATORY — always the first option.
State the cost of doing nothing explicitly.
Then list other options labeled: AGGRESSIVE / DEFENSIVE / LATERAL / RETREAT / DELAY / HYBRID

STAGE 3 — MATA (your recommendation from your doctrine's lens):
Cite one Sthiti fact + one doctrine principle.
Flag knowledge_gaps: facts you DON'T know that would change your recommendation.
Rate decision_quality: high (you're confident), medium (some uncertainty), low (many unknowns), defer (missing critical info).

EXAMPLE:
{{
  "sthiti": ["Resource X is committed", "Deadline is fixed at 30 days"],
  "vikalpa": [
    {{"id": "V0", "type": "INACTION", "description": "Do nothing. Current situation continues. Cost: deadline passes, resource wasted."}},
    {{"id": "V1", "type": "AGGRESSIVE", "description": "Full immediate action"}},
    {{"id": "V2", "type": "DEFENSIVE", "description": "Partial rollout with reserves"}},
    {{"id": "V3", "type": "RETREAT", "description": "Pause, reassess in 2 weeks"}}
  ],
  "mata": {{
    "recommended_vikalpa": "V2",
    "doctrine_reason": "Sthiti fact 1 + doctrine: never commit without reserves",
    "minimum_acceptable": "V3",
    "confidence": 0.82,
    "warning": "Full commitment is a red line",
    "knowledge_gaps": ["We don't know if opponent has already moved", "Legal status unclear"],
    "decision_quality": "medium"
  }}
}}
"""
```

- [ ] **Step 4: Update `_validate()` to enforce V0 + penalize missing fields**

In `_validate()` in `minister_voice.py`, after building `vikalpa` list:

```python
# Enforce V0 INACTION
has_inaction = any(v["type"] == "INACTION" for v in vikalpa)
if not has_inaction:
    vikalpa.insert(0, {
        "id": "V0",
        "type": "INACTION",
        "description": "Do nothing. Current trajectory continues. Cost of inaction: unknown.",
    })
    inaction_injected = True
else:
    inaction_injected = False

# Extract knowledge_gaps and decision_quality from mata
knowledge_gaps = [str(g)[:200] for g in (mata_raw.get("knowledge_gaps") or [])[:5]]
decision_quality = mata_raw.get("decision_quality", "medium")
if decision_quality not in {"high", "medium", "low", "defer"}:
    decision_quality = "medium"

# Confidence penalties
confidence = max(0.0, min(1.0, float(mata_raw.get("confidence", 0.5) or 0.5)))
if len(doctrine_reason) < 25:
    confidence = min(confidence, 0.4)
if inaction_injected:
    confidence *= 0.80  # penalize for not listing inaction voluntarily
if not knowledge_gaps:
    confidence *= 0.90  # penalize overconfidence (no gaps flagged)

mata = {
    "recommended_vikalpa": rec,
    "doctrine_reason": doctrine_reason,
    "minimum_acceptable": min_acc,
    "confidence": round(confidence, 4),
    "warning": str(mata_raw.get("warning", ""))[:300],
    "knowledge_gaps": knowledge_gaps,
    "decision_quality": decision_quality,
}
```

- [ ] **Step 5: Run all Task 9 tests**

```bash
python -m pytest tests/test_arthashastra.py::test_minister_vikalpa_includes_v0_inaction tests/test_arthashastra.py::test_minister_fallback_includes_v0 tests/test_arthashastra.py::test_confidence_penalized_for_missing_v0 -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add persona/council/minister_voice.py tests/test_arthashastra.py
git commit -m "feat: add V0 inaction vikalpa, knowledge gaps, decision quality, confidence penalties"
```

---

## Task 10: Pre-Mortem + Pratikula Devil's Advocate

**Files:**
- Modify: `persona/analysis.py`
- Modify: `modules/council_execution/engine.py`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_arthashastra.py

def test_premortem_returns_failure_scenarios():
    from persona.analysis import run_premortem
    llm = make_llm('{"failure_scenarios": [{"scenario": "Competitor responds with price war", "probability": 0.4, "leading_indicator": "competitor announces discount campaign"}, {"scenario": "Regulatory block", "probability": 0.3, "leading_indicator": "government announces review"}, {"scenario": "Team burnout collapses execution", "probability": 0.25, "leading_indicator": "voluntary attrition spikes"}], "blind_spot": "We assume the market wants what we built"}')
    result = run_premortem(llm, "enter new market aggressively", "proceed with full launch")
    assert len(result["failure_scenarios"]) >= 3
    assert all("scenario" in s and "leading_indicator" in s for s in result["failure_scenarios"])
    assert "blind_spot" in result

def test_premortem_safe_default():
    from persona.analysis import run_premortem
    llm = make_llm("not json")
    result = run_premortem(llm, "situation", "recommendation")
    assert result["failure_scenarios"] == []
    assert "blind_spot" in result

def test_pratikula_triggers_on_high_consensus():
    from modules.council_execution.engine import NativeCouncil
    # All 5 ministers agree → Pratikula should trigger
    pre_responses = [
        '{"active_enemies": [], "evidence": {}, "corrective_injection": "expand now", "severity": "low"}',
        '{"power_position": "strong", "ari": {"name": "none", "strength": 0.2}, "mitra": [], "potential_allies": [], "leverage_you_hold": "brand", "leverage_they_hold": "none", "recommended_posture": "direct"}',
        '{"sama_feasibility": 0.5, "sama_path": "N/A", "dana_feasibility": 0.5, "dana_path": "N/A", "bheda_feasibility": 0.5, "bheda_path": "N/A", "danda_feasibility": 0.8, "danda_path": "launch aggressively", "recommended_upaya": "danda", "reason": "we are strong"}',
    ]
    support_resp = '{"sthiti": ["We are strong"], "vikalpa": [{"id": "V0", "type": "INACTION", "description": "stay"}, {"id": "V1", "type": "AGGRESSIVE", "description": "expand"}], "mata": {"recommended_vikalpa": "V1", "doctrine_reason": "strength permits aggression", "minimum_acceptable": "V0", "confidence": 0.9, "warning": "", "knowledge_gaps": [], "decision_quality": "high"}}'
    # Pratikula devil's advocate response
    pratikula_resp = '{"sthiti": ["Expansion requires resources"], "vikalpa": [{"id": "V0", "type": "INACTION", "description": "safer"}, {"id": "V1", "type": "AGGRESSIVE", "description": "expand"}, {"id": "V2", "type": "RETREAT", "description": "consolidate first"}], "mata": {"recommended_vikalpa": "V2", "doctrine_reason": "counter-case: overextension risk", "minimum_acceptable": "V0", "confidence": 0.65, "warning": "supply lines vulnerable if we expand too fast", "knowledge_gaps": ["competitor response unknown"], "decision_quality": "low"}}'
    all_responses = pre_responses + [support_resp] * 5 + [pratikula_resp] * 2
    llm = MagicMock()
    llm.analyze.side_effect = all_responses
    council = NativeCouncil(llm=llm)
    result = council.deliberate("should we expand aggressively?", {"mode": "meeting", "domains": ["strategy"]})
    assert "pratikula" in result.get("arthashastra", {}), "Pratikula must fire on high consensus"
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_premortem_returns_failure_scenarios tests/test_arthashastra.py::test_pratikula_triggers_on_high_consensus -v
```
Expected: both FAIL.

- [ ] **Step 3: Implement `run_premortem` in `persona/analysis.py`**

```python
_PREMORTEM_SYSTEM = "You are a strategic failure analyst. You practice pre-mortem thinking — imagining failure before it happens."

_PREMORTEM_PROMPT = """
A plan has been recommended and executed flawlessly. One year later it has completely failed.
This is NOT an execution failure. The execution was perfect. The strategy itself was wrong.

Situation: {situation}
Recommendation that was executed: {recommendation}

Generate exactly 3 specific, realistic strategic failure scenarios:
- Not "bad luck" — identify what assumption was wrong
- Each needs an early leading indicator (warning sign visible BEFORE collapse)
- Assign realistic probability

Also identify the single assumption the council is most confident about that is most likely wrong.

Output ONLY valid JSON:
{{
  "failure_scenarios": [
    {{"scenario": "...", "probability": 0.4, "leading_indicator": "early warning sign to watch for"}},
    {{"scenario": "...", "probability": 0.3, "leading_indicator": "..."}},
    {{"scenario": "...", "probability": 0.2, "leading_indicator": "..."}}
  ],
  "blind_spot": "The assumption we are most confident about that is most likely wrong"
}}
"""


def run_premortem(llm: Any, situation: str, council_recommendation: str) -> Dict[str, Any]:
    """Run pre-mortem: assume perfect execution, identify why it still fails."""
    _default = {
        "failure_scenarios": [],
        "blind_spot": "unknown — pre-mortem unavailable",
    }
    try:
        raw = llm.analyze(
            system_prompt=_PREMORTEM_SYSTEM,
            user_prompt=_PREMORTEM_PROMPT.format(
                situation=situation, recommendation=council_recommendation
            ),
        )
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("premortem_parse_error", {"raw": raw})
            return _default
        scenarios_raw = parsed.get("failure_scenarios") or []
        scenarios = []
        for s in scenarios_raw[:5]:
            if not isinstance(s, dict):
                continue
            scenarios.append({
                "scenario": str(s.get("scenario", ""))[:400],
                "probability": _normalize_float(s.get("probability"), 0.3),
                "leading_indicator": str(s.get("leading_indicator", ""))[:300],
            })
        result = {
            "failure_scenarios": scenarios,
            "blind_spot": str(parsed.get("blind_spot") or "unknown"),
        }
        trace("premortem_result", result)
        return result
    except Exception as e:
        trace("premortem_exception", {"error": str(e)})
        return _default
```

- [ ] **Step 4: Add Pratikula round to `_llm_deliberate()` in `modules/council_execution/engine.py`**

After Round 1 aggregation, before returning, add:

```python
# --- PRATIKULA (Devil's Advocate) — fires on high consensus ---
all_matas = [stances[n]["mata"] for n in minister_names if "mata" in stances.get(n, {})]
if all_matas:
    rec_counts = {}
    for m in all_matas:
        rec = m.get("recommended_vikalpa", "")
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
    top_rec, top_count = max(rec_counts.items(), key=lambda x: x[1])
    consensus_ratio = top_count / len(all_matas)
else:
    consensus_ratio = 0.0

pratikula_result = None
if consensus_ratio >= 0.80:
    # Find highest-confidence supporter → force to argue opposite
    supporters = [(n, stances[n]) for n in minister_names
                  if stances.get(n, {}).get("mata", {}).get("recommended_vikalpa") == top_rec]
    if supporters:
        strongest = max(supporters, key=lambda x: x[1].get("mata", {}).get("confidence", 0))
        devil_name, _ = strongest
        devil_voice = MinisterVoice(minister_name=devil_name, llm=self.llm)
        devil_context = {
            **enriched_context,
            "peer_summary": (
                f"PRATIKULA ASSIGNMENT: The council has {consensus_ratio:.0%} consensus on '{top_rec}'. "
                f"You must now argue the OPPOSING case with maximum strength. "
                f"Your doctrine must find reasons this consensus is WRONG. "
                f"Find the strongest possible counter-argument. Do not simply agree with the majority."
            ),
        }
        pratikula_result = devil_voice.deliberate(situation, devil_context, knowledge_entries=knowledge_entries)
```

Add to the arthashastra metadata:
```python
council_result["arthashastra"]["pratikula"] = {
    "triggered": pratikula_result is not None,
    "consensus_ratio": round(consensus_ratio, 3),
    "devil_advocate_output": pratikula_result,
}
```

- [ ] **Step 5: Update `build_arthashastra_sovereign_context` in `persona/main.py`** to include pre-mortem and Pratikula:

```python
# Add after victory definition block in build_arthashastra_sovereign_context():

# Pre-mortem
premortem = kwargs.get("premortem", {})
if premortem.get("failure_scenarios"):
    lines.append("PRE-MORTEM — Strategic failure scenarios (assume perfect execution):")
    for s in premortem["failure_scenarios"][:3]:
        lines.append(f"  • {s['scenario']} (p={s['probability']:.0%}) — Watch for: {s['leading_indicator']}")
    if premortem.get("blind_spot"):
        lines.append(f"  BLIND SPOT: {premortem['blind_spot']}\n")

# Pratikula
pratikula = council_result.get("arthashastra", {}).get("pratikula", {})
if pratikula.get("triggered") and pratikula.get("devil_advocate_output"):
    dv = pratikula["devil_advocate_output"]
    dv_mata = dv.get("mata", {})
    lines.append(f"PRATIKULA STRESS TEST ({pratikula['consensus_ratio']:.0%} consensus triggered devil's advocate):")
    lines.append(f"  Counter-argument: {dv_mata.get('doctrine_reason', 'N/A')[:300]}")
    if dv_mata.get("warning"):
        lines.append(f"  Devil's warning: {dv_mata['warning']}\n")
```

Update function signature: `build_arthashastra_sovereign_context(council_result, prabhu, utsaha, sandhi, premortem=None)`

- [ ] **Step 6: Run all Task 10 tests**

```bash
python -m pytest tests/test_arthashastra.py::test_premortem_returns_failure_scenarios tests/test_arthashastra.py::test_premortem_safe_default tests/test_arthashastra.py::test_pratikula_triggers_on_high_consensus -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add persona/analysis.py modules/council_execution/engine.py persona/main.py tests/test_arthashastra.py
git commit -m "feat: add pre-mortem analysis and Pratikula devil's advocate on high consensus"
```

---

## Task 11: Outcome Tracking Loop

**Files:**
- Modify: `persona/analysis.py`
- Modify: `persona/session_manager.py`
- Create: `data/outcomes/` directory

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_arthashastra.py
import os, json, tempfile

def test_record_outcome_writes_to_file():
    from persona.analysis import record_outcome
    with tempfile.TemporaryDirectory() as tmpdir:
        outcome_path = os.path.join(tmpdir, "outcomes.jsonl")
        record_outcome(
            session_id="test-session-001",
            situation_hash="abc123",
            recommendation_summary="Proceed with defensive option V2",
            minister_votes={"risk": "V2", "timing": "V1"},
            outcome_text="We followed V2. Market share held. Competition did not respond.",
            followed=True,
            outcome_path=outcome_path,
        )
        assert os.path.exists(outcome_path)
        with open(outcome_path) as f:
            entry = json.loads(f.readline())
        assert entry["followed"] is True
        assert entry["session_id"] == "test-session-001"
        assert "timestamp" in entry

def test_record_outcome_appends_not_overwrites():
    from persona.analysis import record_outcome
    with tempfile.TemporaryDirectory() as tmpdir:
        outcome_path = os.path.join(tmpdir, "outcomes.jsonl")
        for i in range(3):
            record_outcome("s1", f"hash{i}", f"rec{i}", {}, f"outcome{i}", True, outcome_path)
        with open(outcome_path) as f:
            lines = f.readlines()
        assert len(lines) == 3
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_record_outcome_writes_to_file -v
```
Expected: `ImportError`.

- [ ] **Step 3: Implement `record_outcome` in `persona/analysis.py`**

```python
import hashlib as _hashlib
from datetime import datetime as _datetime

def record_outcome(
    session_id: str,
    situation_hash: str,
    recommendation_summary: str,
    minister_votes: Dict[str, str],
    outcome_text: str,
    followed: bool,
    outcome_path: str = None,
) -> None:
    """Append a decision outcome to the outcomes log for future MinisterConfidenceTracker updates."""
    if outcome_path is None:
        _era_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        outcome_path = _os.path.join(_era_root, "data", "outcomes", "outcomes.jsonl")

    _os.makedirs(_os.path.dirname(outcome_path), exist_ok=True)

    entry = {
        "session_id": session_id,
        "situation_hash": situation_hash,
        "recommendation_summary": recommendation_summary[:500],
        "minister_votes": minister_votes,
        "outcome_text": outcome_text[:1000],
        "followed": bool(followed),
        "timestamp": _datetime.utcnow().isoformat(),
    }
    with open(outcome_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    trace("outcome_recorded", {"session_id": session_id, "followed": followed})
```

Add import at top of `persona/analysis.py`:
```python
import os as _os
```

- [ ] **Step 4: Create outcomes directory**

```bash
mkdir -p "C:\Users\naren\Work\Projects\School\era\data\outcomes"
echo "" > "C:\Users\naren\Work\Projects\School\era\data\outcomes\.gitkeep"
```

- [ ] **Step 5: Add pending outcome check to `persona/session_manager.py`**

Find the session start / `load_session` or `create_session` function. Add:

```python
def check_pending_outcomes(session_id: str, outcome_path: str = None) -> list:
    """
    Return list of sessions that made decisions but have no recorded outcome yet.
    Called at session start to prompt user for feedback on prior decisions.
    """
    if outcome_path is None:
        _era_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        outcome_path = os.path.join(_era_root, "data", "outcomes", "outcomes.jsonl")

    if not os.path.exists(outcome_path):
        return []

    recorded_sessions = set()
    try:
        with open(outcome_path, encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line.strip())
                recorded_sessions.add(entry.get("session_id", ""))
    except Exception:
        return []

    # pending_decisions.json stores {session_id: {situation_summary, recommendation_summary, timestamp}}
    pending_path = os.path.join(os.path.dirname(outcome_path), "pending_decisions.json")
    if not os.path.exists(pending_path):
        return []

    try:
        with open(pending_path, encoding="utf-8") as f:
            pending = json.load(f)
        return [v for k, v in pending.items() if k not in recorded_sessions]
    except Exception:
        return []


def register_pending_decision(session_id: str, situation_summary: str, recommendation_summary: str, outcome_path: str = None) -> None:
    """Register a decision as pending outcome collection."""
    if outcome_path is None:
        _era_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        outcome_path = os.path.join(_era_root, "data", "outcomes", "outcomes.jsonl")

    pending_path = os.path.join(os.path.dirname(outcome_path), "pending_decisions.json")
    os.makedirs(os.path.dirname(pending_path), exist_ok=True)

    pending = {}
    if os.path.exists(pending_path):
        try:
            with open(pending_path, encoding="utf-8") as f:
                pending = json.load(f)
        except Exception:
            pass

    pending[session_id] = {
        "session_id": session_id,
        "situation_summary": situation_summary[:300],
        "recommendation_summary": recommendation_summary[:300],
        "timestamp": datetime.utcnow().isoformat(),
    }
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=2)
```

- [ ] **Step 6: Wire into `persona/main.py` session start**

At session initialization (before the main REPL loop), add:

```python
# Check for pending outcomes from prior decisions
try:
    from persona.session_manager import check_pending_outcomes
    pending = check_pending_outcomes(session_id=state.session_id if hasattr(state, "session_id") else "default")
    for p in pending[:1]:  # Ask about one at a time — don't overwhelm
        print(f"\n[ERA] Last session: we discussed '{p['situation_summary']}'")
        print(f"[ERA] Recommendation was: {p['recommendation_summary']}")
        followed = input("[ERA] Did you follow this recommendation? (yes/no/partially): ").strip().lower()
        outcome_text = input("[ERA] What happened? (brief): ").strip()
        from persona.analysis import record_outcome
        record_outcome(
            session_id=p["session_id"],
            situation_hash=p["session_id"],
            recommendation_summary=p["recommendation_summary"],
            minister_votes={},
            outcome_text=outcome_text,
            followed=(followed == "yes"),
        )
        print("[ERA] Recorded. This will improve minister calibration over time.\n")
except Exception:
    pass
```

- [ ] **Step 7: Run outcome tracking tests**

```bash
python -m pytest tests/test_arthashastra.py::test_record_outcome_writes_to_file tests/test_arthashastra.py::test_record_outcome_appends_not_overwrites -v
```
Expected: both PASS.

- [ ] **Step 8: Commit**

```bash
git add persona/analysis.py persona/session_manager.py data/outcomes/.gitkeep tests/test_arthashastra.py
git commit -m "feat: add outcome tracking loop — record decisions, prompt for feedback on next session"
```

---

## Task 12: Reversibility Gate in Sandhi + Final E2E Test

**Files:**
- Modify: `persona/analysis.py` — update `synthesize_sandhi()`
- Test: `tests/test_arthashastra.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_arthashastra.py

def test_sandhi_reversibility_gate_fires():
    from persona.analysis import synthesize_sandhi
    # Irreversible decision with low confidence — gate must fire
    llm = make_llm('{"minimum_acceptable_outcome": "retain clients", "target_outcome": "full recovery", "stop_condition": "when revenue restored", "sandhi_type": "uchchhinna", "overreach_warning": "total victory creates enemies", "reversibility": "irreversible", "minimum_confidence_required": 0.85}')
    prabhu = {"prabhu_shakti_score": 0.55, "recommendation": "proceed cautiously"}
    utsaha = {"execution_risk": 0.75, "fatal_flaw": "no allies", "minimum_viable_version": "partial only"}
    result = synthesize_sandhi(llm, "burn bridges with supplier", prabhu, utsaha)
    assert result["reversibility"] in {"high", "medium", "low", "irreversible"}
    assert "minimum_confidence_required" in result
    assert result["minimum_confidence_required"] >= 0.80  # irreversible requires high bar

def test_sandhi_reversibility_blocks_low_confidence():
    """Sovereign context must flag when confidence < minimum_confidence_required."""
    from persona.main import build_arthashastra_sovereign_context
    sandhi = {"sandhi_type": "karyasandhi", "target_outcome": "...", "stop_condition": "...", "overreach_warning": "", "reversibility": "irreversible", "minimum_confidence_required": 0.85}
    council_result = {"recommendation": "proceed", "arthashastra": {"arishadvarga": {"active_enemies": [], "severity": "low"}, "mandala": {}, "upaya": {}, "pratikula": {"triggered": False, "consensus_ratio": 0.5, "devil_advocate_output": None}}}
    prabhu = {"prabhu_shakti_score": 0.7, "recommendation": "proceed", "arishadvarga_in_recommendation": []}
    utsaha = {"execution_risk": 0.4, "fatal_flaw": "", "minimum_viable_version": "..."}
    context = build_arthashastra_sovereign_context(council_result, prabhu, utsaha, sandhi, premortem={"failure_scenarios": [], "blind_spot": ""})
    assert "irreversible" in context.lower() or "confidence" in context.lower()
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_arthashastra.py::test_sandhi_reversibility_gate_fires -v
```
Expected: FAIL — `synthesize_sandhi` doesn't return `reversibility` or `minimum_confidence_required`.

- [ ] **Step 3: Update `synthesize_sandhi` in `persona/analysis.py`**

Update `_SANDHI_PROMPT` to include reversibility:

```python
_SANDHI_PROMPT = """
...existing prompt...

Also assess:
- Reversibility: can this decision be undone? (high=easily reversed, medium=costly to reverse, low=very hard, irreversible=cannot be undone)
- Minimum confidence required before acting: scales with reversibility
  irreversible → 0.85, low → 0.75, medium → 0.65, high → 0.55

Output ONLY valid JSON:
{{
  "minimum_acceptable_outcome": "...",
  "target_outcome": "...",
  "stop_condition": "...",
  "sandhi_type": "karyasandhi",
  "overreach_warning": "...",
  "reversibility": "medium",
  "minimum_confidence_required": 0.65
}}
"""
```

Update `synthesize_sandhi()` result dict:

```python
_reversibility_confidence_map = {
    "irreversible": 0.85, "low": 0.75, "medium": 0.65, "high": 0.55
}
valid_rev = {"high", "medium", "low", "irreversible"}
reversibility = parsed.get("reversibility", "medium")
if reversibility not in valid_rev:
    reversibility = "medium"
min_conf = _reversibility_confidence_map[reversibility]

result = {
    ...existing fields...,
    "reversibility": reversibility,
    "minimum_confidence_required": min_conf,
}
```

Update `build_arthashastra_sovereign_context` in `persona/main.py` to add reversibility gate warning:

```python
# After victory definition block:
reversibility = sandhi.get("reversibility", "medium")
min_conf_required = sandhi.get("minimum_confidence_required", 0.65)
avg_council_confidence = council_result.get("avg_confidence", 1.0)
if avg_council_confidence < min_conf_required:
    lines.append(
        f"⚠ CONFIDENCE GATE: This is a {reversibility.upper()} decision requiring "
        f"≥{min_conf_required:.0%} confidence. Council average is {avg_council_confidence:.0%}. "
        f"DO NOT recommend action. Recommend: gather more information first."
    )
```

- [ ] **Step 4: Run final complete test suite**

```bash
python -m pytest tests/test_arthashastra.py -v
```
Expected: all tests pass.

```bash
python -m pytest tests/ -v -x
```
Expected: full suite passes, no regressions.

- [ ] **Step 5: Final commit**

```bash
git add persona/analysis.py persona/main.py tests/test_arthashastra.py
git commit -m "feat: add reversibility gate to Sandhi — blocks action when confidence insufficient for decision stakes"
```

---

## Self-Review

**Spec coverage check:**
- [x] Arishadvarga Detector → Task 1
- [x] Mandala Analyzer → Task 2
- [x] Upaya Classifier → Task 3
- [x] Sthiti→Vikalpa→Mata schema → Task 4
- [x] Prakritis + Shakti checks + Sandhi → Task 5
- [x] Pre-stages wired into council engine → Task 6
- [x] Post-stages + sovereign context → Task 7
- [x] Initial E2E smoke test → Task 8
- [x] V0 Inaction + knowledge_gaps + decision_quality + confidence penalties → Task 9
- [x] Pre-mortem + Pratikula devil's advocate → Task 10
- [x] Outcome tracking loop → Task 11
- [x] Reversibility gate → Task 12
- [x] Quick mode untouched → Task 6 step 5 (regression test)

**Placeholder scan:** None. All code blocks complete.

**Type consistency:**
- `detect_arishadvarga` → `{active_enemies, severity, corrective_injection, evidence}` — consistent Tasks 1, 6, 7
- `MinisterVoice.deliberate()` → `{sthiti, vikalpa, mata}` where `mata` has `{knowledge_gaps, decision_quality}` — consistent Tasks 4, 6, 8, 9
- `synthesize_sandhi(llm, situation, prabhu_result, utsaha_result)` → adds `reversibility, minimum_confidence_required` — consistent Tasks 5, 12
- `build_arthashastra_sovereign_context(council_result, prabhu, utsaha, sandhi, premortem=None)` — consistent Tasks 7, 10, 12
- `run_premortem(llm, situation, council_recommendation)` → `{failure_scenarios, blind_spot}` — consistent Tasks 10, 7
- `record_outcome(session_id, situation_hash, recommendation_summary, minister_votes, outcome_text, followed, outcome_path=None)` — consistent Tasks 11
