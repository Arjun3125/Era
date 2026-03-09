"""Extension stage contracts for decision pipeline customization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence

from core.contracts import ExecutionContext


@dataclass(frozen=True)
class ExtensionStageSpec:
    """Declarative stage registration payload for pipeline extension points."""

    name: str
    handler: Callable[[ExecutionContext], Any]
    on_error: str = "degrade"
    before: Optional[str] = None
    after: Optional[str] = None
    source: str = "runtime"


@dataclass
class ExtensionStagePlanner:
    """Deterministic planner for anchoring extension stages into base plans."""

    valid_error_policies: tuple[str, str] = ("abort", "degrade")

    def compose(
        self,
        *,
        base_plan: Sequence[ExtensionStageSpec],
        extensions: Sequence[ExtensionStageSpec],
    ) -> List[ExtensionStageSpec]:
        base_items = self._coerce_spec_sequence(base_plan, name="base_plan")
        extension_items = self._coerce_spec_sequence(extensions, name="extensions")

        plan = [self._clone(item) for item in base_items]
        self._validate_base_plan(plan)
        self._validate_extensions(extensions=extension_items, base_plan=plan)

        unresolved = [self._clone(item) for item in extension_items]
        while unresolved:
            next_round: List[ExtensionStageSpec] = []
            progressed = False
            for extension in unresolved:
                inserted = self._try_insert(plan=plan, extension=extension)
                if inserted:
                    progressed = True
                else:
                    next_round.append(extension)

            if progressed:
                unresolved = next_round
                continue

            unresolved_names = [item.name for item in next_round]
            unresolved_anchors = [
                f"{item.name}(before={item.before!r},after={item.after!r})"
                for item in next_round
            ]
            raise ValueError(
                "Unresolvable extension anchors (missing or cyclic): "
                f"{', '.join(unresolved_anchors)}; unresolved_names={unresolved_names}"
            )

        return plan

    def _try_insert(
        self,
        *,
        plan: List[ExtensionStageSpec],
        extension: ExtensionStageSpec,
    ) -> bool:
        if extension.before:
            index = self._find_stage_index(plan, extension.before)
            if index is None:
                return False
            plan.insert(index, extension)
            return True

        if extension.after:
            insertion_index = self._find_after_insertion_index(plan, extension.after)
            if insertion_index is None:
                return False
            plan.insert(insertion_index, extension)
            return True

        plan.append(extension)
        return True

    def _validate_base_plan(self, plan: Sequence[ExtensionStageSpec]) -> None:
        seen = set()
        for item in self._coerce_spec_sequence(plan, name="base_plan"):
            name = str(item.name).strip()
            if not name:
                raise ValueError("Base stage name must be non-empty.")
            if name in seen:
                raise ValueError(f"Duplicate base stage name '{name}'.")
            if item.on_error not in self.valid_error_policies:
                raise ValueError(
                    f"Base stage '{name}' on_error must be one of {self.valid_error_policies}."
                )
            if not callable(item.handler):
                raise TypeError(f"Base stage '{name}' handler must be callable.")
            seen.add(name)

    def _validate_extensions(
        self,
        *,
        extensions: Sequence[ExtensionStageSpec],
        base_plan: Sequence[ExtensionStageSpec],
    ) -> None:
        base_names = {
            item.name for item in self._coerce_spec_sequence(base_plan, name="base_plan")
        }
        extension_names = set()
        normalized_extensions = [
            self._clone(item)
            for item in self._coerce_spec_sequence(extensions, name="extensions")
        ]
        known_names = base_names.union({item.name for item in normalized_extensions})
        for item in normalized_extensions:
            name = str(item.name).strip()
            if not name:
                raise ValueError("Extension stage name must be non-empty.")
            if name in base_names:
                raise ValueError(f"Stage '{name}' conflicts with existing pipeline stage.")
            if name in extension_names:
                raise ValueError(f"Extension stage '{name}' already registered.")
            extension_names.add(name)

            if item.before and item.after:
                raise ValueError(
                    f"Extension stage '{name}' cannot specify both 'before' and 'after'."
                )
            if item.on_error not in self.valid_error_policies:
                raise ValueError(
                    f"Extension stage '{name}' on_error must be one of {self.valid_error_policies}."
                )
            if not callable(item.handler):
                raise TypeError(
                    f"Extension stage '{name}' handler must be callable."
                )
            if item.before and str(item.before).strip() == name:
                raise ValueError(f"Extension stage '{name}' cannot anchor before itself.")
            if item.after and str(item.after).strip() == name:
                raise ValueError(f"Extension stage '{name}' cannot anchor after itself.")
            if item.before and str(item.before).strip() not in known_names:
                raise ValueError(
                    f"Extension stage '{name}' anchors before unknown stage '{item.before}'."
                )
            if item.after and str(item.after).strip() not in known_names:
                raise ValueError(
                    f"Extension stage '{name}' anchors after unknown stage '{item.after}'."
                )

    @staticmethod
    def _find_stage_index(
        plan: Sequence[ExtensionStageSpec],
        anchor: str,
    ) -> Optional[int]:
        target = str(anchor).strip()
        for index, item in enumerate(
            ExtensionStagePlanner._coerce_spec_sequence(plan, name="plan")
        ):
            if item.name == target:
                return index
        return None

    @staticmethod
    def _find_after_insertion_index(
        plan: Sequence[ExtensionStageSpec],
        anchor: str,
    ) -> Optional[int]:
        anchor_index = ExtensionStagePlanner._find_stage_index(plan, anchor)
        if anchor_index is None:
            return None

        insertion_index = anchor_index + 1
        while insertion_index < len(plan):
            candidate = plan[insertion_index]
            if str(candidate.after or "").strip() != str(anchor).strip():
                break
            insertion_index += 1
        return insertion_index

    @staticmethod
    def _clone(item: ExtensionStageSpec) -> ExtensionStageSpec:
        return ExtensionStageSpec(
            name=ExtensionStagePlanner._normalize_text(item.name),
            handler=item.handler,
            on_error=ExtensionStagePlanner._normalize_text(item.on_error).lower(),
            before=ExtensionStagePlanner._normalize_text(item.before) if item.before else None,
            after=ExtensionStagePlanner._normalize_text(item.after) if item.after else None,
            source=ExtensionStagePlanner._normalize_text(item.source) or "runtime",
        )

    @staticmethod
    def _coerce_spec_sequence(value: Any, *, name: str) -> List[ExtensionStageSpec]:
        if value in (None, ""):
            return []
        if isinstance(value, (str, bytes, bytearray)):
            raise TypeError(f"{name} must be a sequence of ExtensionStageSpec.")
        if isinstance(value, Sequence):
            items, _ = ExtensionStagePlanner._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
        elif isinstance(value, Iterable):
            items, failed = ExtensionStagePlanner._coerce_iterable_items(
                value,
                preserve_partial=True,
            )
            if failed and not items:
                raise TypeError(f"{name} must be a sequence of ExtensionStageSpec.")
        else:
            raise TypeError(f"{name} must be a sequence of ExtensionStageSpec.")
        for index, item in enumerate(items):
            if not isinstance(item, ExtensionStageSpec):
                raise TypeError(
                    f"{name}[{index}] must be ExtensionStageSpec."
                )
        return items

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
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace").strip()
        return str(value).strip()
