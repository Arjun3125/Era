"""Central decision pipeline engine for mode->council->prime orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from core.contracts import (
    ContractValidationContract,
    CouncilNormalizationContract,
    CouncilContract,
    DecisionPackagingContract,
    DecisionContract,
    DomainAnalysisContract,
    ExecutionContext,
    InputContract,
    KnowledgeContract,
    ModeResolutionContract,
    ModulePlugin,
    ModuleResult,
    ModuleStatus,
    PipelineErrorSummaryContract,
    PipelineIssueContract,
    PipelineTelemetryContract,
    RequestContextContract,
    RuntimeConfigContract,
)
from core.orchestrator import OrchestrationResult, PipelineOrchestrator, StageOutcome
from modules.contract_validation.module import ContractValidationModule
from modules.council_execution.module import CouncilExecutionModule
from modules.council_normalization.module import CouncilNormalizationModule
from modules.council_router.module import ModeRoutingModule
from modules.domain_analysis.module import DomainAnalysisModule
from modules.input_normalization.module import InputNormalizationModule
from modules.knowledge_synthesis.module import KnowledgeSynthesisModule
from modules.decision_packaging.module import DecisionPackagingModule
from modules.prime_decision.engine import PrimeDecisionEngine
from modules.prime_decision.module import PrimeDecisionModule
from modules.runtime_config.module import RuntimeConfigModule

from .errors import DecisionPipelineErrorEngine
from .extensions import ExtensionStagePlanner, ExtensionStageSpec
from .telemetry import DecisionPipelineTelemetryEngine


@dataclass
class DecisionPipelineResult:
    """Structured result for one decision pipeline execution."""

    run_id: str
    status: str
    request_context_contract: RequestContextContract
    runtime_config_contract: RuntimeConfigContract
    contract_validation_contract: ContractValidationContract
    council_normalization_contract: CouncilNormalizationContract
    decision_packaging_contract: DecisionPackagingContract
    error_summary_contract: PipelineErrorSummaryContract
    telemetry_contract: PipelineTelemetryContract
    domain_analysis_contract: DomainAnalysisContract
    mode_resolution: ModeResolutionContract
    knowledge_contract: KnowledgeContract
    council_contract: CouncilContract
    decision_contract: DecisionContract
    domain_analysis_result: Dict[str, Any] = field(default_factory=dict)
    knowledge_result: Dict[str, Any] = field(default_factory=dict)
    council_result: Dict[str, Any] = field(default_factory=dict)
    council_result_normalized: Dict[str, Any] = field(default_factory=dict)
    decision_package: Dict[str, Any] = field(default_factory=dict)
    final_decision: Dict[str, Any] = field(default_factory=dict)
    pipeline_issues: List[PipelineIssueContract] = field(default_factory=list)
    telemetry_metrics: Dict[str, Any] = field(default_factory=dict)
    telemetry_trace: Dict[str, Any] = field(default_factory=dict)
    stage_order: List[str] = field(default_factory=list)
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    orchestration_result: Optional[OrchestrationResult] = None


@dataclass
class DecisionPipelineEngine:
    """Composable engine over orchestrator-compatible module plugins."""

    input_module: InputNormalizationModule
    config_module: RuntimeConfigModule
    domain_module: DomainAnalysisModule
    mode_module: ModeRoutingModule
    knowledge_module: KnowledgeSynthesisModule
    validation_module: ContractValidationModule
    council_module: CouncilExecutionModule
    council_normalization_module: CouncilNormalizationModule
    prime_module: PrimeDecisionModule
    decision_packaging_module: DecisionPackagingModule
    telemetry_engine: DecisionPipelineTelemetryEngine = field(
        default_factory=DecisionPipelineTelemetryEngine
    )
    error_engine: DecisionPipelineErrorEngine = field(
        default_factory=DecisionPipelineErrorEngine
    )
    extension_stages: List[ExtensionStageSpec] = field(default_factory=list)
    strict: bool = False
    pipeline_name: str = "decision_pipeline"
    _pipeline: Optional[PipelineOrchestrator] = field(default=None, init=False, repr=False)
    _extension_planner: ExtensionStagePlanner = field(
        default_factory=ExtensionStagePlanner,
        init=False,
        repr=False,
    )

    @classmethod
    def create(
        cls,
        *,
        llm: Any = None,
        prime_decider: Any = None,
        risk_threshold: float = 0.7,
        strict: bool = False,
    ) -> "DecisionPipelineEngine":
        prime_engine = PrimeDecisionEngine(
            risk_threshold=risk_threshold,
            llm_adapter=llm,
            prime_decider=prime_decider,
        )
        return cls(
            input_module=InputNormalizationModule.create(),
            config_module=RuntimeConfigModule.create(),
            domain_module=DomainAnalysisModule.create(llm_adapter=llm),
            mode_module=ModeRoutingModule.create(),
            knowledge_module=KnowledgeSynthesisModule.create(),
            validation_module=ContractValidationModule.create(),
            council_module=CouncilExecutionModule.create(llm=llm),
            council_normalization_module=CouncilNormalizationModule.create(),
            prime_module=PrimeDecisionModule(engine=prime_engine),
            decision_packaging_module=DecisionPackagingModule.create(),
            strict=strict,
        )

    def run(
        self,
        *,
        user_input: str,
        requested_mode: Optional[str] = None,
        routing_context: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        source: str = "interactive",
    ) -> DecisionPipelineResult:
        """Execute all decision stages through a central orchestrator."""
        normalized_user_input = self._normalize_user_input(user_input)
        normalized_source = self._normalize_source(source)
        normalized_requested_mode = self._normalize_optional_scalar(requested_mode)
        normalized_routing_context = self._to_mapping(routing_context)
        run_metadata = self._to_mapping(metadata)
        if normalized_requested_mode:
            run_metadata["requested_mode"] = normalized_requested_mode

        result = self._pipeline_instance().run(
            InputContract(
                user_input=normalized_user_input,
                source=normalized_source,
                metadata={"routing_context": dict(normalized_routing_context)},
            ),
            metadata=run_metadata,
            config={"routing_context": dict(normalized_routing_context)},
        )
        state = result.context.state

        request_context_contract = self._resolve_request_context_contract(state)
        runtime_config_contract = self._resolve_runtime_config_contract(state)
        contract_validation_contract = self._resolve_contract_validation_contract(state)
        council_normalization_contract = self._resolve_council_normalization_contract(state)
        decision_packaging_contract = self._resolve_decision_packaging_contract(state)
        domain_contract = self._resolve_domain_contract(state)
        mode_contract = self._resolve_mode_contract(state, requested_mode=normalized_requested_mode)
        knowledge_contract = self._resolve_knowledge_contract(state)
        council_contract = self._resolve_council_contract(state)
        decision_contract = self._resolve_decision_contract(state, mode_contract.mode)
        domain_analysis_result = self._to_mapping(
            self._read_mapping_field(state, ("domain_analysis_result",))
        )
        knowledge_result = self._to_mapping(
            self._read_mapping_field(state, ("knowledge_result",))
        )
        council_result_raw = self._to_mapping(
            self._read_mapping_field(state, ("council_result",))
        )
        council_result_normalized = self._to_mapping(
            self._read_mapping_field(state, ("council_result_normalized",))
        )
        council_result = council_result_normalized or council_result_raw
        decision_package = self._to_mapping(
            self._read_mapping_field(state, ("decision_package",))
        )
        final_decision = self._to_mapping(
            self._read_mapping_field(state, ("prime_decision",))
        )
        if decision_package:
            final_decision = dict(decision_package)
        elif not final_decision:
            final_decision = {
                "final_outcome": decision_contract.decision,
                "reason": decision_contract.rationale,
            }

        telemetry_result = self.telemetry_engine.collect(
            result=result,
            runtime_config=runtime_config_contract,
            metadata=run_metadata,
        )
        error_result = self.error_engine.collect(
            result=result,
            additional_warnings=telemetry_result.warnings,
        )
        stage_timings_ms = self._to_mapping(getattr(result, "stage_timings_ms", {}))

        return DecisionPipelineResult(
            run_id=result.run_id,
            status=result.status.value,
            request_context_contract=request_context_contract,
            runtime_config_contract=runtime_config_contract,
            contract_validation_contract=contract_validation_contract,
            council_normalization_contract=council_normalization_contract,
            decision_packaging_contract=decision_packaging_contract,
            error_summary_contract=error_result.summary,
            telemetry_contract=telemetry_result.contract,
            domain_analysis_contract=domain_contract,
            mode_resolution=mode_contract,
            knowledge_contract=knowledge_contract,
            council_contract=council_contract,
            decision_contract=decision_contract,
            domain_analysis_result=domain_analysis_result,
            knowledge_result=knowledge_result,
            council_result=council_result,
            council_result_normalized=council_result_normalized,
            decision_package=decision_package,
            final_decision=final_decision,
            pipeline_issues=list(error_result.issues),
            telemetry_metrics=self._to_mapping(getattr(telemetry_result, "metrics", {})),
            telemetry_trace=self._to_mapping(getattr(telemetry_result, "trace", {})),
            stage_order=list(stage_timings_ms.keys()),
            stage_timings_ms=stage_timings_ms,
            errors=list(error_result.messages),
            orchestration_result=result,
        )

    def register_extension_module(
        self,
        module: ModulePlugin,
        *,
        before: Optional[str] = None,
        after: Optional[str] = None,
        on_error: str = "degrade",
    ) -> None:
        """Register a module plugin as an extension stage in this pipeline."""
        if module is None:
            raise TypeError("Extension module must be provided.")
        if not hasattr(module, "name") or not callable(getattr(module, "name")):
            raise TypeError("Extension module must define callable name().")
        stage_name = str(module.name()).strip()
        if not stage_name:
            raise ValueError("Extension module name must be non-empty.")

        def _handler(context: ExecutionContext) -> StageOutcome:
            self._prepare_context(context)
            return self._run_plugin(module, context)

        self.register_extension_handler(
            name=stage_name,
            handler=_handler,
            before=before,
            after=after,
            on_error=on_error,
        )

    def register_extension_handler(
        self,
        *,
        name: str,
        handler: Callable[[ExecutionContext], Any],
        before: Optional[str] = None,
        after: Optional[str] = None,
        on_error: str = "degrade",
        source: str = "runtime",
    ) -> None:
        """Register an ad-hoc extension stage handler in this pipeline."""
        stage_name = str(name).strip()
        if not stage_name:
            raise ValueError("Extension stage name must be non-empty.")
        if stage_name in self._core_stage_names():
            raise ValueError(f"Extension stage '{stage_name}' conflicts with core pipeline stage.")
        if before and after:
            raise ValueError("Extension stage cannot specify both 'before' and 'after'.")
        normalized_on_error = str(on_error).strip().lower()
        if normalized_on_error not in {"abort", "degrade"}:
            raise ValueError("Extension stage on_error must be 'abort' or 'degrade'.")
        if not callable(handler):
            raise TypeError("Extension stage handler must be callable.")
        before_name = str(before).strip() if before is not None else None
        after_name = str(after).strip() if after is not None else None
        if before_name and before_name == stage_name:
            raise ValueError("Extension stage cannot anchor before itself.")
        if after_name and after_name == stage_name:
            raise ValueError("Extension stage cannot anchor after itself.")

        for existing in self.extension_stages:
            if existing.name == stage_name:
                raise ValueError(f"Extension stage '{stage_name}' already registered.")

        self.extension_stages.append(
            ExtensionStageSpec(
                name=stage_name,
                handler=handler,
                on_error=normalized_on_error,
                before=before_name,
                after=after_name,
                source=str(source).strip() or "runtime",
            )
        )
        self._pipeline = None

    def _pipeline_instance(self) -> PipelineOrchestrator:
        if self._pipeline is not None:
            return self._pipeline

        pipeline = PipelineOrchestrator(name=self.pipeline_name, strict=self.strict)
        for spec in self._compose_stage_plan():
            pipeline.register_stage(spec.name, spec.handler, on_error=spec.on_error)
        self._pipeline = pipeline
        return pipeline

    def _compose_stage_plan(self) -> List[ExtensionStageSpec]:
        base_plan: List[ExtensionStageSpec] = [
            ExtensionStageSpec(
                name="input_normalization",
                handler=self._stage_input_normalization,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="runtime_config",
                handler=self._stage_runtime_config,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="domain_analysis",
                handler=self._stage_domain_analysis,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="mode_routing",
                handler=self._stage_mode_routing,
                on_error="abort",
                source="core",
            ),
            ExtensionStageSpec(
                name="knowledge_synthesis",
                handler=self._stage_knowledge_synthesis,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="council_execution",
                handler=self._stage_council_execution,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="council_normalization",
                handler=self._stage_council_normalization,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="prime_decision",
                handler=self._stage_prime_decision,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="decision_packaging",
                handler=self._stage_decision_packaging,
                on_error="degrade",
                source="core",
            ),
            ExtensionStageSpec(
                name="contract_validation",
                handler=self._stage_contract_validation,
                on_error="degrade",
                source="core",
            ),
        ]
        return self._extension_planner.compose(
            base_plan=base_plan,
            extensions=self.extension_stages,
        )

    @staticmethod
    def _core_stage_names() -> set[str]:
        return {
            "input_normalization",
            "runtime_config",
            "domain_analysis",
            "mode_routing",
            "knowledge_synthesis",
            "council_execution",
            "council_normalization",
            "prime_decision",
            "decision_packaging",
            "contract_validation",
        }

    def _stage_runtime_config(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.config_module, context)
        return self._merge_runtime_config_into_context(context, outcome)

    def _stage_input_normalization(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.input_module, context)
        return self._merge_request_context_into_state(context, outcome)

    def _stage_domain_analysis(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.domain_module, context)
        return self._merge_domain_analysis_into_routing_context(context, outcome)

    def _stage_mode_routing(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        return self._run_plugin(self.mode_module, context)

    def _stage_knowledge_synthesis(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.knowledge_module, context)
        return self._merge_knowledge_into_routing_context(context, outcome)

    def _stage_council_execution(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        return self._run_plugin(self.council_module, context)

    def _stage_council_normalization(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.council_normalization_module, context)
        return self._merge_council_normalization_into_state(context, outcome)

    def _stage_contract_validation(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        return self._run_plugin(self.validation_module, context)

    def _stage_decision_packaging(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        outcome = self._run_plugin(self.decision_packaging_module, context)
        return self._merge_decision_package_into_state(context, outcome)

    def _stage_prime_decision(self, context: ExecutionContext) -> StageOutcome:
        self._prepare_context(context)
        if self._read_mapping_field(context.state, ("minister_outputs_normalized",)) is None:
            normalized = self._to_mapping(
                self._read_mapping_field(context.state, ("council_result_normalized",))
            )
            context.state["minister_outputs_normalized"] = (
                self._read_mapping_field(normalized, ("minister_outputs",))
                or self._read_mapping_field(normalized, ("minister_positions",))
                or {}
            )
        if self._read_mapping_field(context.state, ("minister_outputs",)) is None:
            context.state["minister_outputs"] = (
                self._read_mapping_field(context.state, ("minister_outputs_normalized",))
                or {}
            )
        return self._run_plugin(self.prime_module, context)

    def _prepare_context(self, context: ExecutionContext) -> None:
        metadata = self._to_mapping(getattr(context, "metadata", {}))
        input_metadata = self._to_mapping(getattr(context.input_contract, "metadata", {}))
        mode_candidates = [
            self._read_mapping_field(context.state, ("requested_mode", "mode")),
            self._read_mapping_field(metadata, ("requested_mode", "mode")),
            self._read_mapping_field(input_metadata, ("requested_mode", "mode")),
        ]
        for raw_mode in mode_candidates:
            mode_value = self._normalize_optional_scalar(raw_mode)
            if not mode_value:
                continue
            context.state["requested_mode"] = mode_value
            break

        routing_context = self._to_mapping(
            self._read_mapping_field(context.state, ("routing_context",))
        )
        if not routing_context:
            routing_context = self._to_mapping(
                self._read_mapping_field(context.config, ("routing_context",))
            )
            routing_context.update(
                self._to_mapping(self._read_mapping_field(input_metadata, ("routing_context",)))
            )
        context.state["routing_context"] = routing_context

    @staticmethod
    def _merge_request_context_into_state(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        mode = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("requested_mode", "mode"),
        )
        if isinstance(mode, str) and mode.strip():
            context.state["requested_mode"] = mode.strip().lower()

        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(outputs, ("routing_context",))
        )
        if routing_context:
            context.state["routing_context"] = DecisionPipelineEngine._to_mapping(routing_context)
            context.config["routing_context"] = DecisionPipelineEngine._to_mapping(routing_context)

        contract = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("request_context_contract",),
        )
        if isinstance(contract, RequestContextContract):
            context.state["request_context_contract"] = contract

        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _merge_runtime_config_into_context(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        runtime_settings = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(outputs, ("runtime_settings",))
        )
        if runtime_settings:
            context.config["runtime_settings"] = DecisionPipelineEngine._to_mapping(runtime_settings)
            context.state["runtime_settings"] = DecisionPipelineEngine._to_mapping(runtime_settings)

        contract = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("runtime_config_contract",),
        )
        if isinstance(contract, RuntimeConfigContract):
            context.state["runtime_config_contract"] = contract

        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _merge_knowledge_into_routing_context(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        knowledge_result = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(outputs, ("knowledge_result",))
        )
        synthesized = DecisionPipelineEngine._to_list(
            DecisionPipelineEngine._read_mapping_field(
                knowledge_result,
                ("synthesized_knowledge",),
            )
        )
        knowledge_quality = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(
                knowledge_result,
                ("knowledge_quality",),
            )
        )

        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(context.state, ("routing_context",))
        )
        if synthesized:
            routing_context["synthesized_knowledge"] = synthesized
        if knowledge_quality:
            routing_context["knowledge_quality"] = knowledge_quality
        context.state["routing_context"] = routing_context

        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _merge_domain_analysis_into_routing_context(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        contract = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("domain_analysis_contract",),
        )

        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(context.state, ("routing_context",))
        )
        if isinstance(contract, DomainAnalysisContract):
            if not routing_context.get("domains"):
                routing_context["domains"] = DecisionPipelineEngine._to_list(contract.domains)
            routing_context.setdefault(
                "domain_confidence",
                DecisionPipelineEngine._safe_float(contract.domain_confidence, default=0.0),
            )
            routing_context.setdefault("stakes", contract.stakes)
            routing_context.setdefault("reversibility", contract.reversibility)
            if contract.key_entities and not routing_context.get("key_entities"):
                routing_context["key_entities"] = DecisionPipelineEngine._to_list(contract.key_entities)
            if contract.domain_scores and not routing_context.get("domain_scores"):
                routing_context["domain_scores"] = DecisionPipelineEngine._to_mapping(contract.domain_scores)

        context.state["routing_context"] = routing_context
        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _merge_council_normalization_into_state(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        normalized_council = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("council_result_normalized",),
        )
        normalized_mapping = DecisionPipelineEngine._to_mapping(normalized_council)
        if normalized_mapping:
            context.state["council_result_normalized"] = DecisionPipelineEngine._to_mapping(normalized_mapping)
            context.state["council_result"] = DecisionPipelineEngine._to_mapping(normalized_mapping)

        normalized_ministers = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("minister_outputs_normalized",),
        )
        normalized_minister_mapping = DecisionPipelineEngine._to_mapping(normalized_ministers)
        if normalized_minister_mapping:
            context.state["minister_outputs"] = DecisionPipelineEngine._to_mapping(normalized_minister_mapping)

        normalized_positions = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("council_positions_normalized",),
        )
        if isinstance(normalized_positions, Sequence) and not isinstance(
            normalized_positions,
            (str, bytes, bytearray),
        ):
            current = DecisionPipelineEngine._to_mapping(
                DecisionPipelineEngine._read_mapping_field(context.state, ("council_result",))
            )
            current["council_positions"] = DecisionPipelineEngine._to_list(normalized_positions)
            context.state["council_result"] = current
        elif isinstance(normalized_positions, Iterable) and not isinstance(
            normalized_positions,
            (str, bytes, bytearray, Mapping),
        ):
            current = DecisionPipelineEngine._to_mapping(
                DecisionPipelineEngine._read_mapping_field(context.state, ("council_result",))
            )
            current["council_positions"] = DecisionPipelineEngine._to_list(normalized_positions)
            context.state["council_result"] = current

        contract = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("council_normalization_contract",),
        )
        if isinstance(contract, CouncilNormalizationContract):
            context.state["council_normalization_contract"] = contract

        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _merge_decision_package_into_state(
        context: ExecutionContext,
        outcome: StageOutcome,
    ) -> StageOutcome:
        outputs = DecisionPipelineEngine._to_mapping(outcome.outputs)
        package = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(outputs, ("decision_package",))
        )
        if package:
            context.state["decision_package"] = DecisionPipelineEngine._to_mapping(package)

        contract = DecisionPipelineEngine._read_mapping_field(
            outputs,
            ("decision_packaging_contract",),
        )
        if isinstance(contract, DecisionPackagingContract):
            context.state["decision_packaging_contract"] = contract

        return StageOutcome(
            outputs=outputs,
            errors=list(outcome.errors or []),
            continue_pipeline=outcome.continue_pipeline,
            degraded=outcome.degraded,
        )

    @staticmethod
    def _run_plugin(plugin: ModulePlugin, context: ExecutionContext) -> StageOutcome:
        plugin_name = DecisionPipelineEngine._safe_plugin_name(plugin)
        try:
            plugin.validate(context)
            result: ModuleResult = plugin.execute(context)
            if not isinstance(result, ModuleResult):
                raise TypeError("Plugin execute() must return ModuleResult.")
            outputs = DecisionPipelineEngine._to_mapping(result.outputs)
            outputs[f"{plugin_name}_status"] = result.status.value
            if result.metrics:
                outputs[f"{plugin_name}_metrics"] = DecisionPipelineEngine._to_mapping(result.metrics)
            return StageOutcome(
                outputs=outputs,
                errors=list(result.errors or []),
                degraded=(result.status != ModuleStatus.SUCCESS),
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            return StageOutcome(
                outputs={f"{plugin_name}_status": ModuleStatus.FAILED.value},
                errors=[f"{type(exc).__name__}: {exc}"],
                degraded=True,
            )

    @staticmethod
    def _resolve_mode_contract(
        state: Mapping[str, Any],
        *,
        requested_mode: Optional[str],
    ) -> ModeResolutionContract:
        mode_contract = DecisionPipelineEngine._read_mapping_field(state, ("mode_contract",))
        if isinstance(mode_contract, ModeResolutionContract):
            return mode_contract

        mode = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(state, ("resolved_mode", "mode"))
            or requested_mode
            or DecisionPipelineEngine._read_mapping_field(state, ("requested_mode", "mode"))
            or "meeting"
        ).lower() or "meeting"
        should_invoke = DecisionPipelineEngine._to_bool(
            DecisionPipelineEngine._read_mapping_field(state, ("should_invoke_council",))
        )
        if should_invoke is None:
            should_invoke = mode != "quick"
        selected = DecisionPipelineEngine._to_list(
            DecisionPipelineEngine._read_mapping_field(state, ("selected_ministers",))
        )
        rationale = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(state, ("mode_frame",))
        )
        confidence = DecisionPipelineEngine._safe_float(
            DecisionPipelineEngine._read_mapping_field(
                state,
                ("mode_resolution_confidence",),
                default=1.0,
            ),
            default=1.0,
        )
        return ModeResolutionContract(
            mode=mode,
            should_invoke_council=bool(should_invoke),
            selected_ministers=selected,
            rationale=rationale,
            confidence=confidence,
        )

    @staticmethod
    def _resolve_request_context_contract(
        state: Mapping[str, Any],
    ) -> RequestContextContract:
        request_contract = DecisionPipelineEngine._read_mapping_field(
            state,
            ("request_context_contract",),
        )
        if isinstance(request_contract, RequestContextContract):
            return request_contract

        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("routing_context",))
        )
        mode = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(
                state,
                ("requested_mode", "mode"),
                default="meeting",
            )
        ).lower() or "meeting"
        return RequestContextContract(
            requested_mode=mode,
            routing_context=routing_context,
            warning_count=0,
            source="decision_pipeline_fallback",
        )

    @staticmethod
    def _resolve_runtime_config_contract(
        state: Mapping[str, Any],
    ) -> RuntimeConfigContract:
        runtime_contract = DecisionPipelineEngine._read_mapping_field(
            state,
            ("runtime_config_contract",),
        )
        if isinstance(runtime_contract, RuntimeConfigContract):
            return runtime_contract

        runtime_settings = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("runtime_settings",))
        )
        return RuntimeConfigContract(
            app_name=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(runtime_settings, ("app_name",), default="era")
            ),
            environment=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(
                    runtime_settings,
                    ("environment",),
                    default="development",
                )
            ),
            orchestrator_strict=bool(
                DecisionPipelineEngine._to_bool(
                    DecisionPipelineEngine._read_mapping_field(runtime_settings, ("orchestrator_strict",))
                )
            ),
            decision_pipeline_enabled=DecisionPipelineEngine._to_bool(
                DecisionPipelineEngine._read_mapping_field(
                    runtime_settings,
                    ("decision_pipeline_enabled",),
                    default=True,
                )
            )
            is not False,
            observability_enabled=DecisionPipelineEngine._to_bool(
                DecisionPipelineEngine._read_mapping_field(
                    runtime_settings,
                    ("observability_enabled",),
                    default=True,
                )
            )
            is not False,
            observability_emit_events=bool(
                DecisionPipelineEngine._to_bool(
                    DecisionPipelineEngine._read_mapping_field(
                        runtime_settings,
                        ("observability_emit_events",),
                        default=False,
                    )
                )
            ),
            observability_emit_summary=DecisionPipelineEngine._to_bool(
                DecisionPipelineEngine._read_mapping_field(
                    runtime_settings,
                    ("observability_emit_summary",),
                    default=True,
                )
            )
            is not False,
            observability_write_file=bool(
                DecisionPipelineEngine._to_bool(
                    DecisionPipelineEngine._read_mapping_field(
                        runtime_settings,
                        ("observability_write_file",),
                        default=False,
                    )
                )
            ),
            observability_stderr=bool(
                DecisionPipelineEngine._to_bool(
                    DecisionPipelineEngine._read_mapping_field(
                        runtime_settings,
                        ("observability_stderr",),
                        default=False,
                    )
                )
            ),
            observability_file=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(
                    runtime_settings,
                    ("observability_file",),
                    default="logs/orchestration_events.jsonl",
                )
            ),
            source="decision_pipeline_fallback",
            overrides_applied=DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(runtime_settings, ("overrides_applied",))
            ),
        )

    @staticmethod
    def _resolve_contract_validation_contract(
        state: Mapping[str, Any],
    ) -> ContractValidationContract:
        validation_contract = DecisionPipelineEngine._read_mapping_field(
            state,
            ("contract_validation_contract",),
        )
        if isinstance(validation_contract, ContractValidationContract):
            return validation_contract
        return ContractValidationContract(
            passed=True,
            warning_count=0,
            error_count=0,
            warning_checks=[],
            failed_checks=[],
            checks={},
            source="decision_pipeline_fallback",
        )

    @staticmethod
    def _resolve_council_normalization_contract(
        state: Mapping[str, Any],
    ) -> CouncilNormalizationContract:
        contract = DecisionPipelineEngine._read_mapping_field(
            state,
            ("council_normalization_contract",),
        )
        if isinstance(contract, CouncilNormalizationContract):
            return contract

        council_result = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("council_result_normalized",))
            or DecisionPipelineEngine._read_mapping_field(state, ("council_result",))
            or {}
        )
        mode = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(council_result, ("mode",))
            or DecisionPipelineEngine._read_mapping_field(state, ("resolved_mode", "mode"))
            or DecisionPipelineEngine._read_mapping_field(state, ("requested_mode", "mode"))
            or "meeting"
        ).lower() or "meeting"
        red_line_count = len(
            DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(council_result, ("red_line_concerns",))
            )
        )
        ministers_failed = len(
            DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(council_result, ("ministers_failed",))
            )
        )
        ministers = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(council_result, ("minister_outputs",))
        )
        consensus = DecisionPipelineEngine._safe_float(
            DecisionPipelineEngine._read_mapping_field(
                council_result,
                ("consensus_strength",),
                default=0.0,
            ),
            default=0.0,
        )
        outcome = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(council_result, ("outcome",), default="not_invoked")
        ) or "not_invoked"
        council_invoked = outcome not in {"quick_mode_direct_response", "council_disabled_ablation"}
        return CouncilNormalizationContract(
            mode=mode,
            outcome=outcome,
            recommendation=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(
                    council_result,
                    ("recommendation",),
                    default="defer",
                )
            ),
            consensus_strength=consensus,
            minister_count=len(ministers),
            failed_minister_count=ministers_failed,
            red_line_count=red_line_count,
            council_invoked=council_invoked,
            warning_count=0,
            source="decision_pipeline_fallback",
        )

    @staticmethod
    def _resolve_decision_packaging_contract(
        state: Mapping[str, Any],
    ) -> DecisionPackagingContract:
        contract = DecisionPipelineEngine._read_mapping_field(
            state,
            ("decision_packaging_contract",),
        )
        if isinstance(contract, DecisionPackagingContract):
            return contract

        package = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("decision_package",))
        )
        decision_contract = DecisionPipelineEngine._read_mapping_field(state, ("decision_contract",))
        outcome = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(package, ("final_outcome",))
            or getattr(decision_contract, "decision", "defer")
        ).lower() or "defer"
        mode = DecisionPipelineEngine._normalize_text(
            DecisionPipelineEngine._read_mapping_field(package, ("mode",))
            or getattr(decision_contract, "mode", "meeting")
        ).lower() or "meeting"
        confidence = DecisionPipelineEngine._safe_float(
            DecisionPipelineEngine._read_mapping_field(
                package,
                ("confidence",),
                default=getattr(decision_contract, "confidence", 0.0),
            ),
            default=0.0,
        )
        red_line_value = DecisionPipelineEngine._read_mapping_field(
            package,
            ("red_line_concerns",),
        )
        red_lines = DecisionPipelineEngine._to_list(red_line_value)
        if not red_lines and isinstance(red_line_value, Mapping):
            red_lines = DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._to_mapping(red_line_value).keys()
            )
        knowledge_items = DecisionPipelineEngine._safe_int(
            DecisionPipelineEngine._read_mapping_field(package, ("knowledge_items_used",), default=0),
            default=0,
        )
        requires_followup = DecisionPipelineEngine._to_bool(
            DecisionPipelineEngine._read_mapping_field(package, ("requires_followup",), default=False)
        )
        return DecisionPackagingContract(
            final_outcome=outcome,
            mode=mode,
            confidence=confidence,
            recommendation=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(package, ("recommendation",), default="defer")
            ),
            council_outcome=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(package, ("council_outcome",), default="not_invoked")
            ),
            red_line_count=len(red_lines),
            knowledge_item_count=knowledge_items,
            requires_followup=bool(requires_followup),
            warning_count=0,
            source="decision_pipeline_fallback",
        )

    @staticmethod
    def _resolve_domain_contract(state: Mapping[str, Any]) -> DomainAnalysisContract:
        contract = DecisionPipelineEngine._read_mapping_field(state, ("domain_analysis_contract",))
        if isinstance(contract, DomainAnalysisContract):
            return contract

        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("routing_context",))
        )
        domains = DecisionPipelineEngine._to_list(
            DecisionPipelineEngine._read_mapping_field(routing_context, ("domains",))
        ) or ["strategy"]
        confidence = DecisionPipelineEngine._safe_float(
            DecisionPipelineEngine._read_mapping_field(
                routing_context,
                ("domain_confidence",),
                default=0.0,
            ),
            default=0.0,
        )

        scores = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(routing_context, ("domain_scores",))
        )
        domain_scores = {}
        for key, value in scores.items():
            try:
                domain_scores[str(key)] = float(value)
            except Exception:
                continue

        return DomainAnalysisContract(
            domains=[str(domain).strip().lower() for domain in domains if str(domain).strip()],
            domain_confidence=max(confidence, 0.0),
            stakes=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(routing_context, ("stakes",), default="medium")
            ),
            reversibility=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(
                    routing_context,
                    ("reversibility",),
                    default="partially_reversible",
                )
            ),
            key_entities=[
                str(item)
                for item in DecisionPipelineEngine._to_list(
                    DecisionPipelineEngine._read_mapping_field(routing_context, ("key_entities",))
                )
            ],
            domain_scores=domain_scores,
            source="decision_pipeline_fallback",
        )

    @staticmethod
    def _resolve_council_contract(state: Mapping[str, Any]) -> CouncilContract:
        council_contract = DecisionPipelineEngine._read_mapping_field(state, ("council_contract",))
        if isinstance(council_contract, CouncilContract):
            return council_contract

        council_result = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("council_result",))
        )
        return CouncilContract(
            outcome=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(council_result, ("outcome",), default="not_invoked")
            ),
            recommendation=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(council_result, ("recommendation",), default="defer")
            ),
            consensus_strength=DecisionPipelineEngine._safe_float(
                DecisionPipelineEngine._read_mapping_field(
                    council_result,
                    ("consensus_strength",),
                    default=0.0,
                ),
                default=0.0,
            ),
            minister_positions=DecisionPipelineEngine._to_mapping(
                DecisionPipelineEngine._read_mapping_field(council_result, ("minister_positions",))
            ),
            red_line_concerns=DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(council_result, ("red_line_concerns",))
            ),
        )

    @staticmethod
    def _resolve_knowledge_contract(state: Mapping[str, Any]) -> KnowledgeContract:
        knowledge_contract = DecisionPipelineEngine._read_mapping_field(state, ("knowledge_contract",))
        if isinstance(knowledge_contract, KnowledgeContract):
            return knowledge_contract

        domain_contract = DecisionPipelineEngine._resolve_domain_contract(state)
        knowledge_result = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("knowledge_result",))
        )
        routing_context = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("routing_context",))
        )
        return KnowledgeContract(
            active_domains=DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(knowledge_result, ("active_domains",))
                or domain_contract.domains
                or DecisionPipelineEngine._read_mapping_field(routing_context, ("domains",), default=[])
                or []
            ),
            synthesized_items=DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(knowledge_result, ("synthesized_knowledge",))
            ),
            trace=DecisionPipelineEngine._to_list(
                DecisionPipelineEngine._read_mapping_field(knowledge_result, ("knowledge_trace",))
            ),
            quality=DecisionPipelineEngine._to_mapping(
                DecisionPipelineEngine._read_mapping_field(knowledge_result, ("knowledge_quality",))
            ),
        )

    @staticmethod
    def _resolve_decision_contract(
        state: Mapping[str, Any],
        mode: str,
    ) -> DecisionContract:
        decision_contract = DecisionPipelineEngine._read_mapping_field(state, ("decision_contract",))
        if isinstance(decision_contract, DecisionContract):
            return decision_contract

        prime_decision = DecisionPipelineEngine._to_mapping(
            DecisionPipelineEngine._read_mapping_field(state, ("prime_decision",))
        )
        return DecisionContract(
            decision=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(prime_decision, ("final_outcome",), default="defer")
            ),
            confidence=DecisionPipelineEngine._safe_float(
                DecisionPipelineEngine._read_mapping_field(prime_decision, ("confidence",), default=0.0),
                default=0.0,
            ),
            rationale=DecisionPipelineEngine._normalize_text(
                DecisionPipelineEngine._read_mapping_field(prime_decision, ("reason",), default="")
            ),
            mode=mode,
            metadata={"source": "decision_pipeline_fallback"},
        )

    @staticmethod
    def _normalize_user_input(value: Any) -> str:
        if not isinstance(value, str):
            raise TypeError("DecisionPipelineEngine.run user_input must be a string.")
        return value

    @staticmethod
    def _normalize_source(value: Any) -> str:
        text = DecisionPipelineEngine._normalize_text(value)
        return text or "interactive"

    @staticmethod
    def _normalize_optional_scalar(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, (int, float, bool)):
            text = str(value).strip()
            return text or None
        return None

    @staticmethod
    def _safe_plugin_name(plugin: Any) -> str:
        try:
            name = str(plugin.name()).strip()
        except Exception:
            name = ""
        return name or "unknown_plugin"

    @staticmethod
    def _coerce_iterable_items(value: Any, *, preserve_partial: bool) -> tuple[List[Any], bool]:
        try:
            iterator = iter(value)
        except Exception:
            return [], True
        items: List[Any] = []
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

    @staticmethod
    def _to_mapping(value: Any) -> Dict[str, Any]:
        if isinstance(value, Mapping):
            try:
                raw_items = value.items()
            except Exception:
                return {}
            items, _ = DecisionPipelineEngine._coerce_iterable_items(
                raw_items,
                preserve_partial=True,
            )
            normalized: Dict[str, Any] = {}
            for key, item in items:
                text = DecisionPipelineEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = DecisionPipelineEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not raw_items:
                return {}
            normalized = {}
            for raw_item in raw_items:
                try:
                    key, item = raw_item
                except Exception:
                    return {}
                text = DecisionPipelineEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        return {}

    @staticmethod
    def _to_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray)):
            return []
        if isinstance(value, Mapping):
            return []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            items, _ = DecisionPipelineEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        if isinstance(value, Iterable):
            items, _ = DecisionPipelineEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        return []

    @staticmethod
    def _safe_int(value: Any, *, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any, *, default: float) -> float:
        try:
            numeric = float(value)
        except Exception:
            return default
        if not math.isfinite(numeric):
            return default
        return numeric

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = DecisionPipelineEngine._normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

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
            DecisionPipelineEngine._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _read_mapping_field(
        source: Mapping[str, Any],
        keys: Sequence[str],
        *,
        default: Any = None,
    ) -> Any:
        if not isinstance(source, Mapping):
            return default
        normalized_targets = {
            DecisionPipelineEngine._normalize_key_name(key)
            for key in keys
        }
        try:
            raw_items = source.items()
        except Exception:
            return default
        items, _ = DecisionPipelineEngine._coerce_iterable_items(
            raw_items,
            preserve_partial=True,
        )
        for raw_key, value in items:
            if DecisionPipelineEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default
