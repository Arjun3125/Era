from modules import get_module_catalog
from modules.decision_pipeline import DecisionPipelineEngine


def test_module_catalog_contains_core_stages():
    catalog = get_module_catalog()
    for name in (
        "input_normalization",
        "runtime_config",
        "domain_analysis",
        "council_execution",
        "decision_packaging",
        "contract_validation",
    ):
        assert name in catalog


def test_decision_pipeline_core_stage_names():
    stage_names = DecisionPipelineEngine._core_stage_names()
    assert "scenario_memory" in stage_names
    assert "mode_routing" in stage_names
