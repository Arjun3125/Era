"""
Utilities for Phase2 minister-level logging and gating features.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import requests
import torch

from ml.features.feature_extractor import (
    ConstraintState,
    KISOutput,
    SituationState,
    build_feature_vector,
    feature_vector_to_list,
    get_feature_names,
)

MINISTER_ORDER = ["risk", "optionality", "execution", "adversary"]
MINISTER_KEY_TO_LABEL = {
    "risk": "MINISTER_RISK",
    "optionality": "MINISTER_OPTIONALITY",
    "execution": "MINISTER_EXECUTION",
    "adversary": "MINISTER_ADVERSARY",
}

FEATURE_VERSION = "phase2_gating_v2"
LEGACY_INPUT_DIM = 50
STRUCTURED_INPUT_DIM_EXTENDED = 62  # 41 base + 21 engineered extras
DEFAULT_EMBED_MODEL = os.getenv("GATING_EMBED_MODEL", "nomic-embed-text:latest")

_EMBED_CACHE: Dict[str, List[float]] = {}


@dataclass
class MinisterOutput:
    path: str
    confidence: float
    reason: str


def _normalize_path(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9_ -]", "", value)
    return value.replace("-", "_").replace(" ", "_")


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def _extract_float(value: str, default: float = 0.5) -> float:
    try:
        parsed = float(value.strip())
        if parsed > 1.0:
            parsed = parsed / 100.0
        return _clamp(parsed)
    except Exception:
        return default


def parse_minister_outputs(response: str) -> Dict[str, MinisterOutput]:
    """
    Parse diversity prompt minister lines:
    `MINISTER_X: [path] | [conf] | [reason]`
    """
    text = response or ""
    outputs: Dict[str, MinisterOutput] = {}
    for key in MINISTER_ORDER:
        label = MINISTER_KEY_TO_LABEL[key]
        pattern = rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+)$"
        match = re.search(pattern, text)
        if not match:
            continue
        payload = match.group(1).strip()
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) >= 3:
            path_raw, conf_raw, reason_raw = parts[0], parts[1], "|".join(parts[2:])
        elif len(parts) == 2:
            path_raw, conf_raw, reason_raw = parts[0], parts[1], ""
        else:
            path_raw, conf_raw, reason_raw = payload, "0.5", ""
        outputs[key] = MinisterOutput(
            path=_normalize_path(path_raw),
            confidence=_extract_float(conf_raw, default=0.5),
            reason=reason_raw.strip(),
        )
    return outputs


def disagreement_entropy(minister_outputs: Dict[str, MinisterOutput]) -> float:
    if not minister_outputs:
        return 0.0
    counts: Dict[str, int] = {}
    for item in minister_outputs.values():
        counts[item.path] = counts.get(item.path, 0) + 1
    total = float(sum(counts.values()))
    if total <= 0:
        return 0.0
    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log(p, 2)
    # Normalize by the number of observed decision paths (K), not number of ministers.
    # This yields H_norm in [0, 1] with 1.0 representing maximal vote disagreement.
    k_paths = len(counts)
    max_entropy = math.log(k_paths, 2) if k_paths > 1 else 1.0
    return _clamp(entropy / max_entropy if max_entropy > 0 else 0.0)


def minister_confidence_variance(minister_outputs: Dict[str, MinisterOutput]) -> float:
    if not minister_outputs:
        return 0.0
    values = [o.confidence for o in minister_outputs.values()]
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    # For values in [0,1], variance upper bound is 0.25. Scale to [0,1].
    return _clamp(var / 0.25)


def minister_confidence_vector(minister_outputs: Dict[str, MinisterOutput]) -> List[float]:
    return [float(minister_outputs.get(m, MinisterOutput("", 0.5, "")).confidence) for m in MINISTER_ORDER]


def pairwise_confidence_gaps(minister_outputs: Dict[str, MinisterOutput]) -> List[float]:
    values = minister_confidence_vector(minister_outputs)
    pairs: List[float] = []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            pairs.append(_clamp(abs(values[i] - values[j])))
    while len(pairs) < 6:
        pairs.append(0.0)
    return pairs[:6]


def vote_margin(minister_outputs: Dict[str, MinisterOutput]) -> float:
    if not minister_outputs:
        return 0.0
    counts: Dict[str, int] = {}
    for out in minister_outputs.values():
        counts[out.path] = counts.get(out.path, 0) + 1
    sorted_counts = sorted(counts.values(), reverse=True)
    top = float(sorted_counts[0]) if sorted_counts else 0.0
    second = float(sorted_counts[1]) if len(sorted_counts) > 1 else 0.0
    return _clamp((top - second) / max(len(minister_outputs), 1))


def irreversibility_score(scenario: Dict[str, Any]) -> float:
    category = str(scenario.get("category", "")).strip().lower()
    category_map = {
        "irreversible": 1.0,
        "long_horizon": 0.8,
        "strategic": 0.7,
        "adversarial": 0.75,
        "out_of_distribution": 0.6,
        "emotional": 0.5,
    }
    base = category_map.get(category, 0.5)
    context = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
    if any(token in context for token in ["irreversible", "one-way", "cannot undo", "permanent"]):
        base = max(base, 0.9)
    return _clamp(base)


def escalation_pressure_indicator(scenario: Dict[str, Any]) -> float:
    text = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
    hot_terms = [
        "urgent",
        "deadline",
        "attack",
        "adversary",
        "hostile",
        "threat",
        "crisis",
        "immediate",
    ]
    matches = sum(1 for t in hot_terms if t in text)
    return _clamp(matches / 3.0)


def decision_difficulty_proxy(
    scenario: Dict[str, Any],
    *,
    disagreement: float,
    vote_margin_score: float,
) -> float:
    rubric = scenario.get("ground_truth_rubric", {}) or {}
    n_paths = len(rubric.get("acceptable_paths", []) or [])
    n_failures = len(rubric.get("critical_failure_modes", []) or [])
    text = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
    uncertainty_hits = sum(1 for t in ["uncertain", "unknown", "unclear", "partial", "ambiguous"] if t in text)
    path_complexity = _clamp(n_paths / 5.0)
    failure_severity = _clamp(n_failures / 5.0)
    uncertainty = _clamp(uncertainty_hits / 3.0)
    low_margin = 1.0 - _clamp(vote_margin_score)
    score = (
        0.30 * _clamp(disagreement)
        + 0.25 * low_margin
        + 0.20 * path_complexity
        + 0.15 * failure_severity
        + 0.10 * uncertainty
    )
    return _clamp(score)


def _infer_situation_state(scenario: Dict[str, Any], irr_score: float) -> SituationState:
    category = str(scenario.get("category", "")).strip().lower()
    if category == "irreversible":
        decision_type = "irreversible"
    elif category == "emotional":
        decision_type = "reversible"
    else:
        decision_type = "exploratory"

    if category in {"irreversible", "adversarial"}:
        risk_level = "high"
    elif category in {"strategic", "out_of_distribution"}:
        risk_level = "medium"
    else:
        risk_level = "low"

    if category == "long_horizon":
        horizon = "long"
    elif category in {"adversarial", "emotional"}:
        horizon = "short"
    else:
        horizon = "medium"

    text = f"{scenario.get('input', '')} {scenario.get('context', '')}".lower()
    pressure_hits = sum(1 for t in ["urgent", "deadline", "now", "immediate"] if t in text)
    uncertainty_hits = sum(1 for t in ["uncertain", "unknown", "unclear", "missing"] if t in text)
    time_pressure = _clamp(0.2 + pressure_hits * 0.25)
    information_completeness = _clamp(0.8 - uncertainty_hits * 0.2)

    agency = "org" if any(t in text for t in ["team", "company", "organization", "board"]) else "individual"

    return SituationState(
        decision_type=decision_type,
        risk_level=risk_level,
        time_horizon=horizon,
        time_pressure=time_pressure,
        information_completeness=information_completeness,
        agency=agency,
        user_input=str(scenario.get("input", "")),
    )


def _infer_constraint_state(scenario: Dict[str, Any], irr_score: float) -> ConstraintState:
    rubric = scenario.get("ground_truth_rubric", {}) or {}
    acceptable_paths = rubric.get("acceptable_paths", []) or []
    failure_modes = rubric.get("critical_failure_modes", []) or []
    principles_required = rubric.get("principles_required", []) or []

    optionality_loss = _clamp(1.0 - min(len(acceptable_paths), 5) / 5.0)
    fragility = _clamp(min(len(failure_modes), 5) / 5.0)
    downside = _clamp(min(len(failure_modes), 4) / 4.0)
    upside = _clamp(min(len(principles_required), 4) / 4.0)
    recovery_time_long = bool(irr_score >= 0.75 or str(scenario.get("category", "")).lower() == "long_horizon")

    return ConstraintState(
        irreversibility_score=irr_score,
        fragility_score=fragility,
        optionality_loss_score=optionality_loss,
        downside_asymmetry=downside,
        upside_asymmetry=upside,
        recovery_time_long=recovery_time_long,
    )


def _empty_kis_output() -> KISOutput:
    return KISOutput(
        knowledge_trace=[],
        used_principle=False,
        used_rule=False,
        used_warning=False,
        used_claim=False,
        used_advice=False,
        avg_kis_principle=0.0,
        avg_kis_rule=0.0,
        avg_kis_warning=0.0,
        avg_kis_claim=0.0,
        avg_kis_advice=0.0,
        num_entries_used=0,
        avg_entry_age_days=0.0,
        avg_penalty_count=0.0,
    )


def scenario_text_for_embedding(scenario: Dict[str, Any]) -> str:
    category = str(scenario.get("category", "")).strip()
    prompt = str(scenario.get("input", "")).strip()
    context = str(scenario.get("context", "")).strip()
    return f"Category: {category}\nScenario: {prompt}\nContext: {context}".strip()


def _embed_cache_key(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}\n{text}".encode("utf-8")).hexdigest()


def fetch_ollama_embedding(
    text: str,
    *,
    model: str = DEFAULT_EMBED_MODEL,
    timeout_sec: float = 20.0,
) -> List[float]:
    key = _embed_cache_key(model, text)
    if key in _EMBED_CACHE:
        return list(_EMBED_CACHE[key])
    base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    endpoint = f"{base_url}/api/embeddings"
    response = requests.post(
        endpoint,
        json={"model": model, "prompt": text},
        timeout=timeout_sec,
    )
    response.raise_for_status()
    payload = response.json()
    vec = payload.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise RuntimeError("Embedding response missing vector.")
    parsed = [float(x) for x in vec]
    _EMBED_CACHE[key] = parsed
    return list(parsed)


def fit_pca_reducer(
    vectors: List[List[float]],
    *,
    output_dim: int,
    seed: int = 42,
) -> Dict[str, Any]:
    if not vectors:
        raise ValueError("No vectors provided for PCA fit.")
    x = torch.tensor(vectors, dtype=torch.float32)
    mean = x.mean(dim=0, keepdim=True)
    xc = x - mean
    torch.manual_seed(seed)
    rank = min(output_dim, int(xc.shape[0] - 1), int(xc.shape[1]))
    if rank <= 0:
        raise ValueError("Insufficient vectors for PCA fit.")
    _, s, v = torch.pca_lowrank(xc, q=rank, center=False)
    comp = v[:, :rank].T  # [rank, original_dim]
    if rank < output_dim:
        pad = torch.zeros((output_dim - rank, comp.shape[1]), dtype=comp.dtype)
        comp = torch.cat([comp, pad], dim=0)
    var_ratio = ((s[:rank] ** 2) / (xc.shape[0] - 1 + 1e-9)).tolist()
    return {
        "output_dim": int(output_dim),
        "input_dim": int(x.shape[1]),
        "mean": mean.squeeze(0).tolist(),
        "components": comp.tolist(),
        "explained_variance": var_ratio,
    }


def apply_pca_reducer(vector: List[float], reducer: Dict[str, Any]) -> List[float]:
    if not reducer:
        return []
    mean = reducer.get("mean", [])
    components = reducer.get("components", [])
    if not mean or not components:
        return []
    x = torch.tensor(vector, dtype=torch.float32)
    mu = torch.tensor(mean, dtype=torch.float32)
    c = torch.tensor(components, dtype=torch.float32)
    if x.numel() != mu.numel():
        if x.numel() < mu.numel():
            pad = torch.zeros(mu.numel() - x.numel(), dtype=torch.float32)
            x = torch.cat([x, pad], dim=0)
        else:
            x = x[: mu.numel()]
    reduced = torch.matmul(c, (x - mu))
    return [float(v) for v in reduced.tolist()]


def build_gating_features(
    scenario: Dict[str, Any],
    minister_outputs: Dict[str, MinisterOutput],
    *,
    feature_names_41: List[str] | None = None,
    include_extended_features: bool = False,
    embedding_reduced: List[float] | None = None,
    target_dim: int | None = LEGACY_INPUT_DIM,
) -> Tuple[List[float], List[float], Dict[str, Any]]:
    """
    Return:
    - 41-d base feature list
    - model input list (structured +/- embedding)
    - diagnostics dict
    """
    names_41 = feature_names_41 or get_feature_names()
    irr = irreversibility_score(scenario)
    situation = _infer_situation_state(scenario, irr)
    constraints = _infer_constraint_state(scenario, irr)
    kis = _empty_kis_output()
    base_dict = build_feature_vector(situation, constraints, kis, action=None)
    base_41 = [float(base_dict.get(name, 0.0)) for name in names_41]
    if len(base_41) != 41:
        ordered = feature_vector_to_list(base_dict)
        if len(ordered) >= 41:
            base_41 = ordered[:41]
        else:
            base_41 = ordered + [0.0] * (41 - len(ordered))

    confidences = [o.confidence for o in minister_outputs.values()] or [0.5]
    conf_avg = sum(confidences) / len(confidences)
    conf_max = max(confidences)
    conf_min = min(confidences)
    conf_var = minister_confidence_variance(minister_outputs)
    disagreement = disagreement_entropy(minister_outputs)
    escalation = escalation_pressure_indicator(scenario)

    path_counts: Dict[str, int] = {}
    for out in minister_outputs.values():
        path_counts[out.path] = path_counts.get(out.path, 0) + 1
    agreement_ratio = max(path_counts.values()) / max(len(minister_outputs), 1) if path_counts else 0.0
    acceptable_paths = (scenario.get("ground_truth_rubric", {}) or {}).get("acceptable_paths", []) or []
    path_coverage = _clamp(len(path_counts) / max(len(acceptable_paths), 1))

    legacy_extras = [
        disagreement,
        irr,
        conf_var,
        escalation,
        _clamp(conf_avg),
        _clamp(conf_max),
        _clamp(conf_min),
        _clamp(agreement_ratio),
        _clamp(path_coverage),
    ]

    extras = list(legacy_extras)
    conf_vec = minister_confidence_vector(minister_outputs)
    conf_gap_vec = pairwise_confidence_gaps(minister_outputs)
    vote_margin_score = vote_margin(minister_outputs)
    difficulty = decision_difficulty_proxy(
        scenario,
        disagreement=disagreement,
        vote_margin_score=vote_margin_score,
    )
    if include_extended_features:
        extras.extend(conf_vec)
        extras.extend(conf_gap_vec)
        extras.extend([vote_margin_score, difficulty])

    model_input = base_41 + extras
    if embedding_reduced:
        model_input.extend([float(x) for x in embedding_reduced])

    if target_dim is not None:
        if len(model_input) < target_dim:
            model_input += [0.0] * (target_dim - len(model_input))
        elif len(model_input) > target_dim:
            model_input = model_input[:target_dim]

    diagnostics: Dict[str, Any] = {
        "disagreement_entropy": disagreement,
        "irreversibility_score": irr,
        "minister_confidence_variance": conf_var,
        "escalation_pressure": escalation,
        "minister_confidence_mean": _clamp(conf_avg),
        "minister_confidence_max": _clamp(conf_max),
        "minister_confidence_min": _clamp(conf_min),
        "agreement_ratio": _clamp(agreement_ratio),
        "path_coverage_ratio": _clamp(path_coverage),
        "minister_confidence_vector": conf_vec,
        "pairwise_confidence_gaps": conf_gap_vec,
        "vote_margin": vote_margin_score,
        "decision_difficulty_proxy": difficulty,
        "model_input_length": len(model_input),
        "include_extended_features": bool(include_extended_features),
        "used_embedding": bool(embedding_reduced),
    }
    return base_41, model_input, diagnostics


def build_model_input_from_spec(
    scenario: Dict[str, Any],
    minister_outputs: Dict[str, MinisterOutput],
    feature_spec: Dict[str, Any] | None,
) -> Tuple[List[float], Dict[str, Any]]:
    spec = feature_spec or {}
    use_extended = bool(spec.get("include_extended_features", False))
    use_embeddings = bool(spec.get("use_embeddings", False))
    embedding_model = str(spec.get("embedding_model", DEFAULT_EMBED_MODEL))
    embedding_timeout = float(spec.get("embedding_timeout_sec", 20.0))
    embedding_reduced_dim = int(spec.get("embedding_reduced_dim", 0))
    reducer = spec.get("embedding_pca_reducer") or {}
    input_dim = spec.get("input_dim")
    input_dim = int(input_dim) if input_dim is not None else None

    embedding_reduced: List[float] = []
    if use_embeddings:
        text = scenario_text_for_embedding(scenario)
        raw = fetch_ollama_embedding(text, model=embedding_model, timeout_sec=embedding_timeout)
        if reducer:
            embedding_reduced = apply_pca_reducer(raw, reducer)
        else:
            embedding_reduced = raw
        if embedding_reduced_dim > 0:
            if len(embedding_reduced) < embedding_reduced_dim:
                embedding_reduced += [0.0] * (embedding_reduced_dim - len(embedding_reduced))
            elif len(embedding_reduced) > embedding_reduced_dim:
                embedding_reduced = embedding_reduced[:embedding_reduced_dim]

    _, model_input, diagnostics = build_gating_features(
        scenario,
        minister_outputs,
        include_extended_features=use_extended,
        embedding_reduced=embedding_reduced,
        target_dim=input_dim,
    )
    return model_input, diagnostics


def compute_regret_adjusted_target(
    *,
    final_score: float,
    path_matched: bool,
    failure_modes_matched_count: int,
    scenario: Dict[str, Any],
) -> float:
    """
    Build a bounded target in [0,1] using deterministic rubric score + regret scale.
    """
    scale = scenario.get("regret_scale", {}) or {}
    catastrophic = float(scale.get("catastrophic", 1.0))
    moderate = float(scale.get("moderate", 0.5))
    minimal = float(scale.get("minimal", 0.1))

    if failure_modes_matched_count > 0:
        regret = catastrophic
    elif path_matched:
        regret = minimal
    else:
        regret = moderate

    regret_quality = 1.0 - _clamp(regret)
    blended = 0.5 * _clamp(final_score) + 0.5 * regret_quality
    return _clamp(blended)
