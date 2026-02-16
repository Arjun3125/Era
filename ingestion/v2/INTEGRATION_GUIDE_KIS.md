"""
Integration Guide: KIS with Async Ingestion Pipeline

Complete step-by-step instructions for integrating IngestionKISEnhancer
with the AsyncIngestionOrchestrator in run_all_v2_ingest.py.

LOCATION OF CHANGES:
- File: ingestion/v2/run_all_v2_ingest.py
- Changes: 4 specific locations
- Lines affected: ~30-40 lines total across the file
"""

# =============================================================================
# STEP 1: ADD IMPORTS (at top of run_all_v2_ingest.py)
# =============================================================================

# Add these imports after existing imports:
from ingestion.v2.src.ingestion_kis_enhancer import (
    IngestionKISEnhancer,
    IngestionKISContext,
)


# =============================================================================
# STEP 2: INITIALIZE KIS ENHANCER (in AsyncIngestionOrchestrator.__init__)
# =============================================================================

# In the AsyncIngestionOrchestrator class, add to __init__:

class AsyncIngestionOrchestrator:
    def __init__(self):
        # ... existing initialization ...
        
        # Initialize KIS enhancer for knowledge synthesis during ingestion
        self.kis_enhancer = IngestionKISEnhancer(
            knowledge_base_path="data/ministers"
        )
        
        # Track ingestion decision → outcome mapping
        self.ingestion_outcomes: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# STEP 3: ENHANCE AGGREGATION STAGE
# =============================================================================

# In the aggregation_worker method, add KIS enhancement:

async def aggregation_worker(self, job_queue):
    """
    Enhanced aggregation worker with KIS synthesis.
    """
    while True:
        job_data = await job_queue.get()
        
        if job_data is None:  # Shutdown signal
            break
        
        try:
            job_id = job_data["job_id"]
            chapter_title = job_data.get("chapter_title", "Unknown")
            minister_domain = job_data.get("minister_domain", "general")
            doctrine_excerpt = job_data.get("document_text", "")[:300]  # First 300 chars
            
            # CREATE KIS CONTEXT
            kis_context = IngestionKISContext(
                chapter_title=chapter_title,
                minister_domain=minister_domain,
                doctrine_excerpt=doctrine_excerpt,
                ingestion_job_id=job_id
            )
            
            # ENHANCE WITH KIS
            kis_context = self.kis_enhancer.enhance_aggregation_stage(
                kis_context,
                max_related_items=5
            )
            
            logger.info(
                f"Aggregation enhanced with KIS: {len(kis_context.kis_synthesis or [])} "
                f"related knowledge items"
            )
            
            # Continue with existing aggregation logic
            # ...
            aggregated_data = {
                "job_id": job_id,
                "aggregated_document": job_data.get("document_text", ""),
                "kis_guidance": kis_context.kis_synthesis or [],
                "kis_context": kis_context.kis_context or {},
                # ... existing fields ...
            }
            
            await storage_job_queue.put(aggregated_data)
            
            # Track for outcome recording
            self.ingestion_outcomes[job_id] = {
                "stage": "aggregation",
                "kis_context": kis_context,
                "timestamp": datetime.now().isoformat(),
            }
            
            job_queue.task_done()
            
        except Exception as e:
            logger.error(f"Aggregation error: {e}")
            self.kis_enhancer.record_ingestion_failure(
                ingestion_job_id=job_data.get("job_id", "unknown"),
                error_message=str(e),
                recovery_time_sec=5
            )
            job_queue.task_done()


# =============================================================================
# STEP 4: TRACK SUCCESS IN STORAGE WRITER
# =============================================================================

# In the storage_writer method, add outcome recording:

async def storage_writer(self, storage_queue):
    """
    Enhanced storage writer with KIS outcome tracking.
    """
    while True:
        item = await storage_queue.get()
        
        if item is None:  # Shutdown signal
            break
        
        try:
            job_id = item.get("job_id")
            
            # Write to storage (existing logic)
            # ...
            
            # RECORD SUCCESS FOR TRAINING
            if job_id in self.ingestion_outcomes:
                outcome_data = self.ingestion_outcomes[job_id]
                
                success = self.kis_enhancer.record_ingestion_success(
                    ingestion_job_id=job_id,
                    minister_json=item.get("aggregated_document", {}),
                    num_chunks=item.get("num_chunks", 0),
                    num_embeddings=item.get("num_embeddings", 0),
                    storage_success=True
                )
                
                logger.info(f"Recorded ingestion success: {job_id}")
                
                # Clean up
                del self.ingestion_outcomes[job_id]
            
            storage_queue.task_done()
            
        except Exception as e:
            logger.error(f"Storage write error: {e}")
            
            # RECORD FAILURE FOR TRAINING
            job_id = item.get("job_id")
            if job_id in self.ingestion_outcomes:
                self.kis_enhancer.record_ingestion_failure(
                    ingestion_job_id=job_id,
                    error_message=str(e),
                    recovery_time_sec=10
                )
            
            storage_queue.task_done()


# =============================================================================
# STEP 5: EXPORT INGESTION LOGS (in cleanup or shutdown)
# =============================================================================

# Add to the main run() method or cleanup section:

async def run_with_kis_logging(self):
    """
    Run the ingestion pipeline with KIS learning enabled.
    """
    try:
        await self.run()  # Existing run logic
    finally:
        # Export ingestion logs for analysis
        self.kis_enhancer.save_ingestion_logs(
            "ml/cache/ingestion_kis_logs.json"
        )
        
        # Log final statistics
        stats = self.kis_enhancer.get_ingestion_statistics()
        logger.info(f"Ingestion KIS Stats: {json.dumps(stats, indent=2)}")


# =============================================================================
# STEP 6: DECISION → OUTCOME FEEDBACK LOOP
# =============================================================================

# This is how the ML system learns from ingestion:

"""
DECISION FLOW:
1. User requests doctrine ingestion for (e.g.) "career_risk" minister
2. DECISION: "Should we process this doctrine chapter?"
   - KIS synthesizes related knowledge
   - Aggregation worker enhances with context
   - ML system makes judgment (confidence, suitable?, constraints)

3. OUTCOME: Document is stored/processed
   - record_ingestion_success() logs success
   - OR record_ingestion_failure() logs failure with error
   
4. TRAINING: ML learns pattern
   - Situation: (doctrine type, minister domain, book chapter)
   - Outcome: Success/failure of ingestion
   - Learning: Adjust confidence in KIS judgments
   
EXPECTED LEARNING PATTERNS:
- If doctrine chapters from "The Richest Man in Babylon" ingested successfully
  → Learn: This source is trustworthy
- If ingestion fails on unstructured text
  → Learn: Unstructured text requires preprocessing
- If KIS guidance + aggregation increases downstream accuracy
  → Learn: KIS enhancement improves ingestion pipeline
"""

# Example from run_all_v2_ingest.py:

async def main():
    orchestrator = AsyncIngestionOrchestrator()
    
    # Run ingestion
    await orchestrator.run_with_kis_logging()
    
    # Print learning progress
    learning_summary = orchestrator.kis_enhancer.get_ingestion_statistics()
    print(f"""
    ╔════════════════════════════════════════════╗
    ║       KIS-ENHANCED INGESTION COMPLETE      ║
    ╠════════════════════════════════════════════╣
    │ Total Ingestions: {learning_summary['total_ingestions']}
    │ Enhanced with KIS: {learning_summary['enhanced_with_kis']}
    │ Enhancement Rate: {learning_summary['enhancement_rate']:.1%}
    │ Total Knowledge Synthesized: {learning_summary['total_knowledge_items_synthesized']}
    │ Avg Items/Ingestion: {learning_summary['avg_items_per_ingestion']:.1f}
    ╚════════════════════════════════════════════╝
    """)


# =============================================================================
# FILES TO CHECK/MODIFY
# =============================================================================

"""
1. ingestion/v2/run_all_v2_ingest.py
   - Add imports (STEP 1)
   - Initialize kis_enhancer in __init__ (STEP 2)
   - Modify aggregation_worker (STEP 3)
   - Modify storage_writer (STEP 4)
   - Add kis_logging to main (STEP 5)

2. ingestion/v2/src/ingestion_kis_enhancer.py
   - ALREADY CREATED (no changes needed)

3. ml/kis/knowledge_integration_system.py
   - Should already exist (no changes)

4. ml/ml_orchestrator.py
   - Should already exist (no changes)

5. Create ingestion/v2/src/__init__.py if missing
   - Add: from .ingestion_kis_enhancer import IngestionKISEnhancer, IngestionKISContext
"""

# =============================================================================
# EXPECTED DATA FLOW AFTER INTEGRATION
# =============================================================================

"""
User Input (Books/Doctrine)
    ↓
CHUNKING WORKER
    ↓
EMBEDDING WORKER
    ↓
AGGREGATION WORKER ← KIS SYNTHESIS ADDED HERE
    ├─ Create IngestionKISContext
    ├─ Query KIS for related guidance
    ├─ Enhance aggregated data with kis_guidance
    └─ Pass to storage with kis_context
    ↓
STORAGE WRITER ← OUTCOME RECORDING ADDED HERE
    ├─ Write aggregated data to pgvector
    ├─ Record success: kis_enhancer.record_ingestion_success()
    └─ ML system learns pattern
    ↓
ML WISDOM SYSTEM
    ├─ Groups outcome by (document_type, domain, book_source)
    ├─ Learns: adjust KIS confidence for similar situations
    └─ Next ingestion uses updated KIS weights
"""

# =============================================================================
# QUICK TEST: Does IngestionKISContext work?
# =============================================================================

if __name__ == "__main__":
    # Run the test at the bottom of ingestion_kis_enhancer.py:
    # python -c "from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISEnhancer; e = IngestionKISEnhancer(); print('[OK] Enhancer loaded')"
    
    # Or test directly:
    from ingestion.v2.src.ingestion_kis_enhancer import IngestionKISEnhancer
    
    enhancer = IngestionKISEnhancer()
    print("[OK] IngestionKISEnhancer successfully imported and initialized")
    print(f"[OK] KnowledgeIntegrationSystem available: {enhancer.kis_engine is not None}")
    print(f"[OK] MLWisdomOrchestrator available: {enhancer.orchestrator is not None}")
