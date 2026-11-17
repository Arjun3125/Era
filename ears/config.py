"""
ears/config.py — Central configuration for the Ambient Sensory Memory Module.

All secrets come from environment variables (never hardcode API keys).
Set these in a `.env` file at your era/ project root, or as system env vars.
"""
import os
from pathlib import Path

# --- Cloud STT provider (Deepgram — chosen because it does streaming +
# speaker diarization in one API, which solves "self vs. other" separation
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_MODEL = "nova-2"
DEEPGRAM_LANGUAGE = os.environ.get("DEEPGRAM_LANGUAGE", "multi")  # Supports Hindi, Marathi, English, and Hinglish combined

# --- LLM for fact extraction (OpenRouter cloud LLM) ---
LLM_URL = os.environ.get("LLM_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")

ERA_ROOT = Path(os.environ.get("ERA_ROOT", Path(__file__).resolve().parent.parent))
MEMORY_DIR = ERA_ROOT / "Memory"
ACTIVE_MEMORY_FILE = ERA_ROOT / "data" / "memory" / "episodes.jsonl"
PWM_PATH = ERA_ROOT / "data" / "pwm" / "entities.json"
EARS_STATE_DIR = ERA_ROOT / "ears" / "_state"

# --- Privacy defaults (see privacy/consent_state.py) ---
# SOLO: only your own speech is ever transcribed/stored. Other speakers'
#   content is used for momentary context only, then discarded.
# ANNOUNCED_RECORDING: you've told everyone present that this session is
#   being recorded. Only then may other speakers' content be persisted.
DEFAULT_MODE = "SOLO"

# --- Speaker identification ---
# Deepgram's diarization returns speaker indices (0, 1, 2...) per session,
# not stable identities. On each new session you'll need to confirm which
# index is you (see README_EARS.md, "Identifying yourself each session").
SELF_SPEAKER_LABEL = os.environ.get("EARS_SELF_SPEAKER", "0")

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
EARS_STATE_DIR.mkdir(parents=True, exist_ok=True)
