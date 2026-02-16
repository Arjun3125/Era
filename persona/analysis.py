"""
persona/analysis.py

Comprehensive LLM-driven analysis handshakes used by the persona runtime.

Provides small, robust wrappers around LLM calls and a keyword
fallback for domain classification. Functions are defensive, attempt
to recover from malformed LLM output, and emit traces via `trace()`
so the main runtime can observe results.

Features included (no deletions, full behavior):
- assess_coherence(llm, user_input)
- assess_situation(llm, user_input)
- assess_mode_fitness(llm, user_input, current_mode)
- classify_domains(llm, conversation_excerpt, force_guess=False)
  - LLM-backed classification with robust JSON parsing
  - force_guess behavior that falls back to a local keyword heuristic
  - traces for raw/parsing/fallback events
- assess_emotional_metrics(llm, user_input)
  - returns normalized numeric signals used to drive mode escalation,
    KIS/advice triggering, and tracing.

All functions accept an OllamaRuntime-like object (implements .analyze()).
They return plain Python dicts (JSON-like structures) and never raise
for typical LLM parse failures — instead they emit trace events and
return safe defaults to keep the runtime robust.
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional
from .trace import trace


# ---------- Utilities ----------

def _safe_parse_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Try to parse raw text into JSON. First attempt a straight json.loads.
    If that fails, attempt to extract the first {...} substring and parse it.
    Returns None on failure.
    """
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        # try to extract a JSON object using a greedy regex
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


def _normalize_float(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except Exception:
        return default


# ---------- Coherence ----------

def assess_coherence(llm: Any, user_input: str) -> Dict[str, Any]:
    """
    Ask the LLM whether the input is meaningful human communication.

    Expected JSON:
      { "coherence": 0.0-1.0, "intent_present": true|false }

    Returns a dict with safe defaults on error.
    """
    prompt = f"""
Decide whether this input is meaningful human communication.

Respond ONLY in valid JSON. Do not emit extra text.

JSON format:
{{"coherence": 0.0-1.0, "intent_present": true|false}}

Input:
{user_input}
"""
    raw = None
    try:
        raw = llm.analyze(system_prompt="Language coherence detector.", user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("coherence_parse_error", {"raw": raw})
            return {"coherence": 0.6, "intent_present": True}
        coherence = _normalize_float(parsed.get("coherence", 0.0), 0.6)
        intent = bool(parsed.get("intent_present", False))
        trace("coherence_result", {"raw": raw, "parsed": {"coherence": coherence, "intent_present": intent}})
        return {"coherence": coherence, "intent_present": intent}
    except Exception as e:
        trace("coherence_exception", {"error": str(e), "raw": raw})
        return {"coherence": 0.6, "intent_present": True}


# ---------- Situation Assessment ----------

def assess_situation(llm: Any, user_input: str) -> Dict[str, Any]:
    """
    Silent situational understanding.

    Expected JSON:
      { "situation_type": "casual|emotional|decision|unclear", "clarity": 0.0-1.0, "emotional_load": 0.0-1.0 }

    Returns safe defaults if parsing fails.
    """
    prompt = f"""
You are performing silent human intuition.

Return JSON only.

Fields:
- situation_type: casual | emotional | decision | unclear
- clarity: number 0-1
- emotional_load: number 0-1

Input:
{user_input}
"""
    raw = None
    try:
        raw = llm.analyze(system_prompt="Silent situational understanding.", user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("situation_parse_error", {"raw": raw})
            return {"situation_type": "unclear", "clarity": 0.0, "emotional_load": 0.0}
        # defensive normalization
        stype = parsed.get("situation_type") or parsed.get("type") or "unclear"
        clarity = _normalize_float(parsed.get("clarity", 0.0))
        emotional_load = _normalize_float(parsed.get("emotional_load", parsed.get("emotion", 0.0)))
        out = {"situation_type": stype, "clarity": clarity, "emotional_load": emotional_load}
        trace("situation", {"raw": raw, "parsed": out})
        return out
    except Exception as e:
        trace("situation_exception", {"error": str(e), "raw": raw})
        return {"situation_type": "unclear", "clarity": 0.0, "emotional_load": 0.0}


def assess_situation_heuristic(user_input: str) -> Dict[str, Any]:
    """
    Lightweight local heuristic to ensure we always provide a situation,
    clarity, and emotional_load. Use if the LLM fails to return usable JSON.
    """
    text = (user_input or "").lower()
    # decision indicators
    if any(w in text for w in ("decid", "decision", "whether", "choose", "quit", "leave")):
        return {"situation_type": "decision", "clarity": 0.7, "emotional_load": 0.3}
    # emotional indicators
    if any(w in text for w in ("overwhelm", "overwhelmed", "stress", "stressed", "anx", "panic", "burnout", "sad")):
        return {"situation_type": "emotional", "clarity": 0.5, "emotional_load": 0.8}
    # casual fallback
    words = len(text.split())
    if words <= 3:
        return {"situation_type": "casual", "clarity": 0.5, "emotional_load": 0.1}
    return {"situation_type": "casual", "clarity": 0.7, "emotional_load": 0.1}


# ---------- Mode Fitness ----------

def assess_mode_fitness(llm: Any, user_input: str, current_mode: str) -> Dict[str, Any]:
    """
    Silent cognitive mode assessment.

    Expected JSON:
      { "better_mode": "quick|war|meeting|darbar|none", "confidence": 0.0-1.0, "reason": "short" }

    Returns a safe default when parsing fails.
    """
    prompt = f"""
You are silently assessing whether the current thinking mode is appropriate.

Current mode: {current_mode}

Return JSON only:
{{
  "better_mode": "quick | war | meeting | darbar | none",
  "confidence": 0.0-1.0,
  "reason": "one short sentence"
}}

User input:
{user_input}
"""
    raw = None
    try:
        raw = llm.analyze(system_prompt="Silent cognitive mode assessment.", user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("mode_fitness_parse_error", {"raw": raw})
            return {"better_mode": "none", "confidence": 0.0, "reason": ""}
        better = parsed.get("better_mode", "none")
        confidence = _normalize_float(parsed.get("confidence", 0.0))
        reason = parsed.get("reason", "") or parsed.get("why", "")
        out = {"better_mode": better, "confidence": confidence, "reason": reason}
        trace("mode_fitness", {"raw": raw, "parsed": out})
        return out
    except Exception as e:
        trace("mode_fitness_exception", {"error": str(e), "raw": raw})
        return {"better_mode": "none", "confidence": 0.0, "reason": ""}


# ---------- Domain Classification + Heuristic Fallback ----------

def _heuristic_domain_guess(conversation_excerpt: str, max_domains: int = 3) -> List[str]:
    """
    Local keyword-to-domain heuristic fallback. Returns up to max_domains guesses
    sorted by simple keyword frequency.
    """
    lc = (conversation_excerpt or "").lower()
    mapping = {
        "risk": ["income", "pay", "salary", "financial", "budget", "debt", "savings", "finance", "retirement"],
        "power": ["power", "control", "authority", "influence", "boss", "manager", "dominant"],
        "strategy": ["strategy", "plan", "career", "promotion", "trajectory", "long term", "direction"],
        "psychology": ["stress", "stressful", "burnout", "anxiety", "therapy", "emotion", "feeling", "mental"],
        "data": ["data", "numbers", "metrics", "analysis", "statistics"],
        "diplomacy": ["negotiate", "negotiation", "talk", "diplomacy"],
        "technology": ["tech", "technology", "system", "software", "adoption"],
        "timing": ["time", "timing", "tempo", "when"],
        "optionality": ["option", "options", "choice", "flexible", "alternative", "alternatives"],
        "adaptation": ["adapt", "adaptation", "adjust", "resilience"],
    }
    scores: Dict[str, int] = {}
    for domain, kws in mapping.items():
        s = sum(lc.count(kw) for kw in kws)
        if s:
            scores[domain] = s
    if not scores:
        return ["strategy"]
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return [d for d, _ in ordered[:max_domains]]


def classify_domains(llm: Any, conversation_excerpt: str, force_guess: bool = False) -> Dict[str, Any]:
    """
    Classify the underlying domains of a conversation.

    Returns: {"domains": [...], "confidence": 0.0-1.0}

    Behavior:
    - Query the LLM for domains (JSON).
    - If parsing fails and force_guess==True, return a local heuristic guess.
    - If LLM returns an empty domains list but force_guess==True, use the heuristic fallback and raise confidence minimally.
    - Always emit trace events describing raw and parsed output and any fallback used.
    """
    force_hint = (
        "If you are uncertain, pick the single most relevant domain from the list and set\n"
        "a low but non-zero confidence (for example 0.1-0.4). Do NOT return an empty list.\n"
        if force_guess
        else ""
    )

    prompt = f"""
Classify the underlying domains of a conversation.

Rules:
- Choose at most 3 domains.
- Use ONLY the provided list.
- Choose dominant forces, not surface topics.
- Return JSON only with keys: {{"domains": [...], "confidence": 0.0-1.0}}

Domain list:
adaptation, conflict, data, diplomacy, discipline, grand_strategy,
intelligence, legitimacy, optionality, power, psychology, risk,
risk_resources, sovereignty, strategy, technology, timing

{force_hint}
Conversation:
{conversation_excerpt}
"""
    raw = None
    try:
        raw = llm.analyze(system_prompt="Silent domain classification.", user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("domain_classification_parse_error", {"raw": raw})
            # fall through to force_guess heuristic if requested
        else:
            # normalized return
            domains = parsed.get("domains") or []
            confidence = _normalize_float(parsed.get("confidence", 0.0))
            # if LLM returned empty domains but force_guess requested, use heuristic
            if not domains and force_guess:
                domains = _heuristic_domain_guess(conversation_excerpt)
                # give minimal boost to confidence to indicate a heuristic-latched guess
                confidence = max(confidence, 0.25)
                trace("domain_forceguess_fallback_used", {"raw": raw, "heuristic_domains": domains, "confidence": confidence})
            trace("domain_classification", {"raw": raw, "parsed": {"domains": domains, "confidence": confidence}})
            return {"domains": domains, "confidence": confidence}
    except Exception as e:
        trace("domain_classification_error", {"error": str(e), "raw": raw})

    # If we reach here, the LLM either failed to produce parseable JSON or parsing failed.
    if force_guess:
        try:
            domains = _heuristic_domain_guess(conversation_excerpt)
            trace("domain_forceguess_heuristic", {"heuristic_domains": domains})
            return {"domains": domains, "confidence": 0.2}
        except Exception as e:
            trace("domain_forceguess_heuristic_error", {"error": str(e)})
            return {"domains": [], "confidence": 0.0}

    # conservative fallback
    return {"domains": [], "confidence": 0.0}


# ---------- Emotional Metrics ----------

def assess_emotional_metrics(llm: Any, user_input: str) -> Dict[str, Any]:
    """
    NEW handshake: ask the LLM to rate emotional maturity, volatility,
    stress, confidence, mode_threshold and advice_threshold.

    Expected JSON keys (all 0.0-1.0):
      emotional_maturity, volatility, stress, confidence, mode_threshold, advice_threshold

    Returns a normalized dict with safe defaults.
    """
    prompt = f"""
Assess the emotional state and escalation signals in the user's message.

Return ONLY valid JSON.

Fields (0.0-1.0):
- emotional_maturity  : Higher means more mature / stable (1.0 = very mature)
- volatility          : How emotionally volatile the content is (1.0 = very volatile)
- stress              : How stressed the user appears (1.0 = very stressed)
- confidence          : How confident the LLM is in these ratings
- mode_threshold      : advisory signal for immediate mode escalation (1.0 indicates immediate WAR)
- advice_threshold    : advisory signal for whether to generate deeper synthesized advice (KIS)

User message:
{user_input}
"""
    raw = None
    try:
        raw = llm.analyze(system_prompt="Emotional metrics estimator.", user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None:
            trace("emotional_metrics_parse_error", {"raw": raw})
            # fall through to default values
        else:
            # normalize numeric ranges and provide defaults for missing keys
            out: Dict[str, float] = {}
            for k in ("emotional_maturity", "volatility", "stress", "confidence", "mode_threshold", "advice_threshold"):
                out[k] = _normalize_float(parsed.get(k, 0.0))
            trace("emotional_metrics", {"raw": raw, "parsed": out})
            return out
    except Exception as e:
        trace("emotional_metrics_exception", {"error": str(e), "raw": raw})

    # default safe return
    default = {
        "emotional_maturity": 0.5,
        "volatility": 0.0,
        "stress": 0.0,
        "confidence": 0.0,
        "mode_threshold": 0.0,
        "advice_threshold": 0.0,
    }
    trace("emotional_metrics_default", default)
    return default


def generate_clarifying_questions(
    llm: OllamaRuntime,
    user_input: str,
    max_questions: int = 3,
    context: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Ask the LLM to propose short clarifying questions to reduce ambiguity.

    Expected JSON output (list):
      [ {"id": "q1", "question": "...", "reason": "...", "expected_answer_type": "short|long|yesno"}, ... ]

    Returns a sanitized list of question objects. On failure returns an empty list
    and emits trace events describing the failure.
    """
    system = "Generate a small list of sharply focused clarifying questions. Return JSON array only."
    prompt = f"""
Produce up to {max_questions} short clarifying questions (1-2 sentences each).

Return JSON ONLY: an array of objects with keys: id, question, reason, expected_answer_type

Context:
{context or ''}

User message:
{user_input}
"""
    raw = None
    try:
        # prefer .analyze but fall back to other methods if not present
        caller = getattr(llm, "analyze", None) or getattr(llm, "generate", None) or getattr(llm, "speak", None)
        if not caller:
            trace("generate_clarify_no_caller", {})
            return []
        raw = caller(system_prompt=system, user_prompt=prompt)
        parsed = _safe_parse_json(raw)
        if parsed is None or not isinstance(parsed, list):
            trace("clarify_questions_parse_error", {"raw": raw})
            return []

        out: List[Dict[str, Any]] = []
        for idx, item in enumerate(parsed[:max_questions]):
            try:
                if isinstance(item, str):
                    q = {"id": f"q{idx+1}", "question": item, "reason": "", "expected_answer_type": "short"}
                elif isinstance(item, dict):
                    q = {
                        "id": item.get("id") or f"q{idx+1}",
                        "question": str(item.get("question") or item.get("q") or "").strip(),
                        "reason": str(item.get("reason") or "").strip(),
                        "expected_answer_type": item.get("expected_answer_type") or item.get("type") or "short",
                    }
                else:
                    continue

                if not q["question"]:
                    continue
                out.append(q)
            except Exception:
                continue

        trace("clarifying_questions_generated", {"count": len(out), "raw": raw})
        return out
    except Exception as e:
        trace("generate_clarify_exception", {"error": str(e), "raw": raw})
        return []