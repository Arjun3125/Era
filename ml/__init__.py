"""
ML Wisdom System Package

Integrates Knowledge Integration System (KIS) with machine learning judgment priors
to enable wise decision-making that learns from consequences.

Main Components:
- KIS: Multi-factor knowledge scoring
- Features: Vectorization of situations
- Labels: Outcome-based training
- ML: Learned judgment priors
- LLM: Safe structured calls
- Orchestrator: End-to-end pipeline

Usage:
    from ml_orchestrator import MLWisdomOrchestrator
    from kis.knowledge_integration_system import KnowledgeIntegrationSystem
    
    kis = KnowledgeIntegrationSystem()
    orchestrator = MLWisdomOrchestrator(kis_engine=kis)
    result = orchestrator.process_decision("Should I quit my job?")
"""

__version__ = "1.0.0"
__author__ = "ERA ML Team"

from .kis.knowledge_integration_system import (
    KnowledgeIntegrationSystem,
    KISRequest,
    KISResult,
)

from .features.feature_extractor import (
    build_feature_vector,
    SituationState,
    ConstraintState,
    KISOutput,
)

from .labels.label_generator import (
    generate_type_weights,
    TypeWeights,
)

from .judgment.ml_judgment_prior import (
    MLJudgmentPrior,
)

from .llm_handshakes.llm_interface import (
    LLMInterface,
    SituationFrameOutput,
    ConstraintExtractionOutput,
)

from .ml_orchestrator import (
    MLWisdomOrchestrator,
)

__all__ = [
    "KnowledgeIntegrationSystem",
    "KISRequest",
    "KISResult",
    "build_feature_vector",
    "SituationState",
    "ConstraintState",
    "KISOutput",
    "generate_type_weights",
    "TypeWeights",
    "MLJudgmentPrior",
    "LLMInterface",
    "SituationFrameOutput",
    "ConstraintExtractionOutput",
    "MLWisdomOrchestrator",
]
