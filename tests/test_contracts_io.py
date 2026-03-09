"""Tests for io contract dataclass normalization."""

from __future__ import annotations

from core.contracts import (
    IO_CONTRACT_TYPES,
    DecisionContract,
    DomainAnalysisContract,
    ErrorContract,
    InputContract,
    KnowledgeContract,
    PipelineErrorSummaryContract,
    PipelineIssueContract,
    RuntimeConfigContract,
)


def test_input_contract_normalizes_values():
    contract = InputContract(
        user_input=123,  # type: ignore[arg-type]
        source=" ",
        session_id=" ",
        metadata=["bad"],  # type: ignore[arg-type]
        timestamp=" ",
    )
    assert contract.user_input == "123"
    assert contract.source == "interactive"
    assert contract.session_id is None
    assert contract.metadata == {}
    assert contract.timestamp


def test_input_contract_preserves_scalar_zero_values():
    contract = InputContract(
        user_input=0,  # type: ignore[arg-type]
        source=0,  # type: ignore[arg-type]
        session_id=0,  # type: ignore[arg-type]
    )
    assert contract.user_input == "0"
    assert contract.source == "0"
    assert contract.session_id == "0"


def test_runtime_config_contract_normalizes_booleans_and_overrides():
    contract = RuntimeConfigContract(
        orchestrator_strict="true",  # type: ignore[arg-type]
        observability_enabled="0",  # type: ignore[arg-type]
        observability_emit_summary="yes",  # type: ignore[arg-type]
        observability_write_file="on",  # type: ignore[arg-type]
        overrides_applied="x",  # type: ignore[arg-type]
    )
    assert contract.orchestrator_strict is True
    assert contract.observability_enabled is False
    assert contract.observability_emit_summary is True
    assert contract.observability_write_file is True
    assert contract.overrides_applied == []


def test_runtime_config_contract_accepts_iterable_overrides():
    contract = RuntimeConfigContract(overrides_applied=(item for item in ["x", "x", "y"]))
    assert contract.overrides_applied == ["x", "y"]


def test_pipeline_issue_and_summary_contracts_normalize_payloads():
    issue = PipelineIssueContract(
        code=" ",
        message=" ",
        severity="bad",
        stage=" ",
        recoverable="1",  # type: ignore[arg-type]
        details=["bad"],  # type: ignore[arg-type]
    )
    assert issue.code == "pipeline_issue"
    assert issue.message == "unspecified_issue"
    assert issue.severity == "error"
    assert issue.stage is None
    assert issue.recoverable is True
    assert issue.details == {}

    summary = PipelineErrorSummaryContract(
        issue_count="4",  # type: ignore[arg-type]
        error_count=-2,  # type: ignore[arg-type]
        fatal_count=2,
        has_fatal=False,
        stages_with_issues=["x", "x", " "],
    )
    assert summary.issue_count == 4
    assert summary.error_count == 0
    assert summary.fatal_count == 2
    assert summary.has_fatal is True
    assert summary.stages_with_issues == ["x"]


def test_domain_knowledge_decision_error_contracts_are_defensive():
    domain = DomainAnalysisContract(
        domains=[" Strategy ", 1, ""],  # type: ignore[list-item]
        domain_confidence=float("nan"),
        key_entities="entity",  # type: ignore[arg-type]
        domain_scores={"a": "1.25", "b": "bad"},
        source=" ",
    )
    assert domain.domains == ["strategy", "1"]
    assert domain.domain_confidence == 0.0
    assert domain.key_entities == []
    assert domain.domain_scores == {"a": 1.25}
    assert domain.source == "heuristic"

    knowledge = KnowledgeContract(
        active_domains="single",  # type: ignore[arg-type]
        synthesized_items=["a", " ", "a"],
        trace=[{"k": 1}, "bad"],  # type: ignore[list-item]
        quality=["bad"],  # type: ignore[arg-type]
    )
    assert knowledge.active_domains == []
    assert knowledge.synthesized_items == ["a"]
    assert knowledge.trace == [{"k": 1}]
    assert knowledge.quality == {}

    decision = DecisionContract(
        decision=" ",
        confidence="bad",  # type: ignore[arg-type]
        mode=" ",
        metadata=["bad"],  # type: ignore[arg-type]
    )
    assert decision.decision == "defer"
    assert decision.confidence == 0.0
    assert decision.mode == "meeting"
    assert decision.metadata == {}

    error = ErrorContract(code=" ", message=" ", stage=" ", recoverable="false", details=1)  # type: ignore[arg-type]
    assert error.code == "runtime_error"
    assert error.message == "unspecified_error"
    assert error.stage is None
    assert error.recoverable is False
    assert error.details == {}


def test_domain_and_knowledge_contracts_accept_iterables():
    domain = DomainAnalysisContract(domains=(item for item in ["A", "A", "b"]))
    assert domain.domains == ["a", "b"]

    knowledge = KnowledgeContract(
        active_domains=(item for item in ["x", "x"]),
        trace=(item for item in [{"k": 1}, "bad"]),
    )
    assert knowledge.active_domains == ["x"]
    assert knowledge.trace == [{"k": 1}]


def test_core_contracts_exports_io_contract_types():
    names = {item.__name__ for item in IO_CONTRACT_TYPES}
    assert "InputContract" in names
    assert "RuntimeConfigContract" in names


def test_io_contracts_accept_iterable_mappings_and_bytes_scalars():
    input_contract = InputContract(
        user_input=b"hello",  # type: ignore[arg-type]
        metadata=[(b"route", "x")],  # type: ignore[arg-type]
    )
    runtime_contract = RuntimeConfigContract(
        observability_enabled=b"0",  # type: ignore[arg-type]
        observability_emit_summary=b"1",  # type: ignore[arg-type]
    )
    issue = PipelineIssueContract(
        code=b"issue_code",  # type: ignore[arg-type]
        message=b"issue_message",  # type: ignore[arg-type]
        details=[("k", "v")],  # type: ignore[arg-type]
    )

    assert input_contract.user_input == "hello"
    assert input_contract.metadata == {"route": "x"}
    assert runtime_contract.observability_enabled is False
    assert runtime_contract.observability_emit_summary is True
    assert issue.code == "issue_code"
    assert issue.message == "issue_message"
    assert issue.details == {"k": "v"}


def test_io_mapping_normalization_preserves_first_normalized_key():
    contract = InputContract(
        user_input="x",
        metadata=[(b"route", "first"), ("route", "second")],  # type: ignore[arg-type]
    )
    assert contract.metadata == {"route": "first"}


def test_io_mapping_normalization_ignores_invalid_iterable_shape():
    issue = PipelineIssueContract(
        code="issue",
        message="message",
        details=[("k", "v", "extra")],  # type: ignore[arg-type]
    )
    assert issue.details == {}


def test_io_sequence_normalization_keeps_partial_items_from_faulty_iterable():
    class _FaultyIterable:
        def __iter__(self):
            return self

        def __next__(self):
            index = getattr(self, "_index", 0)
            self._index = index + 1
            if index == 0:
                return " Alpha "
            raise RuntimeError("boom")

    domain = DomainAnalysisContract(domains=_FaultyIterable())  # type: ignore[arg-type]
    assert domain.domains == ["alpha"]
