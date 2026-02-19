"""
Evaluation Framework - Research-grade statistical validation

Components:
- evaluation_runner.py: Main orchestrator with isolation mode & ablations
- stats_engine.py: Statistical validation (t-tests, CI, effect sizes, calibration)
- scoring/outcome_scorer.py: Rubric-based outcome evaluation
- scoring/regret_scorer.py: Regret magnitude quantification
- scoring/rubric_engine.py: Scenario loading & integrity verification
- benchmark_dataset/: Frozen datasets with SHA256 hashes
- MODEL_VERSION.json: Version & configuration tracking
"""

from evaluation.evaluation_runner import EvaluationRunner, EvaluationConfig
from evaluation.stats_engine import StatsEngine, ConfidenceInterval
from evaluation.scoring.outcome_scorer import OutcomeScorer
from evaluation.scoring.regret_scorer import RegretScorer
from evaluation.scoring.rubric_engine import RubricEngine

__all__ = [
    'EvaluationRunner',
    'EvaluationConfig',
    'StatsEngine',
    'ConfidenceInterval',
    'OutcomeScorer',
    'RegretScorer',
    'RubricEngine'
]
