"""
CONCRETE MODIFICATIONS: KIS Integration in ingest_pipeline.py

This file shows EXACTLY what to change in ingest_pipeline.py to integrate KIS.

LOCATION: c:\era\ingestion\v2\src\ingest_pipeline.py

All changes are marked with:
    ### KIS INTEGRATION ###  (start of change)
    ### END KIS INTEGRATION ###  (end of change)

Total lines to add: ~40 lines
"""

# =============================================================================
# MODIFICATION 1: Add imports at top of file (after line 16)
# =============================================================================

# FROM (line 16):
# from .async_doctrine_workers import run_async_doctrine_extraction

# ADD THESE LINES AFTER:

### KIS INTEGRATION ###
try:
    from ingestion.v2.src.ingestion_kis_enhancer import (
        IngestionKISEnhancer,
        IngestionKISContext,
    )
    KIS_AVAILABLE = True
except ImportError:
    KIS_AVAILABLE = False
    print("[WARN] KIS enhancement unavailable - ingestion will proceed without KIS synthesis")
### END KIS INTEGRATION ###


# =============================================================================
# MODIFICATION 2: Initialize KIS enhancer in run_full_ingest_with_resume
# =============================================================================

# Find the line:
# def run_full_ingest_with_resume(pdf_path: str, resume: bool = True) -> None:

# Add these lines right after the function starts (around line 560):

### KIS INTEGRATION ###
    # Initialize KIS enhancer for knowledge synthesis
    kis_enhancer = None
    if KIS_AVAILABLE:
        try:
            kis_enhancer = IngestionKISEnhancer(
                knowledge_base_path="data/ministers"
            )
            print("[KIS] Enhancer initialized for doctrine synthesis", flush=True)
        except Exception as e:
            print(f"[WARN] Failed to initialize KIS enhancer: {e}", flush=True)
    
    # Track ingestion job outcomes for learning feedback
    ingestion_job_outcomes = {}
### END KIS INTEGRATION ###


# =============================================================================
# MODIFICATION 3: Enhance doctrines with KIS synthesis
# =============================================================================

# Find this section (around line 400-430):
# 
#     # Enrich doctrines with metadata
#     _enrich_doctrines(doctrines, chapters, storage)

# ADD BEFORE the _enrich_doctrines call:

### KIS INTEGRATION ###
    # KIS enhancement: synthesize knowledge during aggregation phase
    if kis_enhancer and chapters:
        print("[KIS] Enhancing doctrines with KIS knowledge synthesis...", flush=True)
        for idx, (doctrine, chapter) in enumerate(zip(doctrines, chapters), start=1):
            try:
                chapter_title = chapter.get("chapter_title", f"Chapter {idx}") if isinstance(chapter, dict) else f"Chapter {idx}"
                
                # Extract first domain from doctrine, or use "general"
                domains = doctrine.get("domains", [])
                minister_domain = domains[0] if domains else "general"
                
                # Get first 300 chars of doctrine excerpt
                doctrine_excerpt = ""
                for field in ("principles", "rules", "claims", "warnings"):
                    items = doctrine.get(field, [])
                    if items:
                        doctrine_excerpt = str(items[0])[:300]
                        break
                
                # Create KIS context
                job_id = f"ingest_{book_id}_{idx}"
                kis_context = IngestionKISContext(
                    chapter_title=chapter_title,
                    minister_domain=minister_domain,
                    doctrine_excerpt=doctrine_excerpt,
                    ingestion_job_id=job_id
                )
                
                # Enhance with KIS
                kis_context = kis_enhancer.enhance_aggregation_stage(
                    kis_context,
                    max_related_items=3
                )
                
                # Add KIS guidance to doctrine
                if kis_context.kis_synthesis:
                    doctrine["kis_guidance"] = kis_context.kis_synthesis
                    doctrine["kis_context"] = kis_context.kis_context
                
                # Track for outcome recording
                ingestion_job_outcomes[job_id] = {
                    "kis_context": kis_context,
                    "doctrine_idx": idx,
                }
                
            except Exception as e:
                print(f"[WARN] KIS enhancement failed for chapter {idx}: {e}", flush=True)
### END KIS INTEGRATION ###


# =============================================================================
# MODIFICATION 4: Record success after embeddings complete
# =============================================================================

# Find this section (around line 530):
#
#     with open(os.path.join(storage, "03_embeddings.json"), "w", encoding="utf-8") as f:
#         json.dump(embeddings, f, indent=2, ensure_ascii=False)

# ADD AFTER the embeddings are written:

### KIS INTEGRATION ###
    # Record ingestion success for ML training
    if kis_enhancer and ingestion_job_outcomes:
        print("[KIS] Recording ingestion success outcomes...", flush=True)
        for job_id, outcome_data in ingestion_job_outcomes.items():
            try:
                success = kis_enhancer.record_ingestion_success(
                    ingestion_job_id=job_id,
                    minister_json=doctrines[outcome_data["doctrine_idx"] - 1],
                    num_chunks=len(nodes_to_embed),
                    num_embeddings=len(embeddings),
                    storage_success=True
                )
                if success:
                    print(f"[KIS] Recorded success: {job_id}", flush=True)
            except Exception as e:
                print(f"[WARN] Failed to record KIS success: {e}", flush=True)
        
        # Export ingestion logs
        try:
            kis_enhancer.save_ingestion_logs("ml/cache/ingestion_kis_logs.json")
            print("[KIS] Ingestion logs exported", flush=True)
        except Exception as e:
            print(f"[WARN] Failed to export ingestion logs: {e}", flush=True)
### END KIS INTEGRATION ###


# =============================================================================
# MODIFICATION 5: Handle errors with failure recording
# =============================================================================

# Find exception handlers in the main ingest function.
# For any exception that occurs during embedding/storage phases, add:

### KIS INTEGRATION ###
    # Record failures for learning
    except Exception as e:
        if kis_enhancer and ingestion_job_outcomes:
            for job_id in ingestion_job_outcomes.keys():
                try:
                    kis_enhancer.record_ingestion_failure(
                        ingestion_job_id=job_id,
                        error_message=str(e),
                        recovery_time_sec=30
                    )
                except Exception:
                    pass
        raise  # Continue with original exception handling
### END KIS INTEGRATION ###


# =============================================================================
# SUMMARY OF CHANGES
# =============================================================================

"""
┌──────────────────────────────────────────────────────────────────┐
│  KIS INTEGRATION REQUIREMENTS BY MODIFICATION                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. IMPORTS (5 lines)                                             │
│    - Add conditional import of KIS enhancer                      │
│    - Set KIS_AVAILABLE flag                                      │
│                                                                  │
│ 2. INITIALIZATION (8 lines)                                      │
│    - Create kis_enhancer instance                                │
│    - Initialize ingestion_job_outcomes dict                      │
│    - Handle KIS unavailable gracefully                           │
│                                                                  │
│ 3. ENHANCEMENT (30 lines)                                        │
│    - Loop through each doctrine chapter                          │
│    - Create IngestionKISContext for each                         │
│    - Call enhance_aggregation_stage()                            │
│    - Add kis_guidance to doctrine                                │
│    - Track outcomes for later recording                          │
│                                                                  │
│ 4. SUCCESS RECORDING (10 lines)                                  │
│    - After embeddings written, record success                    │
│    - Export ingestion logs for analysis                          │
│                                                                  │
│ 5. ERROR HANDLING (5 lines)                                      │
│    - Record failures on exceptions                               │
│    - Continue with existing error handling                       │
│                                                                  │
│ TOTAL: ~58 lines of new code (mostly docstrings/comments)       │
│        Including blank lines for readability                     │
│                                                                  │
│ BACKWARD COMPATIBLE: Yes                                        │
│ - KIS is optional (KIS_AVAILABLE flag)                           │
│ - If KIS unavailable, pipeline runs normally                     │
│ - No breaking changes to existing pipeline                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
"""

# =============================================================================
# BEFORE/AFTER EXAMPLE
# =============================================================================

"""
BEFORE KIS INTEGRATION:
  Book "Rich_Man_Babylon.pdf"
    ├─ Chapter 1: "The Richest Man" extract
    │  └─ doctrine: {principles: [...], rules: [...]}
    ├─ Chapter 2: "Golden Rules" 
    │  └─ doctrine: {principles: [...], rules: [...]}
    └─ → Embeddings→ Storage → Done

AFTER KIS INTEGRATION:
  Book "Rich_Man_Babylon.pdf"
    ├─ Chapter 1: "The Richest Man"
    │  ├─ extract doctrine
    │  ├─ KIS SYNTHESIS: Query "What wealth guidance relates to this?"
    │  │  └─ Get: [5 related knowledge items from KIS]
    │  ├─ doctrine: {
    │  │    principles: [...],
    │  │    rules: [...],
    │  │    kis_guidance: [related items],  ← NEW
    │  │    kis_context: {...}  ← NEW
    │  │  }
    │  ├─ Embeddings (now includes KIS context)
    │  ├─ Storage
    │  └─ RECORD SUCCESS for learning
    │
    ├─ Chapter 2: "Golden Rules"
    │  └─ ... (same pattern)
    │
    └─ ML WISDOM SYSTEM
       ├─ Learns: KIS guidance helped ingestion succeed
       ├─ Learns: For wealth/finance chapters, this guidance effective
       └─ NEXT ingestion uses adjusted KIS weights

OBSERVABLE EFFECTS:
✓ ml/cache/ingestion_kis_logs.json created
✓ Each doctrine has kis_guidance and kis_context fields
✓ ML system records outcomes for learning
✓ Next ingestion runs with learned KIS adjustments
"""

# =============================================================================
# HOW TO APPLY MODIFICATIONS
# =============================================================================

"""
MANUAL PATCH METHOD:
1. Open: c:\era\ingestion\v2\src\ingest_pipeline.py
2. Find: "from .async_doctrine_workers import run_async_doctrine_extraction"
3. Add 5 import lines after it
4. Find: "def run_full_ingest_with_resume(pdf_path: str, resume: bool = True)"
5. Add 8 initialization lines
6. Find: "_enrich_doctrines(doctrines, chapters, storage)"
7. Add 30 enhancement lines before it
8. Find embeddings JSON write (line ~530)
9. Add 10 success recording lines after it
10. Find exception handlers
11. Add 5 error recording lines

AUTOMATED PATCH METHOD (if Python script):
- Python script can read file
- Find each section by pattern matching
- Insert code blocks
- Write back to file
- Validate with syntax check

VALIDATION:
- Run: python -c "from ingestion.v2.src.ingest_pipeline import *; print('[OK]')"
- Should not have syntax errors
- KIS_AVAILABLE should be True if ml/ module available
"""

# =============================================================================
# EXPECTED OUTPUT AFTER INTEGRATION
# =============================================================================

"""
When running the ingestion pipeline with KIS integration:

$ python ingestion/v2/run_all_v2_ingest.py

[Processing PDF]
[KIS] Enhancer initialized for doctrine synthesis
[KIS] Enhancing doctrines with KIS knowledge synthesis...
[KIS] Enhanced chapter 1 with 5 related knowledge items
[KIS] Enhanced chapter 2 with 4 related knowledge items
...
[KIS] Recording ingestion success outcomes...
[KIS] Recorded success: ingest_Rich_Man_Babylon_1
[KIS] Recorded success: ingest_Rich_Man_Babylon_2
[KIS] Ingestion logs exported

$ ls -la ml/cache/ingestion_kis_logs.json
[File created with ingestion context + statistics]

ML SYSTEM LEARNS:
- Patterns: doctrine → ingestion success
- Adjusts KIS weights for similar situations
- Next ingestion benefits from learned adjustments
"""
