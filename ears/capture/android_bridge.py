"""
ears/capture/android_bridge.py — Receives already-transcribed, diarized
segments from the phone companion app and feeds them into the privacy gate
→ fact extraction → memory pipeline.

Design choice: the phone streams audio directly to Deepgram itself (it has
its own internet connection) and only sends the resulting text + speaker
labels back here — not raw audio. This keeps bandwidth tiny and means this
backend doesn't need to be reachable in real time; the phone can batch and
retry whenever it next has a connection to your home network.

Run with:  python -m ears.daemon
"""
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from ears.privacy.redaction import filter_segments, summarize_context_only, get_conversation_transcript_for_llm
from ears.privacy import consent_state
from ears.extraction.fact_extractor import extract_facts
from ears.memory_bridge.episodic_writer import write_episode
from ears.speaker_recognition.auto_enrollment import analyze_conversational_correlations
from ears.memory_bridge.sleep_cycle import run_sleep_cycle
from ears.coaching.morning_briefing import generate_morning_briefing, BRIEFINGS_LOG_FILE

app = FastAPI(title="Era — Ambient Sensory Memory Bridge")


class Segment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float


class IngestPayload(BaseModel):
    device_id: str
    segments: List[Segment]


@app.post("/ingest")
def ingest(payload: IngestPayload):
    raw_segments = [s.dict() for s in payload.segments]
    
    # 0. Run self-supervised acoustic correlation on incoming conversation turn pairs
    try:
        analyze_conversational_correlations(raw_segments, auto_promote=True)
    except Exception as e:
        print(f"[android_bridge] warning: auto-enrollment check failed: {e}")

    allowed = filter_segments(raw_segments)

    context_note = summarize_context_only(raw_segments)
    conversation_transcript = get_conversation_transcript_for_llm(allowed)

    if not conversation_transcript.strip():
        return {"status": "skipped", "reason": "no speech in this batch"}

    facts = extract_facts(conversation_transcript, context_note)
    for fact in facts:
        write_episode(fact)

    return {"status": "ok", "facts_written": len(facts)}


@app.post("/memory/sleep_cycle")
def trigger_sleep_cycle(archive_days: int = 30, force_archive: bool = False):
    return run_sleep_cycle(archive_days=archive_days, force_archive=force_archive)


@app.post("/coaching/morning_briefing")
def create_morning_briefing():
    return generate_morning_briefing()


@app.get("/coaching/morning_briefing/latest")
def get_latest_morning_briefing():
    if not BRIEFINGS_LOG_FILE.exists():
        return {"status": "none"}
    try:
        with open(BRIEFINGS_LOG_FILE, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
            return lines[-1] if lines else {"status": "none"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


@app.post("/consent/start_announced_recording")
def start_recording(session_id: str):
    return consent_state.start_announced_recording(session_id)


@app.post("/consent/stop")
def stop_recording():
    return consent_state.stop_announced_recording()


@app.get("/consent/status")
def status():
    return {"mode": consent_state.get_mode()}
