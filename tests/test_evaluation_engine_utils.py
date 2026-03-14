from __future__ import annotations

import pytest

from modules.evaluation_engine.calibration import (
    calibration_bins,
    brier_score,
    expected_calibration_error,
)
from modules.evaluation_engine.metrics import accuracy_score, average, clamp_score, normalize_scores
from modules.evaluation_engine.option_match import match_option, normalize_option
from modules.evaluation_engine.regret import regret_score
from modules.evaluation_engine.rubric_eval import rubric_score


def test_option_normalization_and_match() -> None:
    options = ["Increase marketing", "Lower price", "Ignore competitor"]
    assert normalize_option("Increase   marketing!") == "increase marketing"
    assert match_option("increase marketing", options) == "Increase marketing"
    assert match_option("marketing", options) == "Increase marketing"


def test_rubric_score_and_regret() -> None:
    score = rubric_score("avoid price war and protect margin", ["avoid price war", "protect margin"])
    assert score == pytest.approx(1.0)
    regret = regret_score({"A": 0.8, "B": 0.6}, "B")
    assert regret == pytest.approx(0.2)


def test_metrics_helpers() -> None:
    assert accuracy_score("Accept", "accept") == 1
    assert average([0.2, 0.4]) == pytest.approx(0.3)
    assert clamp_score(1.5) == 1.0
    assert normalize_scores([1.2, -0.2, 0.3]) == [1.0, 0.0, 0.3]


def test_calibration_metrics_helpers() -> None:
    predictions = [{"confidence": 0.9, "correct": True}, {"confidence": 0.2, "correct": False}]
    assert expected_calibration_error(predictions, bins=5) == pytest.approx(0.15)
    assert brier_score(predictions) == pytest.approx(0.025)
    bins = calibration_bins(predictions, bins=5)
    assert len(bins) == 5
