"""Typed contracts for the unified orchestration pipeline."""

from __future__ import annotations

from .context import ExecutionContext
from .events import EventLevel, EventRecord, EventType
from .io import (
    ContractValidationContract,
    CouncilNormalizationContract,
    CouncilContract,
    DecisionPackagingContract,
    DecisionContract,
    DomainAnalysisContract,
    ErrorContract,
    InputContract,
    KnowledgeContract,
    ModeResolutionContract,
    PipelineErrorSummaryContract,
    PipelineIssueContract,
    PipelineTelemetryContract,
    RequestContextContract,
    RuntimeConfigContract,
)
from .module import ModuleHealth, ModulePlugin, ModuleResult, ModuleStatus

IO_CONTRACT_TYPES = (
    ContractValidationContract,
    CouncilNormalizationContract,
    CouncilContract,
    DecisionContract,
    DecisionPackagingContract,
    DomainAnalysisContract,
    ErrorContract,
    InputContract,
    KnowledgeContract,
    ModeResolutionContract,
    PipelineErrorSummaryContract,
    PipelineIssueContract,
    PipelineTelemetryContract,
    RequestContextContract,
    RuntimeConfigContract,
)

__all__ = (
    "CouncilContract",
    "ContractValidationContract",
    "CouncilNormalizationContract",
    "DecisionContract",
    "DecisionPackagingContract",
    "DomainAnalysisContract",
    "ErrorContract",
    "EventLevel",
    "EventRecord",
    "EventType",
    "ExecutionContext",
    "InputContract",
    "KnowledgeContract",
    "ModeResolutionContract",
    "PipelineErrorSummaryContract",
    "PipelineIssueContract",
    "PipelineTelemetryContract",
    "RequestContextContract",
    "RuntimeConfigContract",
    "ModuleHealth",
    "ModulePlugin",
    "ModuleResult",
    "ModuleStatus",
    "IO_CONTRACT_TYPES",
)
