"""Inter-stage contract validation engine for decision pipeline runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
import math
from typing import Any, Dict, List, Mapping, Sequence

from core.contracts import (
    ContractValidationContract,
    CouncilContract,
    CouncilNormalizationContract,
    DecisionContract,
    DecisionPackagingContract,
    DomainAnalysisContract,
    KnowledgeContract,
    ModeResolutionContract,
    RequestContextContract,
    RuntimeConfigContract,
)


_DIRECT_COUNCIL_OUTCOMES = {
    "consensus_reached",
    "bounded_risk_tradeoff",
    "deadlocked",
    "quick_mode_direct_response",
    "council_disabled_ablation",
    "not_invoked",
    "contested",
    "engine_error",
}


def _coerce_iterable_items(
    value: Iterable[Any],
    *,
    preserve_partial: bool,
) -> tuple[List[Any], bool]:
    collected: List[Any] = []
    iterator = iter(value)
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            return collected, False
        except Exception:
            if preserve_partial:
                return collected, True
            return [], True
        collected.append(item)


def _coerce_mapping_like(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            source_items = value.items()
        except Exception:
            return {}
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
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
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = ContractValidationEngine._normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class ContractValidationResult:
    """Validation output for one pipeline state snapshot."""

    contract: ContractValidationContract
    issues: List[str]
    checks: Dict[str, str]


@dataclass
class ContractValidationEngine:
    """Validates end-to-end contract dependencies across pipeline state."""

    def validate(self, *, state: Mapping[str, Any]) -> ContractValidationResult:
        if not isinstance(state, Mapping):
            raise TypeError("state must be a mapping.")

        checks: Dict[str, str] = {}
        issues: List[str] = []

        request_contract = self._read_state_field(state, ("request_context_contract",))
        runtime_contract = self._read_state_field(state, ("runtime_config_contract",))
        mode_contract = self._read_state_field(state, ("mode_contract",))
        domain_contract = self._read_state_field(state, ("domain_analysis_contract",))
        knowledge_contract = self._read_state_field(state, ("knowledge_contract",))
        council_contract = self._read_state_field(state, ("council_contract",))
        council_normalization_contract = self._read_state_field(
            state,
            ("council_normalization_contract",),
        )
        decision_contract = self._read_state_field(state, ("decision_contract",))
        decision_packaging_contract = self._read_state_field(state, ("decision_packaging_contract",))
        decision_package_raw = self._read_state_field(state, ("decision_package",))
        routing_context_raw = self._read_state_field(state, ("routing_context",))
        decision_package = self._coerce_mapping(decision_package_raw)
        routing_context = self._coerce_mapping(routing_context_raw)

        self._assert_type(
            checks,
            issues,
            name="request_context_contract",
            value=request_contract,
            expected=RequestContextContract,
            severity_on_fail="error",
        )
        self._assert_type(
            checks,
            issues,
            name="runtime_config_contract",
            value=runtime_contract,
            expected=RuntimeConfigContract,
            severity_on_fail="error",
        )
        self._assert_type(
            checks,
            issues,
            name="mode_contract",
            value=mode_contract,
            expected=ModeResolutionContract,
            severity_on_fail="warning",
        )
        self._assert_type(
            checks,
            issues,
            name="domain_analysis_contract",
            value=domain_contract,
            expected=DomainAnalysisContract,
            severity_on_fail="warning",
        )
        self._assert_type(
            checks,
            issues,
            name="knowledge_contract",
            value=knowledge_contract,
            expected=KnowledgeContract,
            severity_on_fail="warning",
        )
        self._assert_type(
            checks,
            issues,
            name="council_contract",
            value=council_contract,
            expected=CouncilContract,
            severity_on_fail="warning",
        )
        self._assert_type(
            checks,
            issues,
            name="council_normalization_contract",
            value=council_normalization_contract,
            expected=CouncilNormalizationContract,
            severity_on_fail="warning",
        )
        self._assert_type(
            checks,
            issues,
            name="decision_contract",
            value=decision_contract,
            expected=DecisionContract,
            severity_on_fail="error",
        )
        self._assert_type(
            checks,
            issues,
            name="decision_packaging_contract",
            value=decision_packaging_contract,
            expected=DecisionPackagingContract,
            severity_on_fail="error",
        )

        if self._is_mapping_like(decision_package_raw):
            checks["decision_package_type"] = "pass"
        else:
            self._add_issue(
                checks,
                issues,
                name="decision_package_type",
                severity="error",
                message="decision_package must be dict.",
            )

        if self._is_mapping_like(routing_context_raw):
            checks["routing_context_type"] = "pass"
        else:
            self._add_issue(
                checks,
                issues,
                name="routing_context_type",
                severity="error",
                message="routing_context must be dict.",
            )

        if isinstance(runtime_contract, RuntimeConfigContract):
            if runtime_contract.decision_pipeline_enabled:
                checks["runtime_pipeline_enabled"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="runtime_pipeline_enabled",
                    severity="warning",
                    message="runtime config has decision_pipeline_enabled=false.",
                )

        if isinstance(domain_contract, DomainAnalysisContract):
            if self._collect_iterable_values(domain_contract.domains):
                checks["domain_non_empty"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="domain_non_empty",
                    severity="warning",
                    message="domain_analysis_contract.domains is empty.",
                )

        if isinstance(knowledge_contract, KnowledgeContract):
            active_domains = [
                str(item).strip().lower()
                for item in self._collect_iterable_values(knowledge_contract.active_domains)
            ]
            if active_domains:
                checks["knowledge_active_domains_non_empty"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="knowledge_active_domains_non_empty",
                    severity="warning",
                    message="knowledge_contract.active_domains is empty.",
                )

            if isinstance(domain_contract, DomainAnalysisContract):
                primary = {
                    str(item).strip().lower()
                    for item in self._collect_iterable_values(domain_contract.domains)
                    if str(item).strip()
                }
                if primary and active_domains:
                    overlap = primary.intersection(set(active_domains))
                    if overlap:
                        checks["knowledge_domain_alignment"] = "pass"
                    else:
                        self._add_issue(
                            checks,
                            issues,
                            name="knowledge_domain_alignment",
                            severity="warning",
                            message="knowledge active domains do not overlap domain analysis.",
                        )

        if isinstance(mode_contract, ModeResolutionContract):
            if mode_contract.should_invoke_council and not self._collect_iterable_values(
                mode_contract.selected_ministers
            ):
                self._add_issue(
                    checks,
                    issues,
                    name="council_readiness",
                    severity="warning",
                    message="mode requires council but selected_ministers is empty.",
                )
            else:
                checks["council_readiness"] = "pass"

        if (
            isinstance(mode_contract, ModeResolutionContract)
            and isinstance(council_contract, CouncilContract)
            and mode_contract.should_invoke_council
            and council_contract.outcome == "not_invoked"
        ):
            self._add_issue(
                checks,
                issues,
                name="council_invocation_alignment",
                severity="warning",
                message="mode requires council but council outcome is not_invoked.",
            )
        elif isinstance(mode_contract, ModeResolutionContract) and isinstance(council_contract, CouncilContract):
            checks["council_invocation_alignment"] = "pass"

        if (
            isinstance(mode_contract, ModeResolutionContract)
            and isinstance(council_normalization_contract, CouncilNormalizationContract)
        ):
            if mode_contract.mode == council_normalization_contract.mode:
                checks["council_normalization_mode_alignment"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="council_normalization_mode_alignment",
                    severity="warning",
                    message="normalized council mode does not match mode contract.",
                )

        if (
            isinstance(council_contract, CouncilContract)
            and isinstance(council_normalization_contract, CouncilNormalizationContract)
        ):
            council_outcome = self._normalize_council_outcome(council_contract.outcome)
            normalized_outcome = self._normalize_council_outcome(council_normalization_contract.outcome)
            if council_outcome == normalized_outcome:
                checks["council_outcome_alignment"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="council_outcome_alignment",
                    severity="warning",
                    message="council contract outcome differs from normalized council outcome.",
                )

            council_recommendation = self._normalize_council_recommendation(
                council_contract.recommendation
            )
            normalized_recommendation = self._normalize_council_recommendation(
                council_normalization_contract.recommendation
            )
            if council_recommendation == normalized_recommendation:
                checks["council_recommendation_alignment"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="council_recommendation_alignment",
                    severity="warning",
                    message="council contract recommendation differs from normalized council recommendation.",
                )

        if isinstance(decision_packaging_contract, DecisionPackagingContract):
            if isinstance(mode_contract, ModeResolutionContract):
                if decision_packaging_contract.mode == mode_contract.mode:
                    checks["decision_packaging_mode_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_packaging_mode_alignment",
                        severity="warning",
                        message="decision packaging mode differs from mode contract.",
                    )

            if isinstance(decision_contract, DecisionContract):
                if decision_contract.decision == decision_packaging_contract.final_outcome:
                    checks["decision_contract_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_contract_alignment",
                        severity="warning",
                        message="decision contract outcome differs from packaged final outcome.",
                    )

                if decision_contract.mode == decision_packaging_contract.mode:
                    checks["decision_contract_mode_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_contract_mode_alignment",
                        severity="warning",
                        message="decision contract mode differs from packaged mode.",
                    )

                if self._approximately_equal(
                    decision_contract.confidence,
                    decision_packaging_contract.confidence,
                ):
                    checks["decision_contract_confidence_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_contract_confidence_alignment",
                        severity="warning",
                        message="decision contract confidence differs from packaged confidence.",
                    )

        if (
            isinstance(decision_packaging_contract, DecisionPackagingContract)
            and self._is_mapping_like(decision_package_raw)
        ):
            packaged_outcome = self._normalize_text(
                self._read_mapping_field(decision_package, ("final_outcome",))
            ).lower()
            if (
                packaged_outcome
                and packaged_outcome != decision_packaging_contract.final_outcome
            ):
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_outcome_alignment",
                    severity="warning",
                    message="decision_package.final_outcome does not match packaging contract.",
                )
            else:
                checks["decision_package_outcome_alignment"] = "pass"

            packaged_mode = self._normalize_text(
                self._read_mapping_field(decision_package, ("mode",))
            ).lower()
            if packaged_mode and packaged_mode != decision_packaging_contract.mode:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_mode_alignment",
                    severity="warning",
                    message="decision_package.mode does not match packaging contract.",
                )
            else:
                checks["decision_package_mode_alignment"] = "pass"

            packaged_recommendation = self._normalize_text(
                self._read_mapping_field(decision_package, ("recommendation",))
            ).lower()
            if (
                packaged_recommendation
                and packaged_recommendation != decision_packaging_contract.recommendation
            ):
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_recommendation_alignment",
                    severity="warning",
                    message="decision_package.recommendation does not match packaging contract.",
                )
            else:
                checks["decision_package_recommendation_alignment"] = "pass"

            packaged_council_outcome = self._normalize_text(
                self._read_mapping_field(decision_package, ("council_outcome",))
            ).lower()
            if (
                packaged_council_outcome
                and packaged_council_outcome != decision_packaging_contract.council_outcome
            ):
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_council_outcome_alignment",
                    severity="warning",
                    message="decision_package.council_outcome does not match packaging contract.",
                )
            else:
                checks["decision_package_council_outcome_alignment"] = "pass"

            raw_followup = self._read_mapping_field(decision_package, ("requires_followup",))
            if raw_followup is not None:
                if self._to_bool(raw_followup) == bool(
                    decision_packaging_contract.requires_followup
                ):
                    checks["decision_package_followup_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_package_followup_alignment",
                        severity="warning",
                        message="decision_package.requires_followup does not match packaging contract.",
                    )

            red_line_count = self._to_int(
                self._read_mapping_field(decision_package, ("red_line_concerns",))
            )
            if red_line_count is None:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_red_line_shape",
                    severity="warning",
                    message="decision_package.red_line_concerns is not countable.",
                )
            elif red_line_count == decision_packaging_contract.red_line_count:
                checks["decision_package_red_line_count_alignment"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_red_line_count_alignment",
                    severity="warning",
                    message="decision_package red_line_concerns count does not match packaging contract.",
                )

            knowledge_items = self._to_int(
                self._read_mapping_field(decision_package, ("knowledge_items_used",))
            )
            if knowledge_items is None:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_knowledge_count_shape",
                    severity="warning",
                    message="decision_package.knowledge_items_used is not countable/int-like.",
                )
            elif knowledge_items == decision_packaging_contract.knowledge_item_count:
                checks["decision_package_knowledge_count_alignment"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_package_knowledge_count_alignment",
                    severity="warning",
                    message="decision_package knowledge_items_used does not match packaging contract.",
                )

            package_confidence = self._to_float(
                self._read_mapping_field(decision_package, ("confidence",))
            )
            if package_confidence is None or not math.isfinite(package_confidence):
                self._add_issue(
                    checks,
                    issues,
                    name="decision_confidence_range",
                    severity="warning",
                    message="decision package confidence is not finite.",
                )
            elif 0.0 <= package_confidence <= 1.0:
                checks["decision_confidence_range"] = "pass"
            else:
                self._add_issue(
                    checks,
                    issues,
                    name="decision_confidence_range",
                    severity="warning",
                    message="decision package confidence is outside [0.0, 1.0].",
                )

            if package_confidence is not None and math.isfinite(package_confidence):
                if self._approximately_equal(package_confidence, decision_packaging_contract.confidence):
                    checks["decision_package_confidence_alignment"] = "pass"
                else:
                    self._add_issue(
                        checks,
                        issues,
                        name="decision_package_confidence_alignment",
                        severity="warning",
                        message="decision_package.confidence does not match packaging contract.",
                    )

        issues = self._dedupe_issues(issues)

        warning_checks = sorted([name for name, status in checks.items() if status == "warning"])
        failed_checks = sorted([name for name, status in checks.items() if status == "error"])
        warning_count = len(warning_checks)
        error_count = len(failed_checks)

        contract = ContractValidationContract(
            passed=(error_count == 0),
            warning_count=warning_count,
            error_count=error_count,
            warning_checks=warning_checks,
            failed_checks=failed_checks,
            checks=dict(checks),
            source="contract_validation",
        )
        return ContractValidationResult(
            contract=contract,
            issues=issues,
            checks=checks,
        )

    @staticmethod
    def _assert_type(
        checks: Dict[str, str],
        issues: List[str],
        *,
        name: str,
        value: Any,
        expected: type,
        severity_on_fail: str,
    ) -> None:
        if isinstance(value, expected):
            checks[name] = "pass"
            return
        ContractValidationEngine._add_issue(
            checks,
            issues,
            name=name,
            severity=severity_on_fail,
            message=f"expected {expected.__name__}, got {type(value).__name__}.",
        )

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(ContractValidationEngine._normalize_text(value))
        except Exception:
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            try:
                source_items = value.items()
            except Exception:
                return None
            items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
            return len(items)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return len(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, Mapping)):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            return len(items)
        text = ContractValidationEngine._normalize_text(value)
        if not text:
            return None
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            try:
                return int(text)
            except Exception:
                return None
        try:
            numeric = float(text)
        except Exception:
            return None
        if not math.isfinite(numeric):
            return None
        if numeric.is_integer():
            return int(numeric)
        return None

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = ContractValidationEngine._normalize_text(value).lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return None

    @staticmethod
    def _read_state_field(state: Mapping[str, Any], keys: Sequence[str]) -> Any:
        normalized_targets = {ContractValidationEngine._normalize_key_name(key) for key in keys}
        try:
            source_items = state.items()
        except Exception:
            return None
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
        for raw_key, value in items:
            if ContractValidationEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return None

    @staticmethod
    def _read_mapping_field(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
        if not isinstance(payload, Mapping):
            return None
        normalized_targets = {ContractValidationEngine._normalize_key_name(key) for key in keys}
        try:
            source_items = payload.items()
        except Exception:
            return None
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
        for raw_key, value in items:
            if ContractValidationEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return None

    @staticmethod
    def _coerce_mapping(value: Any) -> Dict[str, Any]:
        mapping_like = _coerce_mapping_like(value)
        if mapping_like is not None:
            return mapping_like
        if isinstance(value, (str, bytes, bytearray)):
            text = ContractValidationEngine._normalize_text(value)
            if not text:
                return {}
            try:
                parsed = json.loads(text)
            except Exception:
                return {}
            parsed_mapping = _coerce_mapping_like(parsed)
            if parsed_mapping is not None:
                return parsed_mapping
        return {}

    @staticmethod
    def _is_mapping_like(value: Any) -> bool:
        if _coerce_mapping_like(value) is not None:
            return True
        if isinstance(value, (str, bytes, bytearray)):
            text = ContractValidationEngine._normalize_text(value)
            if not text:
                return False
            try:
                parsed = json.loads(text)
            except Exception:
                return False
            return _coerce_mapping_like(parsed) is not None
        return False

    @staticmethod
    def _approximately_equal(left: Any, right: Any, *, tolerance: float = 1e-6) -> bool:
        left_value = ContractValidationEngine._to_float(left)
        right_value = ContractValidationEngine._to_float(right)
        if left_value is None or right_value is None:
            return False
        if not math.isfinite(left_value) or not math.isfinite(right_value):
            return False
        return abs(left_value - right_value) <= tolerance

    @staticmethod
    def _add_issue(
        checks: Dict[str, str],
        issues: List[str],
        *,
        name: str,
        severity: str,
        message: str,
    ) -> None:
        checks[name] = severity
        issues.append(f"{name}:{severity}:{message}")

    @staticmethod
    def _dedupe_issues(issues: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for issue in issues:
            if issue in seen:
                continue
            seen.add(issue)
            deduped.append(issue)
        return deduped

    @staticmethod
    def _normalize_council_outcome(value: Any) -> str:
        raw = ContractValidationEngine._normalize_text(value).lower()
        if raw in {"balanced"}:
            return "bounded_risk_tradeoff"
        if raw in {"consensus"}:
            return "consensus_reached"
        if raw in _DIRECT_COUNCIL_OUTCOMES:
            return raw
        return raw or "not_invoked"

    @staticmethod
    def _normalize_council_recommendation(value: Any) -> str:
        raw = ContractValidationEngine._normalize_text(value).lower()
        if raw in {"support", "oppose", "defer"}:
            return raw

        support_tokens = {
            "strong_consensus_support",
            "strong_doctrine_aligned_consensus",
            "aggressive_proceed",
            "proceed_with_confidence",
            "proceed_with_caution",
            "consensus_with_noted_dissent",
            "support_with_caution",
            "accept",
            "accept_with_mitigation",
        }
        oppose_tokens = {
            "strong_consensus_oppose",
            "red_line_blocks_recommendation",
            "red_line_block_override_needed",
            "defensive_hold_or_pivot",
            "reject",
        }
        defer_tokens = {
            "deep_disagreement_defer_decision",
            "mixed_consensus_with_tradeoffs",
            "insufficient_data",
            "unknown_mode",
            "direct_response",
            "no_council_response",
            "use_direct_llm_response",
            "",
        }
        if raw in support_tokens:
            return "support"
        if raw in oppose_tokens:
            return "oppose"
        if raw in defer_tokens:
            return "defer"
        return "defer"

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
            ContractValidationEngine._normalize_text(value)
            .lower()
            .replace("-", "_")
            .replace(".", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )

    @staticmethod
    def _collect_iterable_values(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (str, bytes, bytearray, Mapping)):
            return []
        if isinstance(value, Sequence):
            return list(value)
        if isinstance(value, Iterable):
            items, _ = _coerce_iterable_items(value, preserve_partial=True)
            return items
        return []
