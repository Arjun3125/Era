from __future__ import annotations

import numpy as np

from core.contracts import ExecutionContext, InputContract
from modules.scenario_memory.module import ScenarioMemoryModule
from modules.scenario_memory.scenario_index import ScenarioIndex, ScenarioRecord


def test_scenario_memory_disabled_returns_empty() -> None:
    module = ScenarioMemoryModule()
    context = ExecutionContext(InputContract(user_input="Test prompt"))
    context.state["routing_context"] = {"scenario_memory_enabled": False}
    result = module.execute(context)
    assert result.metrics["scenario_memory_hits"] == 0
    assert result.outputs["scenario_memory_matches"] == []


def test_scenario_memory_retrieves_matches(tmp_path, monkeypatch) -> None:
    index = ScenarioIndex(dim=2, use_faiss=False)
    record = ScenarioRecord(
        scenario_id="S1",
        prompt="Competitor cuts prices",
        expected_decision="add premium features",
        category="strategy",
        difficulty="medium",
        context={"cash_reserve_months": 12},
    )
    index.add(np.array([1.0, 0.0], dtype="float32"), record)
    index_path = tmp_path / "scenario_index"
    index.save(index_path)

    class _DummyEmbedder:
        def __init__(self, *args, **kwargs):
            pass

        def embed(self, text: str):
            return np.array([1.0, 0.0], dtype="float32")

    monkeypatch.setattr(
        "modules.scenario_memory.module.ScenarioEmbedder",
        _DummyEmbedder,
    )

    module = ScenarioMemoryModule()
    context = ExecutionContext(InputContract(user_input="Competitor launches cheaper product"))
    context.state["routing_context"] = {
        "scenario_memory_enabled": True,
        "scenario_index_path": str(index_path),
        "scenario_memory_min_similarity": 0.1,
    }
    result = module.execute(context)
    assert result.metrics["scenario_memory_hits"] == 1
    assert result.outputs["scenario_memory_matches"][0]["scenario_id"] == "S1"
