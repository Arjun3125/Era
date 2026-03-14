"""Minister policy predictor + runtime wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import joblib
import numpy as np

from modules.representation import ScenarioEncoder, ScenarioEncoderConfig
from .policy_model import STANCE_LABELS, MinisterPolicyModel


@dataclass
class MinisterPolicyPredictor:
    model_dir: Path
    model_name: str = "all-MiniLM-L6-v2"
    local_files_only: bool = False

    def __post_init__(self) -> None:
        self.model_dir = Path(self.model_dir)
        self._encoder = ScenarioEncoder(
            ScenarioEncoderConfig(
                model_name=self.model_name,
                local_files_only=bool(self.local_files_only),
            )
        )
        self._model = joblib.load(self.model_dir / "policy.pkl")

    def predict_distribution(
        self,
        *,
        prompt: str,
        context: Dict[str, Any] | None = None,
        knowledge: Iterable[Any] | None = None,
    ) -> Dict[str, float]:
        vector = self._encoder.encode_scenario(
            prompt=prompt,
            context=context or {},
            knowledge=knowledge,
        )
        probs = self._model.predict_proba(np.asarray([vector]))
        return MinisterPolicyModel.decode_proba(probs)


class PolicyMinister:
    def __init__(
        self,
        *,
        name: str,
        predictor: MinisterPolicyPredictor,
    ) -> None:
        self.name = name
        self.predictor = predictor

    def analyze(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        distribution = self.predictor.predict_distribution(
            prompt=user_input,
            context=context,
            knowledge=context.get("knowledge_items") or context.get("synthesized_knowledge"),
        )
        stance = max(distribution.items(), key=lambda item: item[1])[0]
        confidence = float(distribution.get(stance, 0.0))
        return {
            "stance": stance,
            "confidence": confidence,
            "reasoning": f"{self.name}: learned policy distribution {distribution}",
            "red_line_triggered": False,
            "stance_distribution": distribution,
        }
