# Plan B — Ingestion Overhaul
**Date:** 2026-05-18
**Scope:** Replace three stub implementations with real LLM extraction, real embeddings, and semantic retrieval
**Goal:** Ministers receive semantically relevant knowledge, not keyword-matched text — independent of model quality

---

## Problem

ERA's knowledge layer has three silent stubs that make it appear functional while delivering degraded results:

| File | Stub Behavior | Impact |
|------|--------------|--------|
| `ingestion/v2/src/doctrine_extractor.py` | Keyword heuristics only, returns empty principles/rules/claims/warnings | Ministers get no structured knowledge |
| `ingestion/v2/src/embeddings.py:embed_nodes()` | Returns zero vectors `[0.0] * 8` | No semantic similarity possible |
| `persona/knowledge_engine.py:synthesize_knowledge()` | Pure keyword scoring | Retrieval misses semantically relevant entries |

---

## Architecture

```
PDF → pages (unchanged)
    → chapters (unchanged, v1 LLM splitter)
    → [FIX] extract_doctrine()  ← real LLM extraction
    → [FIX] embed_nodes()       ← real Ollama embeddings (nomic-embed-text)
    → JSON storage              ← unchanged structure, adds "embedding": float[]

knowledge_engine.synthesize_knowledge()
    → [FIX] embed query once → cosine similarity ranking
    → 5-factor KIS weights applied on top of semantic scores (unchanged)
    → query embedding cache per session (avoid re-embedding same query)
```

---

## Components

### 1. Real Doctrine Extraction — `ingestion/v2/src/doctrine_extractor.py`

**Replace:** keyword heuristic stub

**New behavior:** LLM prompt given chapter text, returns structured doctrine

Prompt structure:
```
You are extracting structured knowledge from a book chapter.
Given the chapter text below, extract:
- principles: fundamental truths or beliefs stated in the text
- rules: specific behavioral directives or guidelines
- claims: assertions made about the world or outcomes
- warnings: risks, dangers, or cautionary statements
- domains: which domains apply (risk, strategy, power, diplomacy, psychology, etc.)

Output ONLY valid JSON:
{
  "principles": ["..."],
  "rules": ["..."],
  "claims": ["..."],
  "warnings": ["..."],
  "domains": ["..."]
}
```

- Uses `OllamaClient` (already in `ingestion/v2/src/ollama_client.py`)
- Uses `PROGRAM_MODEL` (analyze model) — same as minister analysis
- Falls back to current heuristic if LLM call fails (safe degradation, no crash)
- Same JSON retry pattern as Plan A (1 retry on parse failure)

### 2. Real Embeddings — `ingestion/v2/src/embeddings.py`

**Replace:** `embed_nodes()` zero-vector stub

**New behavior:** Call `ollama.embeddings(model=embed_model, prompt=content)` per node

- Model: `nomic-embed-text` (768-dim, fast, runs locally on Ollama)
- Configurable via `EMBED_MODEL` env var (default: `nomic-embed-text`)
- Stored as `"embedding": [float, ...]` in existing JSON node structure
- Batch with `MAX_EMBED_CONCURRENCY` (already defined in `async_ingest_config.py`)
- Falls back to zero vector if Ollama unavailable (skip_check mode)

**Dimension note:** Current stub uses 8-dim zeros. Real embeddings are 768-dim. Existing stored indexes must be re-ingested after this change.

### 3. Semantic Retrieval — `persona/knowledge_engine.py`

**Replace:** `extract_keywords()` + keyword scoring in `synthesize_knowledge()`

**New behavior:** Cosine similarity over stored embeddings

```python
def cosine_similarity(a: list[float], b: list[float]) -> float:
    # pure numpy — no new dependencies
    ...

def synthesize_knowledge(situation, domains, ...):
    query_vec = _embed_query(situation)  # cached per session
    for entry in all_entries:
        sem_score = cosine_similarity(query_vec, entry["embedding"])
        # existing 5-factor KIS weights applied on top
        final_score = sem_score * domain_w * type_w * memory_w * context_w * goal_w
    return top_k_by_final_score
```

**Query embedding cache:** `dict[str, list[float]]` keyed by `sha256(situation_text)` — prevents re-embedding the same situation across 5–18 ministers in one deliberation round.

**Fallback:** If entry has no embedding or zero vector, fall back to keyword scoring for that entry only.

---

## Files Changed

| File | Change |
|------|--------|
| `ingestion/v2/src/doctrine_extractor.py` | Replace stub with real LLM extraction + retry |
| `ingestion/v2/src/embeddings.py` | Replace `embed_nodes()` stub with Ollama embeddings |
| `persona/knowledge_engine.py` | Add cosine similarity, query embedding, semantic ranking |

---

## Migration Note

All existing ingested books must be **re-ingested** after Plan B lands — zero-vector indexes are incompatible with semantic retrieval. The `_is_ingest_completed()` check uses `progress.json`; delete or reset it per book to trigger re-ingestion.

---

## Non-Goals

- No change to ChromaDB (already present but adds operational complexity — skip for now)
- No change to chapter splitter or PDF extraction
- No change to minister prompts (Plan A)
- No change to JSON storage structure (only `embedding` field added)
- No new Python packages beyond numpy (already required)

---

## Success Criteria

- `extract_doctrine()` returns non-empty principles/rules/claims for typical book chapters
- `embed_nodes()` stores 768-dim float arrays, not zeros
- `synthesize_knowledge()` returns semantically relevant entries (not just keyword matches)
- Query embedding cache hits on second+ minister call in same deliberation
- Re-ingestion of one book completes without error
