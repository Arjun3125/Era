"""Tests for decision pipeline error normalization and summarization."""

from __future__ import annotations

from core.contracts import ErrorContract, ExecutionContext, InputContract, PipelineIssueContract
from core.orchestrator.runtime import OrchestrationResult, RunStatus
from modules.decision_pipeline.errors import DecisionPipelineErrorEngine


def _orchestration_result(*, errors: list[object]) -> OrchestrationResult:
    context = ExecutionContext(
        input_contract=InputContract(user_input="x"),
        errors=list(errors),
    )
    return OrchestrationResult(
        run_id="run-test",
        status=RunStatus.COMPLETED_WITH_ERRORS,
        context=context,
    )


class _PartialFailingIterable:
    def __iter__(self):
        yield "warn_alpha:warning:first"
        yield {
            "code": "warn_beta",
            "message": "warn_beta:error:second",
        }
        raise RuntimeError("iterator boom")


def test_error_engine_parses_structured_severity_from_stage_error_message():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(
            errors=[
                ErrorContract(
                    code="stage_error",
                    message="decision_package_type:error:decision_package must be dict.",
                    stage="contract_validation",
                    recoverable=True,
                )
            ]
        )
    )

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "decision_package_type"
    assert issue.severity == "error"
    assert issue.recoverable is True
    assert issue.stage == "contract_validation"

    assert result.summary.error_count == 1
    assert result.summary.warning_count == 0
    assert result.summary.fatal_count == 0
    assert result.summary.has_fatal is False


def test_error_engine_dedupes_across_sources_and_normalizes_warning_codes():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(
            errors=[
                ErrorContract(
                    code="telemetry_trace_stage_mismatch",
                    message="telemetry_trace_stage_mismatch:metrics=3,trace=2",
                    recoverable=False,
                    details={"stage": "telemetry"},
                )
            ]
        ),
        additional_warnings=[
            "telemetry_trace_stage_mismatch:metrics=3,trace=2",
            "custom_runtime_warn:warning:be careful",
            "",
        ],
    )

    assert len(result.issues) == 2
    mismatch = [item for item in result.issues if item.code == "telemetry_trace_stage_mismatch"][0]
    assert mismatch.severity == "warning"
    assert mismatch.recoverable is True
    assert mismatch.stage == "telemetry"

    assert result.summary.warning_count == 2
    assert result.summary.error_count == 0
    assert result.summary.fatal_count == 0
    assert result.summary.has_fatal is False


def test_error_engine_fatal_count_only_includes_non_recoverable_errors():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(
            errors=[
                ErrorContract(
                    code="stage_error",
                    message="RuntimeError: exploded",
                    stage="mode_routing",
                    recoverable=False,
                ),
                ErrorContract(
                    code="stage_error",
                    message="decision_package_followup_alignment:warning:followup mismatch",
                    stage="contract_validation",
                    recoverable=True,
                ),
            ]
        )
    )

    assert result.summary.error_count == 1
    assert result.summary.warning_count == 1
    assert result.summary.fatal_count == 1
    assert result.summary.has_fatal is True
    assert sorted(result.summary.stages_with_issues) == ["contract_validation", "mode_routing"]


def test_error_engine_accepts_structured_additional_issue_payloads():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(errors=[]),
        additional_warnings=[
            {
                "code": "slow_path",
                "message": "slow_path:warning:slow execution",
                "stage": "runtime",
                "details": {"latency_ms": 9000},
            },
            PipelineIssueContract(
                code="explicit_error",
                message="explicit failure",
                severity="error",
                stage="extension",
                recoverable=False,
                source="extension",
            ),
        ],
    )

    assert len(result.issues) == 2
    assert result.summary.error_count == 1
    assert result.summary.warning_count == 1
    assert result.summary.fatal_count == 1
    assert result.summary.has_fatal is True

    explicit_error = [item for item in result.issues if item.code == "explicit_error"][0]
    assert explicit_error.severity == "error"
    assert explicit_error.recoverable is False


def test_error_engine_treats_string_additional_warning_as_single_item():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(errors=[]),
        additional_warnings="single_warning:warning:hello",
    )

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "single_warning"
    assert issue.message == "hello"
    assert issue.severity == "warning"


def test_error_engine_normalizes_mapping_warning_with_invalid_details_and_bool_string():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(errors=[]),
        additional_warnings=[
            {
                "code": "custom_error",
                "message": "custom_error:error:boom",
                "details": "bad-details",
                "recoverable": "false",
            }
        ],
    )

    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "custom_error"
    assert issue.severity == "error"
    assert issue.recoverable is False
    assert issue.details == {}


def test_error_engine_handles_mapping_errors_from_context_collection():
    engine = DecisionPipelineErrorEngine()
    result_obj = _orchestration_result(errors=[])
    result_obj.context.errors = [  # type: ignore[assignment]
        {
            "code": "custom_stage_failure",
            "message": "custom_stage_failure:error:stage broke",
            "stage": "knowledge_synthesis",
            "recoverable": 1,
            "details": {"hint": "check source"},
        }
    ]

    result = engine.collect(result=result_obj)
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "custom_stage_failure"
    assert issue.message == "stage broke"
    assert issue.severity == "error"
    assert issue.recoverable is True
    assert issue.stage == "knowledge_synthesis"
    assert issue.details == {"hint": "check source"}


def test_error_engine_additional_warnings_accept_iterables_and_strict_bool_parsing():
    engine = DecisionPipelineErrorEngine()
    warnings_iter = iter(
        [
            "warn_alpha:warning:first",
            {
                "code": "warn_beta",
                "message": "warn_beta:error:second",
                "recoverable": 2,
            },
        ]
    )

    result = engine.collect(
        result=_orchestration_result(errors=[]),
        additional_warnings=warnings_iter,  # type: ignore[arg-type]
    )

    assert len(result.issues) == 2
    alpha = [item for item in result.issues if item.code == "warn_alpha"][0]
    beta = [item for item in result.issues if item.code == "warn_beta"][0]
    assert alpha.severity == "warning"
    assert alpha.recoverable is True
    assert beta.severity == "error"
    assert beta.recoverable is False


def test_error_engine_reads_normalized_mapping_keys_and_decodes_bytes():
    engine = DecisionPipelineErrorEngine()
    result_obj = _orchestration_result(errors=[])
    result_obj.context.errors = [  # type: ignore[assignment]
        {
            "co-de": "bad^code",
            "message": b"custom_issue:warning:decoded",
            "stage": "",
            "details": {"stage": "runtime"},
            "recoverable": b"1",
            "source": b"runtime_source",
        }
    ]

    result = engine.collect(result=result_obj)
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == "custom_issue"
    assert issue.message == "decoded"
    assert issue.severity == "warning"
    assert issue.recoverable is True
    assert issue.stage == "runtime"
    assert issue.source == "runtime_source"


def test_error_engine_preserves_partial_additional_warning_iterable_items():
    engine = DecisionPipelineErrorEngine()
    result = engine.collect(
        result=_orchestration_result(errors=[]),
        additional_warnings=_PartialFailingIterable(),  # type: ignore[arg-type]
    )

    assert len(result.issues) == 2
    assert sorted(issue.code for issue in result.issues) == ["warn_alpha", "warn_beta"]
