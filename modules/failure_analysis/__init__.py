"""Failure analysis tooling for ERA benchmark runs."""

from .analyzer import analyze_traces
from .clustering import cluster_failures
from .failure_logger import build_trace, write_traces
from .plots import plot_calibration_curve, plot_category_accuracy, plot_failure_distribution
from .report_generator import generate_report

__all__ = (
    "analyze_traces",
    "build_trace",
    "cluster_failures",
    "generate_report",
    "plot_calibration_curve",
    "plot_category_accuracy",
    "plot_failure_distribution",
    "write_traces",
)
