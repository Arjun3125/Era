"""Top-level module plugin wrapper for the unified decision pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from dataclasses import dataclass
import json
import math
from typing import Any, Dict, Mapping, Sequence

from core.contracts import (
    ContractValidationContract,
    CouncilContract,
    CouncilNormalizationContract,
    DecisionContract,
    DecisionPackagingContract,
    DomainAnalysisContract,
    ExecutionContext,
    KnowledgeContract,
    ModeResolutionContract,
    ModuleHealth,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
    PipelineErrorSummaryContract,
    PipelineIssueContract,
    PipelineTelemetryContract,
    RequestContextContract,
    RuntimeConfigContract,
)

from .engine import DecisionPipelineEngine


def _coerce_iterable_items(value: Any, *, preserve_partial: bool) -> tuple[list[Any], bool]:
    try:
        iterator = iter(value)
    except Exception:
        return [], True
    items: list[Any] = []
    failed = False
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            break
        except Exception:
            failed = True
            break
        items.append(item)
    if failed and not preserve_partial:
        return [], True
    return items, failed


def _coerce_mapping(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            raw_items = value.items()
        except Exception:
            return {}
        items, _ = _coerce_iterable_items(raw_items, preserve_partial=True)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
        if failed and not raw_items:
            return None
        items = []
        for raw_item in raw_items:
            if isinstance(raw_item, Mapping):
                return None
            try:
                key, item_value = raw_item
            except Exception:
                return None
            items.append((key, item_value))
    elif isinstance(value, (str, bytes, bytearray)):
        text = DecisionPipelineModule._normalize_text(value)
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return None
        return _coerce_mapping(parsed)
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = DecisionPipelineModule._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class DecisionPipelineModule(ModulePlugin):
    """Expose the entire decision pipeline as a single pluggable module."""

    engine: DecisionPipelineEngine

    @classmethod
    def create(
        cls,
        *,
        llm: Any = None,
        prime_decider: Any = None,
        risk_threshold: float = 0.7,
        strict: bool = False,
    ) -> "DecisionPipelineModule":
        return cls(
            engine=DecisionPipelineEngine.create(
                llm=llm,
                prime_decider=prime_decider,
                risk_threshold=risk_threshold,
                strict=strict,
            )
        )

    def name(self) -> str:
        return "decision_pipeline"

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "orchestrates_mode_council_prime": True,
            "emits_structured_contracts": True,
            "emits_pipeline_telemetry": True,
            "emits_structured_error_summary": True,
            "supports_extension_stages": True,
            "normalizes_request_context": True,
            "validates_contract_consistency": True,
            "normalizes_council_output": True,
            "packages_final_decision": True,
            "supports_requested_mode": True,
        }

    def validate(self, context: ExecutionContext) -> None:
        if not isinstance(context, ExecutionContext):
            raise TypeError("DecisionPipelineModule requires an ExecutionContext.")
        if not isinstance(context.input_contract.user_input, str):
            raise TypeError("InputContract.user_input must be a string.")
        if not isinstance(context.state, Mapping):
            raise TypeError("ExecutionContext.state must be a mapping.")
        if not isinstance(context.config, Mapping):
            raise TypeError("ExecutionContext.config must be a mapping.")
        if not isinstance(context.metadata, Mapping):
            raise TypeError("ExecutionContext.metadata must be a mapping.")
        self._resolve_requested_mode(context, strict=True)
        self._resolve_routing_context(context, strict=True)

    def execute(self, context: ExecutionContext) -> ModuleResult:
        requested_mode = self._resolve_requested_mode(context, strict=False)
        routing_context = self._resolve_routing_context(context, strict=False)
        try:
            pipeline_result_raw = self.engine.run(
                user_input=context.input_contract.user_input,
                requested_mode=requested_mode,
                routing_context=routing_context,
                metadata=self._resolve_metadata(context),
                source=self._resolve_source(context),
            )
            pipeline_result = self._normalize_pipeline_result(
                pipeline_result_raw,
                requested_mode=requested_mode,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            message = f"{type(exc).__name__}: {exc}"
            pipeline_result_raw = {
                "status": "aborted",
                "errors": [message],
            }
            pipeline_result = self._build_exception_fallback(
                requested_mode=requested_mode,
                errors=[message],
            )

        status = self._resolve_module_status(pipeline_result)
        return ModuleResult(
            status=status,
            outputs={
                "decision_pipeline_result": pipeline_result_raw,
                "request_context_contract": pipeline_result["request_context_contract"],
                "runtime_config_contract": pipeline_result["runtime_config_contract"],
                "contract_validation_contract": pipeline_result["contract_validation_contract"],
                "council_normalization_contract": pipeline_result["council_normalization_contract"],
                "decision_packaging_contract": pipeline_result["decision_packaging_contract"],
                "error_summary_contract": pipeline_result["error_summary_contract"],
                "telemetry_contract": pipeline_result["telemetry_contract"],
                "domain_analysis_contract": pipeline_result["domain_analysis_contract"],
                "mode_contract": pipeline_result["mode_resolution"],
                "knowledge_contract": pipeline_result["knowledge_contract"],
                "council_contract": pipeline_result["council_contract"],
                "decision_contract": pipeline_result["decision_contract"],
                "domain_analysis_result": self._to_mapping(pipeline_result["domain_analysis_result"]),
                "knowledge_result": self._to_mapping(pipeline_result["knowledge_result"]),
                "council_result": self._to_mapping(pipeline_result["council_result"]),
                "council_result_normalized": self._to_mapping(pipeline_result["council_result_normalized"]),
                "decision_package": self._to_mapping(pipeline_result["decision_package"]),
                "prime_decision": self._to_mapping(pipeline_result["final_decision"]),
                "pipeline_issues": self._normalize_pipeline_issues(pipeline_result["pipeline_issues"]),
                "telemetry_metrics": self._to_mapping(pipeline_result["telemetry_metrics"]),
                "telemetry_trace": self._to_mapping(pipeline_result["telemetry_trace"]),
                "stage_order": self._to_string_list(pipeline_result["stage_order"]),
            },
            metrics=self._build_metrics(pipeline_result),
            errors=self._to_string_list(pipeline_result["errors"]),
        )

    def health(self) -> ModuleHealth:
        return ModuleHealth(ok=True, details={"pipeline": self.engine.pipeline_name})

    @staticmethod
    def _resolve_metadata(context: ExecutionContext) -> Dict[str, Any]:
        return DecisionPipelineModule._to_mapping(getattr(context, "metadata", {}))

    @staticmethod
    def _resolve_source(context: ExecutionContext) -> str:
        source = DecisionPipelineModule._normalize_text(getattr(context.input_contract, "source", ""))
        return source or "interactive"

    @staticmethod
    def _resolve_requested_mode(
        context: ExecutionContext,
        *,
        strict: bool,
    ) -> str | None:
        input_metadata = DecisionPipelineModule._to_mapping(context.input_contract.metadata)
        candidates = [
            DecisionPipelineModule._read_mapping_field(context.state, ("requested_mode", "mode")),
            DecisionPipelineModule._read_mapping_field(context.metadata, ("requested_mode", "mode")),
            DecisionPipelineModule._read_mapping_field(input_metadata, ("requested_mode", "mode")),
        ]
        for value in candidates:
            if value is None:
                continue
            if isinstance(value, str):
                text = value.strip()
                return text or None
            if isinstance(value, (int, float, bool)):
                text = str(value).strip()
                return text or None
            if strict:
                raise TypeError("requested_mode must be a scalar string-like value.")
            continue
        return None

    @staticmethod
    def _resolve_routing_context(
        context: ExecutionContext,
        *,
        strict: bool,
    ) -> Dict[str, Any]:
        input_metadata = DecisionPipelineModule._to_mapping(context.input_contract.metadata)
        candidates = [
            DecisionPipelineModule._read_mapping_field(context.state, ("routing_context",)),
            DecisionPipelineModule._read_mapping_field(context.config, ("routing_context",)),
            DecisionPipelineModule._read_mapping_field(input_metadata, ("routing_context",)),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            normalized = DecisionPipelineModule._to_mapping(candidate)
            if normalized:
                return normalized
            if _coerce_mapping(candidate) is not None:
                return {}
            if strict:
                raise TypeError("routing_context must be a mapping when provided.")
            continue
        return {}

    @staticmethod
    def _resolve_module_status(pipeline_result: Any) -> ModuleStatus:
        pipeline_status = str(DecisionPipelineModule._get_field(pipeline_result, "status", "") or "").strip().lower()
        if pipeline_status == "aborted":
            return ModuleStatus.FAILED
        if pipeline_status == "completed_with_errors":
            return ModuleStatus.DEGRADED

        summary = DecisionPipelineModule._get_field(pipeline_result, "error_summary_contract")
        fatal_count = DecisionPipelineModule._safe_int(getattr(summary, "fatal_count", 0))
        error_count = DecisionPipelineModule._safe_int(getattr(summary, "error_count", 0))
        if fatal_count > 0 or error_count > 0:
            return ModuleStatus.DEGRADED
        return ModuleStatus.SUCCESS

    @staticmethod
    def _build_metrics(pipeline_result: Any) -> Dict[str, Any]:
        stage_timings = DecisionPipelineModule._get_field(pipeline_result, "stage_timings_ms", {})
        stage_order = DecisionPipelineModule._to_string_list(
            DecisionPipelineModule._get_field(pipeline_result, "stage_order", [])
        )
        if not isinstance(stage_timings, Mapping):
            stage_timings = {}

        request_context = DecisionPipelineModule._get_field(pipeline_result, "request_context_contract")
        contract_validation = DecisionPipelineModule._get_field(pipeline_result, "contract_validation_contract")
        council_normalization = DecisionPipelineModule._get_field(pipeline_result, "council_normalization_contract")
        decision_packaging = DecisionPipelineModule._get_field(pipeline_result, "decision_packaging_contract")
        error_summary = DecisionPipelineModule._get_field(pipeline_result, "error_summary_contract")
        telemetry = DecisionPipelineModule._get_field(pipeline_result, "telemetry_contract")

        return {
            "pipeline_status": str(DecisionPipelineModule._get_field(pipeline_result, "status", "") or "unknown"),
            "stage_count": len(DecisionPipelineModule._to_mapping(stage_timings)),
            "stage_order_count": len(stage_order),
            "request_context_warning_count": DecisionPipelineModule._safe_int(
                getattr(request_context, "warning_count", 0)
            ),
            "contract_validation_warning_count": DecisionPipelineModule._safe_int(
                getattr(contract_validation, "warning_count", 0)
            ),
            "contract_validation_error_count": DecisionPipelineModule._safe_int(
                getattr(contract_validation, "error_count", 0)
            ),
            "council_normalization_warning_count": DecisionPipelineModule._safe_int(
                getattr(council_normalization, "warning_count", 0)
            ),
            "council_normalized_minister_count": DecisionPipelineModule._safe_int(
                getattr(council_normalization, "minister_count", 0)
            ),
            "decision_packaging_warning_count": DecisionPipelineModule._safe_int(
                getattr(decision_packaging, "warning_count", 0)
            ),
            "decision_requires_followup": bool(
                getattr(decision_packaging, "requires_followup", False)
            ),
            "pipeline_issue_count": DecisionPipelineModule._safe_int(
                getattr(error_summary, "issue_count", 0)
            ),
            "pipeline_fatal_count": DecisionPipelineModule._safe_int(
                getattr(error_summary, "fatal_count", 0)
            ),
            "telemetry_stage_count": DecisionPipelineModule._safe_int(
                getattr(telemetry, "stage_count", 0)
            ),
            "telemetry_total_stage_ms": DecisionPipelineModule._safe_float(
                getattr(telemetry, "total_stage_ms", 0.0)
            ),
        }

    @classmethod
    def _normalize_pipeline_result(
        cls,
        value: Any,
        *,
        requested_mode: str | None,
    ) -> Dict[str, Any]:
        mode = str(requested_mode or "meeting").strip().lower() or "meeting"
        result: Dict[str, Any] = {}
        result["status"] = str(cls._get_field(value, "status", "unknown") or "unknown")
        result["request_context_contract"] = cls._coerce_request_context_contract(
            cls._get_field(value, "request_context_contract"),
            mode=mode,
        )
        result["runtime_config_contract"] = cls._coerce_runtime_contract(
            cls._get_field(value, "runtime_config_contract")
        )
        result["contract_validation_contract"] = cls._coerce_validation_contract(
            cls._get_field(value, "contract_validation_contract")
        )
        result["council_normalization_contract"] = cls._coerce_council_normalization_contract(
            cls._get_field(value, "council_normalization_contract"),
            mode=mode,
        )
        result["decision_packaging_contract"] = cls._coerce_packaging_contract(
            cls._get_field(value, "decision_packaging_contract"),
            mode=mode,
        )
        result["error_summary_contract"] = cls._coerce_error_summary_contract(
            cls._get_field(value, "error_summary_contract")
        )
        result["telemetry_contract"] = cls._coerce_telemetry_contract(
            cls._get_field(value, "telemetry_contract")
        )
        result["domain_analysis_contract"] = cls._coerce_domain_contract(
            cls._get_field(value, "domain_analysis_contract")
        )
        result["mode_resolution"] = cls._coerce_mode_contract(
            cls._get_field(value, "mode_resolution"),
            mode=mode,
        )
        result["knowledge_contract"] = cls._coerce_knowledge_contract(
            cls._get_field(value, "knowledge_contract")
        )
        result["council_contract"] = cls._coerce_council_contract(
            cls._get_field(value, "council_contract")
        )
        result["decision_contract"] = cls._coerce_decision_contract(
            cls._get_field(value, "decision_contract"),
            mode=mode,
        )
        result["domain_analysis_result"] = cls._to_mapping(
            cls._get_field(value, "domain_analysis_result")
        )
        result["knowledge_result"] = cls._to_mapping(
            cls._get_field(value, "knowledge_result")
        )
        council_result_raw = cls._to_mapping(cls._get_field(value, "council_result"))
        council_result_normalized = cls._to_mapping(
            cls._get_field(value, "council_result_normalized")
        )
        result["council_result_normalized"] = council_result_normalized
        result["council_result"] = council_result_normalized or council_result_raw
        result["decision_package"] = cls._to_mapping(
            cls._get_field(value, "decision_package")
        )
        final_decision = cls._to_mapping(cls._get_field(value, "final_decision"))
        if result["decision_package"]:
            final_decision = cls._to_mapping(result["decision_package"])
        elif not final_decision:
            final_decision = {
                "final_outcome": result["decision_contract"].decision,
                "reason": result["decision_contract"].rationale,
                "mode": result["decision_contract"].mode,
            }
        result["final_decision"] = final_decision
        result["telemetry_metrics"] = cls._to_mapping(
            cls._get_field(value, "telemetry_metrics")
        )
        result["telemetry_trace"] = cls._to_mapping(
            cls._get_field(value, "telemetry_trace")
        )
        stage_timings_ms = cls._to_mapping(cls._get_field(value, "stage_timings_ms"))
        result["stage_timings_ms"] = stage_timings_ms
        stage_order = cls._to_string_list(cls._get_field(value, "stage_order"))
        result["stage_order"] = stage_order if stage_order else cls._to_string_list(stage_timings_ms.keys())
        result["pipeline_issues"] = cls._normalize_pipeline_issues(
            cls._get_field(value, "pipeline_issues")
        )
        result["errors"] = cls._to_string_list(cls._get_field(value, "errors"))
        return result

    @classmethod
    def _build_exception_fallback(
        cls,
        *,
        requested_mode: str | None,
        errors: Sequence[str],
    ) -> Dict[str, Any]:
        mode = str(requested_mode or "meeting").strip().lower() or "meeting"
        issue_items = cls._normalize_pipeline_issues(errors)
        return {
            "status": "aborted",
            "request_context_contract": RequestContextContract(requested_mode=mode),
            "runtime_config_contract": RuntimeConfigContract(source="decision_pipeline.module.exception"),
            "contract_validation_contract": ContractValidationContract(
                passed=False,
                warning_count=0,
                error_count=1,
                failed_checks=["decision_pipeline_exception"],
                checks={"decision_pipeline_exception": "error"},
                source="decision_pipeline.module.exception",
            ),
            "council_normalization_contract": CouncilNormalizationContract(mode=mode),
            "decision_packaging_contract": DecisionPackagingContract(mode=mode),
            "error_summary_contract": PipelineErrorSummaryContract(
                issue_count=1,
                error_count=1,
                warning_count=0,
                fatal_count=1,
                has_fatal=True,
                stages_with_issues=["decision_pipeline"],
                source="decision_pipeline.module.exception",
            ),
            "telemetry_contract": PipelineTelemetryContract(
                status="aborted",
                error_count=1,
                source="decision_pipeline.module.exception",
            ),
            "domain_analysis_contract": DomainAnalysisContract(domains=["strategy"], source="decision_pipeline.module.exception"),
            "mode_resolution": ModeResolutionContract(mode=mode, should_invoke_council=False),
            "knowledge_contract": KnowledgeContract(),
            "council_contract": CouncilContract(),
            "decision_contract": DecisionContract(
                decision="defer",
                confidence=0.0,
                rationale="decision_pipeline_module_exception",
                mode=mode,
            ),
            "domain_analysis_result": {},
            "knowledge_result": {},
            "council_result": {},
            "council_result_normalized": {},
            "decision_package": {},
            "final_decision": {
                "final_outcome": "defer",
                "reason": "decision_pipeline_module_exception",
                "confidence": 0.0,
                "mode": mode,
            },
            "pipeline_issues": issue_items,
            "telemetry_metrics": {},
            "telemetry_trace": {},
            "stage_order": [],
            "stage_timings_ms": {},
            "errors": cls._to_string_list(errors),
        }

    @staticmethod
    def _get_field(value: Any, field: str, default: Any = None) -> Any:
        if isinstance(value, Mapping):
            direct = value.get(field, default)
            if direct is not default:
                return direct
            normalized_field = DecisionPipelineModule._normalize_key_name(field)
            mapping_items = _coerce_mapping(value)
            if mapping_items is None:
                return default
            for raw_key, raw_value in mapping_items.items():
                if DecisionPipelineModule._normalize_key_name(raw_key) == normalized_field:
                    return raw_value
            return default
        if hasattr(value, field):
            return getattr(value, field)
        return default

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        return _coerce_mapping(value) or {}

    @staticmethod
    def _to_string_list(value: Any) -> list[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (bytes, bytearray)):
            raw_items = [DecisionPipelineModule._normalize_text(value)]
        elif isinstance(value, str):
            raw_items = [part.strip() for part in value.split(",")]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [DecisionPipelineModule._normalize_text(item) for item in items]
        elif isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            raw_items = [DecisionPipelineModule._normalize_text(item) for item in items]
        else:
            return []
        deduped: list[str] = []
        seen = set()
        for item in raw_items:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    @staticmethod
    def _coerce_request_context_contract(value: Any, *, mode: str) -> RequestContextContract:
        if isinstance(value, RequestContextContract):
            return value
        return RequestContextContract(requested_mode=mode)

    @staticmethod
    def _coerce_runtime_contract(value: Any) -> RuntimeConfigContract:
        if isinstance(value, RuntimeConfigContract):
            return value
        return RuntimeConfigContract()

    @staticmethod
    def _coerce_validation_contract(value: Any) -> ContractValidationContract:
        if isinstance(value, ContractValidationContract):
            return value
        return ContractValidationContract()

    @staticmethod
    def _coerce_council_normalization_contract(
        value: Any,
        *,
        mode: str,
    ) -> CouncilNormalizationContract:
        if isinstance(value, CouncilNormalizationContract):
            return value
        return CouncilNormalizationContract(mode=mode)

    @staticmethod
    def _coerce_packaging_contract(value: Any, *, mode: str) -> DecisionPackagingContract:
        if isinstance(value, DecisionPackagingContract):
            return value
        return DecisionPackagingContract(mode=mode)

    @staticmethod
    def _coerce_error_summary_contract(value: Any) -> PipelineErrorSummaryContract:
        if isinstance(value, PipelineErrorSummaryContract):
            return value
        return PipelineErrorSummaryContract()

    @staticmethod
    def _coerce_telemetry_contract(value: Any) -> PipelineTelemetryContract:
        if isinstance(value, PipelineTelemetryContract):
            return value
        return PipelineTelemetryContract()

    @staticmethod
    def _coerce_domain_contract(value: Any) -> DomainAnalysisContract:
        if isinstance(value, DomainAnalysisContract):
            return value
        return DomainAnalysisContract(domains=["strategy"])

    @staticmethod
    def _coerce_mode_contract(value: Any, *, mode: str) -> ModeResolutionContract:
        if isinstance(value, ModeResolutionContract):
            return value
        return ModeResolutionContract(mode=mode, should_invoke_council=False)

    @staticmethod
    def _coerce_knowledge_contract(value: Any) -> KnowledgeContract:
        if isinstance(value, KnowledgeContract):
            return value
        return KnowledgeContract()

    @staticmethod
    def _coerce_council_contract(value: Any) -> CouncilContract:
        if isinstance(value, CouncilContract):
            return value
        return CouncilContract()

    @staticmethod
    def _coerce_decision_contract(value: Any, *, mode: str) -> DecisionContract:
        if isinstance(value, DecisionContract):
            return value
        return DecisionContract(decision="defer", confidence=0.0, rationale="", mode=mode)

    @staticmethod
    def _normalize_pipeline_issues(value: Any) -> list[Dict[str, Any]]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            values, _ = _coerce_iterable_items(value, preserve_partial=True)
        elif isinstance(value, Iterable):
            values, _ = _coerce_iterable_items(value, preserve_partial=True)
        else:
            values = [value]

        normalized: list[Dict[str, Any]] = []
        for item in values:
            if isinstance(item, PipelineIssueContract):
                normalized.append(asdict(item))
                continue
            if isinstance(item, Mapping):
                normalized.append(_coerce_mapping(item) or {})
                continue
            text = str(item).strip()
            if not text:
                continue
            normalized.append(
                {
                    "code": "pipeline_issue",
                    "message": text,
                    "severity": "error",
                    "stage": None,
                    "recoverable": False,
                    "source": "decision_pipeline.module.normalized_result",
                    "details": {},
                }
            )
        return normalized

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            return 0.0
        if not math.isfinite(numeric):
            return 0.0
        return numeric

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()

    @staticmethod
    def _normalize_key_name(value: Any) -> str:
        return (
            DecisionPipelineModule._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_mapping_field(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
        if not isinstance(source, Mapping):
            return None
        normalized_keys = {DecisionPipelineModule._normalize_key_name(key) for key in keys}
        mapping_items = _coerce_mapping(source)
        if mapping_items is None:
            return None
        for raw_key, value in mapping_items.items():
            if DecisionPipelineModule._normalize_key_name(raw_key) in normalized_keys:
                return value
        return None
