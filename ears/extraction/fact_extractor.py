"""
ears/extraction/fact_extractor.py — Turns raw self-speech (plus an optional
non-identifying context note) into structured facts.

This module only ever receives text that has already passed the privacy
gate in privacy/redaction.py — it doesn't need to know about third-party
filtering, it just extracts facts from whatever text it's handed.
"""
import json
from datetime import datetime, timezone
from ears.extraction.entity_linker import link_and_update_entities
from ears.coaching.proactive_intervention import _safe_float

EXTRACTION_PROMPT = """You are analyzing an ambient person-to-person conversation around the user (Self / Speaker 0) and the people around them (friends, family, coworkers, etc.).
The conversation may be in Hindi, Marathi, English, or Hinglish (code-switching combined).
Analyze and understand:
1. Factual insights, social context, and interpersonal dynamics.
2. How things are said: non-verbal cues (e.g. hesitation, filler words like um/hmm/arre, laughter, urgency, sighs, pacing, sarcasm).
3. The emotional tone of the speaker(s).
4. A confidence score (0.0 to 1.0) assessing how certain you are of the observation and tone.

Return ONLY a JSON array, no preamble, no markdown fences. Each item:
{{"domain": "career|finance|health|family|relationships|social|other",
  "content": "<one factual observation about the user's situation, social context, or interpersonal dynamics in clean English>",
  "emotional_tone": "stressed|anxious|enthusiastic|calm|frustrated|hesitant|sarcastic|neutral|other",
  "non_verbal_cues": "<analysis of how it was said: e.g. hesitation, urgency, laughter, defensive tone, pacing>",
  "confidence": <0.0-1.0>}}

If nothing factual/notable is present, return [].

Context note (may be empty): {context_note}
Conversation Transcript:
{text}
"""


def extract_facts(conversation_transcript: str, context_note: str = "") -> list:
    if not conversation_transcript.strip():
        return []

    prompt = EXTRACTION_PROMPT.format(context_note=context_note or "none", text=conversation_transcript)

    try:
        import os
        os.environ.setdefault("SKIP_OLLAMA_CHECK", "1")
        from persona.openrouter_runtime import OpenRouterRuntime
        llm = OpenRouterRuntime()
        raw = llm.analyze("You are a fact extraction engine. Return ONLY a JSON array.", prompt)
        facts = json.loads(raw)
    except Exception as e:
        # Fail closed: no facts rather than a crash-looping daemon
        print(f"[fact_extractor] extraction failed: {e}")
        return []

    now = datetime.now(timezone.utc).isoformat()
    episodes = [
        {
            "turn": f"ambient_{now}",
            "source": "ears_module",
            "domain": f.get("domain", "other"),
            "type": "ambient_observation",
            "content": f.get("content", ""),
            "emotional_tone": f.get("emotional_tone", "neutral"),
            "non_verbal_cues": f.get("non_verbal_cues", "None detected"),
            "confidence": _safe_float(f.get("confidence", 0.5), default=0.5),
            "speaker": "self",
            "third_party_present": bool(context_note) or "Person " in conversation_transcript,
            "third_party_content_stored": "encrypted",
        }
        for f in facts
        if f.get("content")
    ]
    return link_and_update_entities(episodes, conversation_transcript)
