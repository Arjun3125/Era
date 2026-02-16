"""
PWM runtime helpers: provides stubs for the extract -> score -> commit pipeline using the templates
created from the Personal World Model document.

This module is intentionally lightweight and defensive: it does not require a running DB or LLM to import.
It provides:
- render_template(template_path, **kwargs)
- session_summary(llm, conversation_text)
- extract_signals(llm, session_summary_json)
- generate_hypotheses(llm, observations_json)
- score_confidence(llm, hypotheses_json)
- decide_commits(llm, calibrated_hypotheses_json, threshold=0.7)
- translate_to_db_changes(approved_decisions_json)

These functions call `llm.analyze`/`llm.speak` if available, otherwise return safe defaults.
"""

import json
import os
from typing import Any, Dict, List

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_template(name: str, **kwargs) -> str:
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        tmpl = f.read()
    for k, v in kwargs.items():
        tmpl = tmpl.replace("{{" + k + "}}", json.dumps(v) if not isinstance(v, str) else v)
    return tmpl


def _call_llm(llm: Any, system_prompt: str, user_prompt: str) -> str:
    caller = getattr(llm, "analyze", None) or getattr(llm, "speak", None) or getattr(llm, "generate", None)
    if not caller:
        return ""
    try:
        return caller(system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception:
        return ""


def session_summary(llm: Any, conversation_text: str) -> Dict[str, Any]:
    tpl = render_template("session_summary.txt", FULL_CONVERSATION=conversation_text)
    raw = _call_llm(llm, "Forensic summarizer", tpl)
    try:
        return json.loads(raw)
    except Exception:
        return {"events": [], "people": [], "decisions": [], "explicit_emotions": []}


def extract_signals(llm: Any, session_summary_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    tpl = render_template("signal_extraction.txt", SESSION_SUMMARY_JSON=json.dumps(session_summary_json))
    raw = _call_llm(llm, "Signal extractor", tpl)
    try:
        return json.loads(raw)
    except Exception:
        return []


def generate_hypotheses(llm: Any, observations_json: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tpl = render_template("hypothesis_generation.txt", OBSERVATIONS_JSON=json.dumps(observations_json))
    raw = _call_llm(llm, "Hypothesis generator", tpl)
    try:
        return json.loads(raw)
    except Exception:
        return []


def score_confidence(llm: Any, hypotheses_json: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tpl = render_template("confidence_scoring.txt", HYPOTHESES_JSON=json.dumps(hypotheses_json))
    raw = _call_llm(llm, "Confidence calibrator", tpl)
    try:
        return json.loads(raw)
    except Exception:
        return []


def decide_commits(llm: Any, calibrated_hypotheses_json: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
    tpl = render_template("commit_decision.txt", CALIBRATED_HYPOTHESES_JSON=json.dumps(calibrated_hypotheses_json))
    raw = _call_llm(llm, "Memory gate", tpl)
    try:
        return json.loads(raw)
    except Exception:
        # default automated decision: commit high-confidence, hold middling, reject low
        out = []
        for h in calibrated_hypotheses_json:
            conf = float(h.get("adjusted_confidence") or h.get("initial_confidence") or 0.0)
            if conf >= threshold:
                out.append({"hypothesis": h.get("hypothesis"), "decision": "COMMIT", "justification": "auto", "requires_human_confirmation": False})
            elif conf >= (threshold * 0.6):
                out.append({"hypothesis": h.get("hypothesis"), "decision": "HOLD", "justification": "auto-low", "requires_human_confirmation": False})
            else:
                out.append({"hypothesis": h.get("hypothesis"), "decision": "REJECT", "justification": "auto-low", "requires_human_confirmation": False})
        return out


def translate_to_db_changes(approved_decisions_json: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    # Minimal translator: converts commit decisions into schema-aligned record blocks
    entity_updates = []
    relationship_updates = []
    inference_records = []
    timeline_updates = []
    for d in approved_decisions_json:
        if d.get("decision") != "COMMIT":
            continue
        # Best-effort mapping: put hypothesis into an inference record
        inference_records.append({
            "inference_type": "hypothesis",
            "hypothesis": d.get("hypothesis"),
            "confidence": d.get("confidence") or 0.0,
            "supporting_observations": d.get("supporting_observations") or [],
            "contradicting_observations": d.get("contradicting_observations") or [],
        })
    return {
        "entity_updates": entity_updates,
        "relationship_updates": relationship_updates,
        "inference_records": inference_records,
        "timeline_updates": timeline_updates,
    }
