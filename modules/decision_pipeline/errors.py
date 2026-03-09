"""Error normalization and summarization for decision pipeline runs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Mapping, Sequence

from core.contracts import PipelineErrorSummaryContract, PipelineIssueContract
from core.orchestrator import OrchestrationResult


_SEVERITIES = {"warning", "error"}
_GENERIC_CODES = {"stage_error", "pipeline_warning", "pipeline_issue"}
_WARNING_CODES = {
    "pipeline_warning",
    "telemetry_sanitized",
    "telemetry_trace_stage_mismatch",
    "telemetry_trace_missing_stages",
}
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class DecisionPipelineErrorResult:
    """Normalized issue payload and aggregate summary."""

    summary: PipelineErrorSummaryContract
    issues: List[PipelineIssueContract] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


@dataclass
class DecisionPipelineErrorEngine:
    """Builds stable, typed error contracts from orchestrator outcomes."""

    def collect(
        self,
        *,
        result: OrchestrationResult,
        additional_warnings: Sequence[Any] | None = None,
    ) -> DecisionPipelineErrorResult:
        issues: List[PipelineIssueContract] = []

        for item in self._iter_errors(getattr(result.context, "errors", None)):
            issue = self._issue_from_error_contract(item)
            self._append_unique_issue(issues, issue)

        for warning in self._iter_additional_warnings(additional_warnings):
            issue = self._issue_from_additional_warning(warning)
            if issue is None:
                continue
            self._append_unique_issue(issues, issue)

        stage_set = sorted({issue.stage for issue in issues if issue.stage})
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(1 for issue in issues if issue.severity == "error")
        recoverable_count = sum(1 for issue in issues if issue.recoverable)
        fatal_count = sum(
            1 for issue in issues if issue.severity == "error" and not issue.recoverable
        )
        has_fatal = fatal_count > 0

        summary = PipelineErrorSummaryContract(
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            recoverable_count=recoverable_count,
            fatal_count=fatal_count,
            has_fatal=has_fatal,
            stages_with_issues=stage_set,
            source="decision_pipeline",
        )

        messages = [
            self._format_issue_message(issue)
            for issue in issues
        ]
        return DecisionPipelineErrorResult(
            summary=summary,
            issues=issues,
            messages=messages,
        )

    @staticmethod
    def _issue_from_error_contract(item: Any) -> PipelineIssueContract:
        if isinstance(item, PipelineIssueContract):
            details = DecisionPipelineErrorEngine._coerce_mapping(item.details)
            stage = DecisionPipelineErrorEngine._normalize_stage(item.stage, details=details)
            code = DecisionPipelineErrorEngine._normalize_code(item.code)
            message = DecisionPipelineErrorEngine._normalize_message(item.message)
            severity = DecisionPipelineErrorEngine._normalize_severity(
                item.severity,
                default=("warning" if bool(item.recoverable) else "error"),
            )
            recoverable = bool(item.recoverable) or severity == "warning"
            if code in _WARNING_CODES:
                severity = "warning"
                recoverable = True
            return PipelineIssueContract(
                code=code,
                message=message,
                severity=severity,
                stage=stage,
                recoverable=recoverable,
                source=str(item.source or "orchestrator"),
                details=details,
            )

        if isinstance(item, Mapping):
            details = DecisionPipelineErrorEngine._coerce_mapping(
                DecisionPipelineErrorEngine._read_mapping_field(item, ("details",), default={})
            )
            raw_code = DecisionPipelineErrorEngine._normalize_code(
                DecisionPipelineErrorEngine._read_mapping_field(
                    item,
                    ("code",),
                    default="stage_error",
                )
            )
            raw_message = DecisionPipelineErrorEngine._normalize_message(
                DecisionPipelineErrorEngine._read_mapping_field(item, ("message",), default="")
            )
            stage = DecisionPipelineErrorEngine._normalize_stage(
                DecisionPipelineErrorEngine._read_mapping_field(item, ("stage",), default=None),
                details=details,
            )
            recoverable = DecisionPipelineErrorEngine._to_bool(
                DecisionPipelineErrorEngine._read_mapping_field(item, ("recoverable",))
            )
            if recoverable is None:
                recoverable = False

            parsed = DecisionPipelineErrorEngine._parse_message(raw_message)
            code = parsed["code"] or raw_code
            message = parsed["message"]
            parsed_severity = parsed["severity"]

            default_severity = "warning" if recoverable else "error"
            severity = DecisionPipelineErrorEngine._normalize_severity(
                DecisionPipelineErrorEngine._read_mapping_field(
                    item,
                    ("severity",),
                    default=parsed_severity,
                ),
                default=default_severity,
            )
            if code in _WARNING_CODES:
                severity = "warning"
                recoverable = True
            elif severity == "warning":
                recoverable = True

            return PipelineIssueContract(
                code=code,
                message=message,
                severity=severity,
                stage=stage,
                recoverable=recoverable,
                source=DecisionPipelineErrorEngine._normalize_text(
                    DecisionPipelineErrorEngine._read_mapping_field(item, ("source",), default="orchestrator")
                )
                or "orchestrator",
                details=dict(details),
            )

        details = DecisionPipelineErrorEngine._coerce_mapping(getattr(item, "details", {}))
        raw_code = DecisionPipelineErrorEngine._normalize_code(
            getattr(item, "code", "stage_error")
        )
        raw_message = DecisionPipelineErrorEngine._normalize_message(
            getattr(item, "message", "")
        )
        stage = DecisionPipelineErrorEngine._normalize_stage(
            getattr(item, "stage", None),
            details=details,
        )
        recoverable = bool(getattr(item, "recoverable", False))

        parsed = DecisionPipelineErrorEngine._parse_message(raw_message)
        code = parsed["code"] or raw_code
        message = parsed["message"]
        parsed_severity = parsed["severity"]

        default_severity = "warning" if recoverable else "error"
        severity = DecisionPipelineErrorEngine._normalize_severity(
            parsed_severity,
            default=default_severity,
        )

        if code in _WARNING_CODES:
            severity = "warning"
            recoverable = True
        elif severity == "warning":
            recoverable = True

        return PipelineIssueContract(
            code=code,
            message=message,
            severity=severity,
            stage=stage,
            recoverable=recoverable,
            source=str(getattr(item, "source", "") or "orchestrator"),
            details=details,
        )

    @staticmethod
    def _issue_from_additional_warning(warning: Any) -> PipelineIssueContract | None:
        if isinstance(warning, PipelineIssueContract):
            issue = DecisionPipelineErrorEngine._issue_from_error_contract(warning)
            if issue.severity not in _SEVERITIES:
                issue.severity = "warning"
            issue.recoverable = bool(issue.recoverable) or issue.severity == "warning"
            issue.source = issue.source or "pipeline_runtime"
            return issue

        if isinstance(warning, Mapping):
            raw_code = DecisionPipelineErrorEngine._normalize_code(
                DecisionPipelineErrorEngine._read_mapping_field(
                    warning,
                    ("code",),
                    default="pipeline_warning",
                )
            )
            raw_message = DecisionPipelineErrorEngine._normalize_message(
                DecisionPipelineErrorEngine._read_mapping_field(warning, ("message",), default="")
            )
            if not raw_message:
                return None

            parsed = DecisionPipelineErrorEngine._parse_message(raw_message)
            code = parsed["code"] or raw_code
            severity = DecisionPipelineErrorEngine._normalize_severity(
                DecisionPipelineErrorEngine._read_mapping_field(
                    warning,
                    ("severity",),
                    default=parsed["severity"],
                ),
                default="warning",
            )
            if code in _WARNING_CODES:
                severity = "warning"
            stage = DecisionPipelineErrorEngine._normalize_stage(
                DecisionPipelineErrorEngine._read_mapping_field(warning, ("stage",)),
                details=DecisionPipelineErrorEngine._coerce_mapping(
                    DecisionPipelineErrorEngine._read_mapping_field(warning, ("details",), default={})
                ),
            )
            recoverable_raw = DecisionPipelineErrorEngine._read_mapping_field(
                warning,
                ("recoverable",),
            )
            recoverable = DecisionPipelineErrorEngine._to_bool(recoverable_raw)
            if recoverable is None:
                recoverable = severity == "warning"
            return PipelineIssueContract(
                code=code,
                message=parsed["message"],
                severity=severity,
                stage=stage,
                recoverable=recoverable,
                source=DecisionPipelineErrorEngine._normalize_text(
                    DecisionPipelineErrorEngine._read_mapping_field(
                        warning,
                        ("source",),
                        default="pipeline_runtime",
                    )
                )
                or "pipeline_runtime",
                details=DecisionPipelineErrorEngine._coerce_mapping(
                    DecisionPipelineErrorEngine._read_mapping_field(warning, ("details",), default={})
                ),
            )

        text = DecisionPipelineErrorEngine._normalize_message(warning)
        if not text:
            return None

        parsed = DecisionPipelineErrorEngine._parse_message(text)
        code = parsed["code"] or "pipeline_warning"
        severity = DecisionPipelineErrorEngine._normalize_severity(
            parsed["severity"],
            default="warning",
        )
        if code in _WARNING_CODES:
            severity = "warning"
        return PipelineIssueContract(
            code=code,
            message=parsed["message"],
            severity=severity,
            stage=None,
            recoverable=(severity == "warning"),
            source="pipeline_runtime",
        )

    @staticmethod
    def _append_unique_issue(
        issues: List[PipelineIssueContract],
        issue: PipelineIssueContract,
    ) -> None:
        for existing in issues:
            if (
                existing.code != issue.code
                or existing.message != issue.message
                or existing.severity != issue.severity
                or bool(existing.recoverable) != bool(issue.recoverable)
            ):
                continue

            # Treat missing stage as a wildcard duplicate and keep the richer stage.
            if existing.stage == issue.stage:
                return
            if not existing.stage and issue.stage:
                existing.stage = issue.stage
                if not existing.details and issue.details:
                    existing.details = DecisionPipelineErrorEngine._coerce_mapping(issue.details)
                return
            if existing.stage and not issue.stage:
                return

        issues.append(issue)

    @staticmethod
    def _parse_message(message: Any) -> Dict[str, Any]:
        clean_message = DecisionPipelineErrorEngine._normalize_message(message)
        if not clean_message:
            return {"code": "", "severity": "", "message": "unspecified_issue"}

        parts = [part.strip() for part in clean_message.split(":", 2)]
        if len(parts) == 3:
            code_part, severity_part, remainder = parts
            normalized_code = DecisionPipelineErrorEngine._normalize_code(code_part)
            normalized_severity = DecisionPipelineErrorEngine._normalize_severity(
                severity_part,
                default="",
            )
            if (
                normalized_code
                and normalized_severity in _SEVERITIES
                and remainder
            ):
                return {
                    "code": normalized_code,
                    "severity": normalized_severity,
                    "message": remainder,
                }

        if ":" in clean_message:
            prefix, remainder = clean_message.split(":", 1)
            normalized_code = DecisionPipelineErrorEngine._normalize_code(prefix)
            if normalized_code and normalized_code != "pipeline_issue" and remainder.strip():
                return {"code": normalized_code, "severity": "", "message": remainder.strip()}

        return {"code": "", "severity": "", "message": clean_message}

    @staticmethod
    def _format_issue_message(issue: PipelineIssueContract) -> str:
        return f"{issue.code}:{issue.message}"

    @staticmethod
    def _normalize_code(value: Any) -> str:
        raw = DecisionPipelineErrorEngine._normalize_text(value).lower()
        if not raw:
            return "pipeline_issue"
        if _CODE_PATTERN.match(raw):
            return raw
        collapsed = re.sub(r"[^a-z0-9_]+", "_", raw).strip("_")
        if collapsed and _CODE_PATTERN.match(collapsed):
            return collapsed
        return "pipeline_issue"

    @staticmethod
    def _normalize_message(value: Any) -> str:
        return DecisionPipelineErrorEngine._normalize_text(value)

    @staticmethod
    def _normalize_severity(value: Any, *, default: str) -> str:
        raw = DecisionPipelineErrorEngine._normalize_text(value).lower()
        if raw in _SEVERITIES:
            return raw
        return default

    @staticmethod
    def _normalize_stage(value: Any, *, details: Mapping[str, Any]) -> str | None:
        stage = DecisionPipelineErrorEngine._normalize_text(
            value
            or DecisionPipelineErrorEngine._read_mapping_field(details, ("stage",), default="")
            or ""
        )
        return stage or None

    @staticmethod
    def _coerce_mapping(value: Any) -> Dict[str, Any]:
        if isinstance(value, Mapping):
            try:
                raw_items = value.items()
            except Exception:
                return {}
            items, _ = DecisionPipelineErrorEngine._coerce_iterable_items(
                raw_items,
                preserve_partial=True,
            )
            normalized: Dict[str, Any] = {}
            for key, item in items:
                text = DecisionPipelineErrorEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
            raw_items, failed = DecisionPipelineErrorEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not raw_items:
                return {}
            normalized: Dict[str, Any] = {}
            for raw_item in raw_items:
                try:
                    key, item = raw_item
                except Exception:
                    return {}
                text = DecisionPipelineErrorEngine._normalize_text(key)
                if text:
                    normalized[text] = item
            return normalized
        return {}

    @staticmethod
    def _iter_errors(value: Any) -> List[Any]:
        if value in (None, ""):
            return []
        if isinstance(value, (str, bytes, bytearray)):
            return [value]
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            items, _ = DecisionPipelineErrorEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        if isinstance(value, Iterable):
            items, failed = DecisionPipelineErrorEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not items:
                return [value]
            return items
        return [value]

    @staticmethod
    def _iter_additional_warnings(value: Any) -> List[Any]:
        if value in (None, ""):
            return []
        if isinstance(value, (str, bytes, bytearray)):
            return [value]
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            items, _ = DecisionPipelineErrorEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            return items
        if isinstance(value, Iterable):
            items, failed = DecisionPipelineErrorEngine._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not items:
                return [value]
            return items
        return [value]

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
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = DecisionPipelineErrorEngine._normalize_text(value).lower()
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
            DecisionPipelineErrorEngine._normalize_text(value)
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
            DecisionPipelineErrorEngine._normalize_key_name(key)
            for key in keys
        }
        try:
            raw_items = source.items()
        except Exception:
            return default
        items, _ = DecisionPipelineErrorEngine._coerce_iterable_items(
            raw_items,
            preserve_partial=True,
        )
        for raw_key, value in items:
            if DecisionPipelineErrorEngine._normalize_key_name(raw_key) in normalized_targets:
                return value
        return default
