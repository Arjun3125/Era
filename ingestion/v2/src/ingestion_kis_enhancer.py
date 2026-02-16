"""
Ingestion Pipeline KIS Integration Layer

Connects the async ingestion pipeline (Phase 3.5) with the ML Wisdom System.

The ingestion pipeline processes doctrine books:
1. CHUNKING: Split documents into knowledge units
2. EMBEDDING: Create semantic vectors
3. AGGREGATION: ← Use KIS to enhance minister context
4. STORAGE: Save to pgvector with attribution

KIS Integration:
- During aggregation: Synthesize knowledge about each doctrine piece
- Query "What guidance applies to this minister doctrine?"
- Enhance minister JSON with KIS-ranked knowledge context
- Track ingestion success for learning feedback
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# Add parent paths for imports
# ingestion_kis_enhancer.py is in c:\era\ingestion\v2\src\
# We need to reach c:\era\ to import ml module
era_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, era_root)

print(f"[KIS] Adding to sys.path: {era_root}", flush=True)

try:
    from ml.kis.knowledge_integration_system import (
        KnowledgeIntegrationSystem, KISRequest
    )
    from ml.ml_orchestrator import MLWisdomOrchestrator
except ImportError as e:
    print(f"[WARN] Failed to import ML modules: {e}", flush=True)
    print(f"[DEBUG] sys.path = {sys.path}", flush=True)
    raise


logger = logging.getLogger(__name__)


class IngestionKISContext:
    """
    Context for KIS-enhanced document processing during ingestion.
    
    Passed through the ingestion pipeline stages to enrich documents with
    KIS-synthesized knowledge context.
    """
    
    def __init__(
        self,
        chapter_title: str,
        minister_domain: str,
        doctrine_excerpt: str,
        ingestion_job_id: str
    ):
        """
        Initialize ingestion context.
        
        Args:
            chapter_title: Title of doctrine chapter
            minister_domain: Minister domain (career_risk, optionality, etc.)
            doctrine_excerpt: The doctrine text being processed
            ingestion_job_id: ID from async ingestion orchestrator
        """
        self.chapter_title = chapter_title
        self.minister_domain = minister_domain
        self.doctrine_excerpt = doctrine_excerpt
        self.ingestion_job_id = ingestion_job_id
        
        # Will be populated during aggregation
        self.kis_synthesis = None
        self.kis_context = None
        self.processing_timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_title": self.chapter_title,
            "minister_domain": self.minister_domain,
            "doctrine_excerpt": self.doctrine_excerpt,
            "ingestion_job_id": self.ingestion_job_id,
            "kis_synthesis": self.kis_synthesis,
            "kis_context": self.kis_context,
            "processing_timestamp": self.processing_timestamp,
        }


class IngestionKISEnhancer:
    """
    Enhances document ingestion with KIS synthesis.
    
    Used during the AGGREGATION stage to:
    1. Synthesize knowledge about the doctrine excerpt
    2. Rank related guidance
    3. Add KIS context to minister doctrine JSON
    4. Enable outcome feedback for learning
    """
    
    def __init__(
        self,
        kis_engine: Optional[KnowledgeIntegrationSystem] = None,
        orchestrator: Optional[MLWisdomOrchestrator] = None,
        knowledge_base_path: str = "data/ministers"
    ):
        """
        Initialize the KIS enhancer.
        
        Args:
            kis_engine: KIS instance
            orchestrator: ML orchestrator for tracking
            knowledge_base_path: Where knowledge is stored
        """
        self.kis_engine = kis_engine or KnowledgeIntegrationSystem(base_path=knowledge_base_path)
        self.orchestrator = orchestrator or MLWisdomOrchestrator(kis_engine=self.kis_engine)
        self.knowledge_base_path = knowledge_base_path
        
        # Track ingestion jobs
        self.ingestion_contexts: Dict[str, IngestionKISContext] = {}
        
        logger.info("IngestionKISEnhancer initialized")
    
    def enhance_aggregation_stage(
        self,
        context: IngestionKISContext,
        max_related_items: int = 5
    ) -> IngestionKISContext:
        """
        Enhance document during aggregation stage.
        
        Synthesizes knowledge relevant to the doctrine excerpt,
        adds context to the ingestion context for downstream use.
        
        Args:
            context: Ingestion context with chapter/domain/excerpt
            max_related_items: Max related knowledge items
        
        Returns:
            Enhanced context with kis_synthesis and kis_context
        """
        
        # Build query for KIS
        query = f"""
        Minister Domain: {context.minister_domain}
        Chapter: {context.chapter_title}
        Doctrine Excerpt: {context.doctrine_excerpt[:200]}
        
        What existing guidance applies to this doctrine?
        """
        
        # Synthesize knowledge
        request = KISRequest(
            user_input=query,
            active_domains=[context.minister_domain],
            domain_confidence={context.minister_domain: 0.9},
            max_items=max_related_items
        )
        
        try:
            kis_result = self.kis_engine.synthesize_knowledge(request)
            
            # Populate context
            context.kis_synthesis = kis_result.synthesized_knowledge
            context.kis_context = {
                "knowledge_trace": kis_result.knowledge_trace,
                "quality": kis_result.knowledge_quality,
                "debug": kis_result.knowledge_debug,
            }
            
            logger.info(
                f"Enhanced ingestion {context.ingestion_job_id}: "
                f"{len(kis_result.synthesized_knowledge)} related knowledge items"
            )
            
        except Exception as e:
            logger.error(f"KIS synthesis failed during aggregation: {e}")
            context.kis_context = {"error": str(e)}
        
        # Cache for tracking
        self.ingestion_contexts[context.ingestion_job_id] = context
        
        return context
    
    def enhance_minister_doctrine(
        self,
        minister_json: Dict[str, Any],
        context: IngestionKISContext
    ) -> Dict[str, Any]:
        """
        Add KIS context to minister doctrine JSON.
        
        Enriches the minister JSON with:
        - Related knowledge guidance
        - Knowledge trace (source attribution)
        - Quality metrics
        
        Args:
            minister_json: Minister doctrine JSON
            context: Ingestion context with KIS synthesis
        
        Returns:
            Enhanced minister JSON with kis_guidance section
        """
        
        if not context.kis_context:
            return minister_json
        
        # Add KIS guidance section
        minister_json["kis_guidance"] = {
            "synthesized_knowledge": context.kis_synthesis or [],
            "knowledge_trace": context.kis_context.get("knowledge_trace", []),
            "quality": context.kis_context.get("quality", {}),
            "ingestion_timestamp": context.processing_timestamp,
        }
        
        logger.info(f"Added KIS guidance to minister doctrine")
        
        return minister_json
    
    def record_ingestion_success(
        self,
        ingestion_job_id: str,
        minister_json: Dict[str, Any],
        num_chunks: int,
        num_embeddings: int,
        storage_success: bool
    ) -> bool:
        """
        Record successful ingestion for training feedback.
        
        Args:
            ingestion_job_id: ID of ingestion job
            minister_json: Final minister JSON stored
            num_chunks: Number of chunks created
            num_embeddings: Number of embeddings created
            storage_success: Whether storage succeeded
        
        Returns:
            True if recorded for training
        """
        
        if ingestion_job_id not in self.ingestion_contexts:
            logger.warning(f"Context not found: {ingestion_job_id}")
            return False
        
        context = self.ingestion_contexts[ingestion_job_id]
        
        # Record in orchestrator as successful decision
        decision_id = len(self.orchestrator.decisions_log) - 1
        
        success = self.orchestrator.record_outcome(
            decision_id=decision_id,
            success=storage_success,
            regret_score=0.0 if storage_success else 0.5,
            recovery_time_days=0
        )
        
        logger.info(
            f"Recorded ingestion success: {ingestion_job_id} - "
            f"{num_chunks} chunks, {num_embeddings} embeddings"
        )
        
        return success
    
    def record_ingestion_failure(
        self,
        ingestion_job_id: str,
        error_message: str,
        recovery_time_sec: int = 0
    ) -> bool:
        """
        Record failed ingestion for learning.
        
        Args:
            ingestion_job_id: ID of ingestion job
            error_message: What went wrong
            recovery_time_sec: Time to recover/retry
        
        Returns:
            True if recorded for training
        """
        
        if ingestion_job_id not in self.ingestion_contexts:
            logger.warning(f"Context not found for failure: {ingestion_job_id}")
            return False
        
        context = self.ingestion_contexts[ingestion_job_id]
        decision_id = len(self.orchestrator.decisions_log) - 1
        
        # Record failure for learning
        success = self.orchestrator.record_outcome(
            decision_id=decision_id,
            success=False,
            regret_score=0.7,
            recovery_time_days=max(1, recovery_time_sec // 86400)
        )
        
        logger.info(f"Recorded ingestion failure: {ingestion_job_id} - {error_message}")
        
        return success
    
    def get_ingestion_statistics(self) -> Dict[str, Any]:
        """
        Get statistics on KIS-enhanced ingestions.
        """
        
        contexts = self.ingestion_contexts.values()
        
        total_ingestions = len(contexts)
        enhanced_ingestions = sum(1 for c in contexts if c.kis_context)
        total_knowledge_items = sum(
            len(c.kis_synthesis or []) for c in contexts
        )
        
        return {
            "total_ingestions": total_ingestions,
            "enhanced_with_kis": enhanced_ingestions,
            "enhancement_rate": enhanced_ingestions / max(total_ingestions, 1),
            "total_knowledge_items_synthesized": total_knowledge_items,
            "avg_items_per_ingestion": total_knowledge_items / max(enhanced_ingestions, 1),
        }
    
    def save_ingestion_logs(self, filepath: str) -> bool:
        """
        Export ingestion KIS contexts to JSON.
        """
        
        try:
            with open(filepath, 'w') as f:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "ingestion_contexts": {
                        k: v.to_dict() for k, v in self.ingestion_contexts.items()
                    },
                    "statistics": self.get_ingestion_statistics(),
                }
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported ingestion logs to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export ingestion logs: {e}")
            return False


# ============================================================================
# INTEGRATION WITH ASYNC INGESTION ORCHESTRATOR
# ============================================================================

def create_kis_enhanced_worker_wrapper(
    worker_func,
    kis_enhancer: IngestionKISEnhancer,
    stage_name: str
):
    """
    Wrap an ingestion worker to add KIS enhancement.
    
    Example usage in async_ingestion_orchestrator.py:
    
    ```python
    kis_enhancer = IngestionKISEnhancer()
    
    aggregate_worker = create_kis_enhanced_worker_wrapper(
        original_aggregate_worker,
        kis_enhancer,
        "aggregation"
    )
    ```
    """
    
    async def enhanced_worker(*args, **kwargs):
        """Wrapped worker with KIS enhancement."""
        
        # Call original worker
        result = await worker_func(*args, **kwargs)
        
        # If aggregation stage, enhance with KIS
        if stage_name == "aggregation" and result.get("success"):
            # Extract context if available
            ingestion_job_id = kwargs.get("job_id") or result.get("job_id")
            
            if ingestion_job_id:
                logger.info(f"Enhancing aggregation with KIS for job {ingestion_job_id}")
        
        return result
    
    return enhanced_worker


if __name__ == "__main__":
    # Test the enhancer
    print("\n[...] Initializing IngestionKISEnhancer...")
    enhancer = IngestionKISEnhancer()
    
    print("[OK] Enhancer initialized")
    
    # Example: Process a doctrine chapter
    context = IngestionKISContext(
        chapter_title="Risk Management in Irreversible Decisions",
        minister_domain="career_risk",
        doctrine_excerpt="Always ensure financial buffers before irreversible decisions...",
        ingestion_job_id="ingest_001"
    )
    
    print(f"[...] Enhancing aggregation for {context.ingestion_job_id}...")
    context = enhancer.enhance_aggregation_stage(context)
    
    print(f"[OK] Enhanced with {len(context.kis_synthesis or [])} knowledge items")
    
    # Example: Enhance minister JSON
    minister_json = {
        "minister_id": "risk_001",
        "domain": "career_risk",
        "doctrine": "Financial prudence is primary guard",
    }
    
    enhanced_json = enhancer.enhance_minister_doctrine(minister_json, context)
    print(f"[OK] Enhanced minister JSON with KIS guidance")
    
    # Record success
    enhancer.record_ingestion_success(
        ingestion_job_id="ingest_001",
        minister_json=enhanced_json,
        num_chunks=25,
        num_embeddings=25,
        storage_success=True
    )
    print("[OK] Recorded ingestion success for training")
    
    # Get statistics
    stats = enhancer.get_ingestion_statistics()
    print(f"\n[OK] Ingestion Statistics:")
    for k, v in stats.items():
        print(f"     {k}: {v}")
    
    # Export logs
    enhancer.save_ingestion_logs("ml/cache/ingestion_kis_logs.json")
    print("[OK] Logs exported to ml/cache/ingestion_kis_logs.json")
