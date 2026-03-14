"""Cluster failure traces by prompt similarity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping

import numpy as np

try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:  # pragma: no cover - optional dependency
    KMeans = None
    TfidfVectorizer = None


@dataclass(frozen=True)
class FailureCluster:
    cluster_id: int
    size: int
    example_ids: List[str]
    top_terms: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "size": self.size,
            "example_ids": list(self.example_ids),
            "top_terms": list(self.top_terms),
        }


def cluster_failures(
    traces: Iterable[Mapping[str, Any]],
    *,
    max_clusters: int = 5,
    min_cluster_size: int = 2,
    top_terms: int = 5,
) -> List[Dict[str, Any]]:
    items = list(traces)
    if not items or KMeans is None or TfidfVectorizer is None:
        return []

    texts = [str(item.get("prompt", "")).strip() for item in items]
    if len(texts) < 2:
        return []

    cluster_count = min(max_clusters, len(texts))
    if cluster_count < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []
    if matrix.shape[0] < 2:
        return []

    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(matrix)
    feature_names = vectorizer.get_feature_names_out()

    clusters: List[FailureCluster] = []
    for cluster_id in range(cluster_count):
        idxs = [idx for idx, label in enumerate(labels) if label == cluster_id]
        if len(idxs) < min_cluster_size:
            continue
        cluster_matrix = matrix[idxs].mean(axis=0)
        scores = np.asarray(cluster_matrix).ravel()
        top_idx = scores.argsort()[::-1][:top_terms]
        terms = [feature_names[i] for i in top_idx if scores[i] > 0]
        example_ids = [
            str(items[idx].get("scenario_id", ""))
            for idx in idxs[: min(len(idxs), 5)]
            if items[idx].get("scenario_id") is not None
        ]
        clusters.append(
            FailureCluster(
                cluster_id=cluster_id,
                size=len(idxs),
                example_ids=example_ids,
                top_terms=terms,
            )
        )

    clusters.sort(key=lambda cluster: cluster.size, reverse=True)
    return [cluster.as_dict() for cluster in clusters]
