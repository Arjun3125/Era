"""Configuration constants for ingestion tests."""

import os

# Model defaults (override via env for local installs)
DEFAULT_EXTRACT_MODEL = os.getenv("OLLAMA_EXTRACT_MODEL", "qwen2.5-coder:latest")
DEFAULT_DEEPSEEK_MODEL = os.getenv("OLLAMA_DEEPSEEK_MODEL", "huihui_ai/deepseek-r1-abliterated:8b")
DEFAULT_GLYPH_REPAIR_MODEL = os.getenv("OLLAMA_GLYPH_REPAIR_MODEL", "mistral:7b")
DEFAULT_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
MAX_EMBED_CONCURRENCY = 2
MAX_WORKERS = 6
SKIP_PHASE_35_IF_CONVERTED = True
ATOMIC_JSON_WRITES = True

# Chapter classification bucket types
CHAPTER_TYPES = {
    "doctrinal",
    "commentary",
    "narrative",
    "introductory",
}

ALLOWED_DOMAINS = [
    "adaptation",
    "base",
    "conflict",
    "constraints",
    "data",
    "diplomacy",
    "discipline",
    "executor",
    "legitimacy",
    "optionality",
    "power",
    "psychology",
    "registry",
    "risk",
    "strategy",
    "technology",
    "timing",
    "truth",
]

SYSTEM_PROMPT_DOCTRINE = "You are a doctrine extraction engine."
