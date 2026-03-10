"""Plotting utilities for experiment results."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    return plt


def plot_category_scores(scores: Dict[str, float], output_dir: Path) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    categories = list(scores.keys())
    values = [scores[k] for k in categories]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(categories, values)
    ax.set_title("Accuracy by Category")
    ax.set_ylabel("Score")
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "accuracy_by_category.png")
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
    fig.savefig(output_dir / "confidence_calibration.png")
    plt.close(fig)


def plot_score_distribution(scores: List[float], output_dir: Path) -> None:
    plt = _require_matplotlib()
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(scores, bins=20)
    ax.set_title("Score Distribution")
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "score_distribution.png")
    plt.close(fig)
