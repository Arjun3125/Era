"""Configuration and constants for the ingestion pipeline."""
import os

# ============================================================
# Model Configuration
# ============================================================
DEFAULT_EXTRACT_MODEL = os.environ.get("OLLAMA_EXTRACT_MODEL", "qwen2.5-coder:latest")
# Use deepseek for doctrine extraction (env var overrides, or hardcoded default)
DEFAULT_DEEPSEEK_MODEL = os.environ.get("OLLAMA_DEEPSEEK_MODEL") or "huihui_ai/deepseek-r1-abliterated:8b"
DEFAULT_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
# Use a fast model for glyph text repair (much faster than Deepseek)
DEFAULT_GLYPH_REPAIR_MODEL = os.environ.get("OLLAMA_GLYPH_REPAIR_MODEL", "dolphin-mistral:7b")

# Verify deepseek model is set
if not DEFAULT_DEEPSEEK_MODEL or DEFAULT_DEEPSEEK_MODEL.strip() == "":
    DEFAULT_DEEPSEEK_MODEL = "huihui_ai/deepseek-r1-abliterated:8b"

# ============================================================
# Processing Parameters
# ============================================================
MAX_WORKERS = 6  # Increased from 4: enables 4x throughput for Phase 2 doctrine extraction
MAX_TOKENS = 2000
MAX_CHARS = int(MAX_TOKENS * 3.5)  # ~7000 chars per chunk

# ============================================================
# Phase 3.5 Optimization (Minister Conversion)
# ============================================================
SKIP_PHASE_35_IF_CONVERTED = True  # Skip if already converted (checkpoint recovery)
ATOMIC_JSON_WRITES = True  # Use atomic writes to prevent JSON corruption

# ============================================================
# Cache Configuration
# ============================================================
CACHE_DIR = os.path.join("rag_cache", "llm")
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================================================
# Doctrine Domain Configuration
# ============================================================
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

DOMAIN_KEYWORDS = {
    "adaptation": ["adapt", "adaptation", "adaptable"],
    "base": ["base", "ground", "position"],
    "conflict": ["conflict", "fight", "battle", "combat"],
    "constraints": ["limit", "constraint", "constraint"],
    "data": ["intelligence", "data", "information", "intel"],
    "diplomacy": ["diplomacy", "negotiat", "treaty"],
    "discipline": ["discipline", "order", "training"],
    "executor": ["execute", "executor", "implement"],
    "legitimacy": ["legitimacy", "legitimize", "authority"],
    "optionality": ["option", "optional", "choices"],
    "power": ["power", "force", "strength", "army"],
    "psychology": ["moral", "morale", "psych", "fear", "confidence"],
    "registry": ["register", "record", "registry"],
    "risk": ["risk", "danger", "hazard", "loss"],
    "strategy": ["strategy", "strategic", "plan", "planning"],
    "technology": ["technology", "tech", "weapon", "armament"],
    "timing": ["time", "timing", "tempo", "speed"],
    "truth": ["truth", "fact", "verify", "verify"],
}

CHAPTER_TYPES = {
    "doctrinal",
    "narrative",
    "historical",
    "introductory",
    "transitional",
    "commentary",
    "appendix",
    "summary",
}

# ============================================================
# Prompt Templates
# ============================================================
PHASE1_SYSTEM_PROMPT = """
You are a deterministic book-structure parser.

Your ONLY task is to detect chapter boundaries.

You will receive text incrementally.
You must decide ONE of the following exact values:

- start_new_chapter
- continue_chapter
- end_chapter

STRICT OUTPUT REQUIREMENTS (READ CAREFULLY):
- You MUST return ONLY a single JSON object and NOTHING else (no commentary,
    no markdown, no explanation, no code fences).
- The JSON object MUST exactly match this structure:
    {"decision": "start_new_chapter" | "continue_chapter" | "end_chapter", "confidence": 0.0}
- Use the lowercase decision strings shown above exactly.
- Set "confidence" to a float between 0.0 and 1.0. If unsure, return 0.0.
- If you cannot follow these rules, return {"decision": "continue_chapter", "confidence": 0.0}.

RULES:
- Do NOT summarize, interpret, or invent content.
- Do NOT quote or copy large verbatim passages.
- Do NOT reorder text.
- Be deterministic: prefer conservative choices when uncertain.

Return ONLY valid JSON.
"""

SYSTEM_PROMPT_DOCTRINE = f"""
You are an operational doctrine extraction engine.

Your task is to EXTRACT actionable operational guidance from text.
Not to quote verbatim, but to ABSTRACT principles, rules, decision criteria, warnings, and claims.

MANDATORY OUTPUT REQUIREMENTS:
- You MUST include a field called "domains".
- "domains" MUST be a list of 1 to 3 items.
- Each domain MUST be chosen ONLY from the list below.
- If no domain applies, choose the closest applicable domain.

ALLOWED DOMAINS (EXACT STRINGS):
{', '.join(ALLOWED_DOMAINS)}

EXTRACTION GUIDELINES:
1. A PRINCIPLE is a fundamental truth, maxim, or foundation for action (e.g., "reputation is built over time").
2. A RULE is a prescriptive action, constraint, or decision criterion (e.g., "never engage without understanding opponent intentions").
3. A CLAIM is a factual assertion made by the text (e.g., "wealth compounds over time").
4. A WARNING is a cautionary statement or risk indicator (e.g., "acting without patience leads to failure").

EXTRACTION RULES:
- Generalize language: convert specific examples into abstract principles.
- DO NOT quote sentences verbatim; paraphrase into normalized language.
- DO NOT quote phrases longer than 10 consecutive words from the original.
- Focus on *operational content*: advice, decision rules, risk factors, foundational beliefs.
- Ignore: plot summaries, character development, literary flourishes, meta-commentary.

WHEN TO EXTRACT:
- ANY clear guidance, advice, lesson, or principle = EXTRACT.
- ANY operational decision rule or constraint = EXTRACT.
- ANY risk, warning, or caution = EXTRACT.
- Anything implied by the narrative or examples = EXTRACT.

MINIMIZE EMPTY FIELDS:
- If the text contains ANY actionable content, extract SOMETHING into each field.
- If no explicit rules, infer rules from the principles or examples.
- If no explicit warnings, infer warnings from risks or negative outcomes mentioned.
- Prefer over-extraction to under-extraction.

Return ONLY valid JSON matching the schema. Do not include commentary.
"""