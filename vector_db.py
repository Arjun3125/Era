"""Vector DB stub for tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class VectorIndexStub:
    data: List[Any] = field(default_factory=list)

    def add(self, record: Any) -> None:
        self.data.append(record)


class VectorDBStub:
    def __init__(self, storage_root: str = "data") -> None:
        self.combined_index = VectorIndexStub()
        self.base_index = VectorIndexStub()
        self.conflict_index = VectorIndexStub()
        self.strategy_index = VectorIndexStub()
        self.diplomacy_index = VectorIndexStub()
