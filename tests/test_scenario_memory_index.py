import numpy as np

from modules.scenario_memory.retrieval import ScenarioRetriever
from modules.scenario_memory.scenario_index import ScenarioIndex, ScenarioRecord


class DummyEmbedder:
    def __init__(self, vector):
        self._vector = np.asarray(vector, dtype="float32")

    def embed(self, _text):
        return self._vector


def test_scenario_index_search():
    index = ScenarioIndex(dim=3, use_faiss=False)
    vectors = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype="float32")
    records = [
        ScenarioRecord(
            scenario_id="S1",
            prompt="Price war",
            expected_decision="add premium features",
            category="strategy",
            difficulty="medium",
        ),
        ScenarioRecord(
            scenario_id="S2",
            prompt="Supply chain shock",
            expected_decision="dual source",
            category="risk",
            difficulty="hard",
        ),
    ]
    index.add_many(vectors, records)
    matches = index.search(np.asarray([1.0, 0.0, 0.0], dtype="float32"), k=1)
    assert matches
    assert matches[0].record.scenario_id == "S1"


def test_scenario_retriever_formats_matches():
    index = ScenarioIndex(dim=3, use_faiss=False)
    vectors = np.asarray([[1.0, 0.0, 0.0]], dtype="float32")
    record = ScenarioRecord(
        scenario_id="S3",
        prompt="Compliance gap",
        expected_decision="pause release",
        category="ethics",
        difficulty="hard",
    )
    index.add_many(vectors, [record])
    retriever = ScenarioRetriever(index, embedder=DummyEmbedder([1.0, 0.0, 0.0]))
    matches = retriever.retrieve(prompt="Compliance", context={}, top_k=1)
    formatted = ScenarioRetriever.format_matches(matches)
    assert "Scenario:" in formatted[0]
    assert "Expected:" in formatted[0]
