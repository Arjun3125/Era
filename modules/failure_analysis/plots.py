"""Plotting helpers for failure analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    return plt


def plot_failure_distribution(failure_counts: Dict[str, int], output_dir: Path) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    labels = list(failure_counts.keys())
    values = [failure_counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values)
    ax.set_title("Failure Distribution")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "failure_distribution.png")
    plt.close(fig)


def plot_category_accuracy(category_accuracy: Dict[str, float], output_dir: Path) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    labels = list(category_accuracy.keys())
    values = [category_accuracy[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values)
    ax.set_title("Accuracy by Category")
    ax.set_ylabel("Accuracy")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "failure_category_accuracy.png")
    plt.close(fig)


def plot_calibration_curve(confidences: List[float], accuracies: List[float], output_dir: Path) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(confidences, accuracies, marker="o")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_title("Calibration")
    ax.set_xlabel("Confidence")
    ax.set_ylabel("Accuracy")
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "failure_calibration_curve.png")
    plt.close(fig)
