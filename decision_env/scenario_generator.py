"""Scenario generation for the embedded decision environment."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any, Dict, List, Mapping, Optional


SCENARIO_DOMAINS = (
    "startup",
    "military",
    "economic_policy",
    "corporate_strategy",
    "risk_management",
)


@dataclass(frozen=True)
class ScenarioOption:
    """One candidate action inside a generated decision scenario."""

    label: str
    title: str
    description: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "label": self.label,
            "title": self.title,
            "description": self.description,
        }


@dataclass
class DecisionScenario:
    """Structured scenario presented to the ERA policy adapter."""

    scenario_id: str
    domain: str
    title: str
    summary: str
    context: str
    options: List[ScenarioOption]
    simulated_outcomes: Dict[str, Dict[str, float]]
    reward_weights: Dict[str, float]
    requested_mode: str = "meeting"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        option_lines = []
        for option in self.options:
            option_lines.append(
                f"{option.label}: {option.title} - {option.description}"
            )
        constraint_lines = [
            f"- {item}"
            for item in self._normalize_string_list(self.metadata.get("constraints"))
        ]
        lines = [
            f"Scenario ID: {self.scenario_id}",
            f"Domain: {self.domain}",
            f"Title: {self.title}",
            f"Situation: {self.summary}",
            f"Context: {self.context}",
            "Options:",
            *option_lines,
        ]
        if constraint_lines:
            lines.extend(["Constraints:", *constraint_lines])
        return "\n".join(lines)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "title": self.title,
            "summary": self.summary,
            "context": self.context,
            "options": [option.as_dict() for option in self.options],
            "simulated_outcomes": {
                key: dict(value) for key, value in self.simulated_outcomes.items()
            },
            "reward_weights": dict(self.reward_weights),
            "requested_mode": self.requested_mode,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _normalize_string_list(value: Any) -> List[str]:
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if not isinstance(value, list):
            return []
        normalized: List[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized


class ScenarioGenerator:
    """Generates deterministic scenario variations from a curated template bank."""

    def __init__(self, *, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(self, *, domain: Optional[str] = None) -> DecisionScenario:
        selected_domain = self._normalize_domain(domain)
        candidates = [
            template for template in _SCENARIO_TEMPLATES if template["domain"] == selected_domain
        ]
        if not candidates:
            candidates = list(_SCENARIO_TEMPLATES)
        template = self._rng.choice(candidates)
        scenario_index = self._rng.randint(1000, 9999)
        options = [
            ScenarioOption(
                label=str(option["label"]).strip().upper(),
                title=str(option["title"]).strip(),
                description=str(option["description"]).strip(),
            )
            for option in template["options"]
        ]
        simulated_outcomes = {
            label.upper(): self._perturb_outcome_metrics(metrics)
            for label, metrics in template["simulated_outcomes"].items()
        }
        return DecisionScenario(
            scenario_id=f"{template['domain']}-{scenario_index}",
            domain=str(template["domain"]).strip(),
            title=str(template["title"]).strip(),
            summary=str(template["summary"]).strip(),
            context=str(template["context"]).strip(),
            options=options,
            simulated_outcomes=simulated_outcomes,
            reward_weights=dict(template["reward_weights"]),
            requested_mode=str(template.get("requested_mode", "meeting")).strip() or "meeting",
            metadata=dict(template.get("metadata", {})),
        )

    @staticmethod
    def _normalize_domain(domain: Optional[str]) -> str:
        text = str(domain or "").strip().lower()
        return text if text in SCENARIO_DOMAINS else ""

    def _perturb_outcome_metrics(
        self,
        metrics: Mapping[str, float],
    ) -> Dict[str, float]:
        perturbed: Dict[str, float] = {}
        for metric_name, raw_value in metrics.items():
            value = float(raw_value)
            jitter = self._rng.uniform(-2.5, 2.5)
            perturbed[metric_name] = self._clamp_metric(
                metric_name,
                round(value + jitter, 2),
            )
        return perturbed

    @staticmethod
    def _clamp_metric(metric_name: str, value: float) -> float:
        metric = str(metric_name).strip().lower()
        if metric in {
            "risk",
            "regulatory_risk",
            "reputational_risk",
            "casualties",
            "burn",
        }:
            return max(0.0, min(100.0, value))
        return max(-100.0, min(100.0, value))


_SCENARIO_TEMPLATES: List[Dict[str, Any]] = [
    {
        "domain": "startup",
        "title": "Cheaper Competitor Launch",
        "summary": "A well-funded competitor has launched a lower-priced version of your core product.",
        "context": (
            "Revenue growth is slowing, customer churn is rising, and the board wants a response "
            "within two weeks without exhausting runway."
        ),
        "options": [
            {
                "label": "A",
                "title": "Lower price",
                "description": "Cut price aggressively to slow churn and defend market share.",
            },
            {
                "label": "B",
                "title": "Increase marketing",
                "description": "Preserve price and push differentiation through campaigns and sales.",
            },
            {
                "label": "C",
                "title": "Hold position",
                "description": "Avoid reaction and wait for stronger data before responding.",
            },
        ],
        "simulated_outcomes": {
            "A": {"profit": -6.0, "market_share": 12.0, "risk": 19.0, "survival": 5.0, "optionality": -4.0},
            "B": {"profit": -2.0, "brand": 8.0, "market_share": 4.0, "risk": 10.0, "optionality": 3.0},
            "C": {"profit": 1.0, "market_share": -15.0, "risk": 25.0, "survival": -8.0, "optionality": -6.0},
        },
        "reward_weights": {
            "profit": 0.45,
            "market_share": 0.3,
            "brand": 0.15,
            "survival": 0.35,
            "optionality": 0.2,
            "risk": -0.4,
        },
        "requested_mode": "meeting",
        "metadata": {
            "constraints": [
                "Runway cannot absorb a prolonged price war.",
                "Board prefers actions that preserve future financing leverage.",
            ]
        },
    },
    {
        "domain": "military",
        "title": "Border Provocation",
        "summary": "An adversary has advanced into a disputed zone and is testing response thresholds.",
        "context": (
            "Command must balance deterrence, escalation risk, alliance credibility, and troop safety "
            "over the next 72 hours."
        ),
        "options": [
            {
                "label": "A",
                "title": "Rapid reinforcement",
                "description": "Deploy reinforcements and air defense while avoiding direct engagement.",
            },
            {
                "label": "B",
                "title": "Preemptive strike",
                "description": "Attempt to dislodge the incursion immediately with force.",
            },
            {
                "label": "C",
                "title": "Diplomatic delay",
                "description": "Rely on mediation and hold current lines without reinforcement.",
            },
        ],
        "simulated_outcomes": {
            "A": {"readiness": 16.0, "deterrence": 14.0, "risk": 18.0, "casualties": 7.0, "survival": 9.0},
            "B": {"deterrence": 18.0, "readiness": 4.0, "risk": 42.0, "casualties": 31.0, "survival": -6.0},
            "C": {"readiness": -8.0, "deterrence": -12.0, "risk": 26.0, "casualties": 12.0, "survival": -4.0},
        },
        "reward_weights": {
            "readiness": 0.35,
            "deterrence": 0.35,
            "survival": 0.45,
            "risk": -0.35,
            "casualties": -0.5,
        },
        "requested_mode": "war",
        "metadata": {
            "constraints": [
                "Alliance commitments matter.",
                "Large civilian harm would be strategically unacceptable.",
            ]
        },
    },
    {
        "domain": "economic_policy",
        "title": "Inflation Shock Response",
        "summary": "Inflation remains elevated while unemployment is beginning to rise.",
        "context": (
            "Government leadership needs a near-term policy move that balances price stability, "
            "growth, and political legitimacy."
        ),
        "options": [
            {
                "label": "A",
                "title": "Raise rates further",
                "description": "Signal anti-inflation credibility through another rate hike.",
            },
            {
                "label": "B",
                "title": "Targeted fiscal support",
                "description": "Stabilize vulnerable sectors while maintaining current rates.",
            },
            {
                "label": "C",
                "title": "Pause action",
                "description": "Wait for new data and avoid immediate policy changes.",
            },
        ],
        "simulated_outcomes": {
            "A": {"inflation_control": 15.0, "growth": -8.0, "stability": 4.0, "risk": 18.0, "trust": 6.0},
            "B": {"inflation_control": 7.0, "growth": 6.0, "stability": 9.0, "risk": 11.0, "trust": 8.0},
            "C": {"inflation_control": -6.0, "growth": 1.0, "stability": -5.0, "risk": 24.0, "trust": -7.0},
        },
        "reward_weights": {
            "inflation_control": 0.35,
            "growth": 0.25,
            "stability": 0.3,
            "trust": 0.25,
            "risk": -0.35,
        },
        "requested_mode": "meeting",
        "metadata": {
            "constraints": [
                "Policy credibility must be preserved.",
                "A recession before elections would create political strain.",
            ]
        },
    },
    {
        "domain": "corporate_strategy",
        "title": "Platform Expansion Choice",
        "summary": "The company can either acquire a niche player, build internally, or defer expansion.",
        "context": (
            "Leadership wants a move that improves strategic position without blowing up integration risk "
            "or capital allocation discipline."
        ),
        "options": [
            {
                "label": "A",
                "title": "Acquire niche player",
                "description": "Buy a smaller competitor to accelerate market entry.",
            },
            {
                "label": "B",
                "title": "Build internally",
                "description": "Invest in internal platform development over the next three quarters.",
            },
            {
                "label": "C",
                "title": "Defer expansion",
                "description": "Preserve cash and revisit the opportunity later.",
            },
        ],
        "simulated_outcomes": {
            "A": {"strategic_position": 14.0, "growth": 11.0, "risk": 23.0, "burn": 18.0, "optionality": -4.0},
            "B": {"strategic_position": 10.0, "growth": 7.0, "risk": 11.0, "burn": 8.0, "optionality": 7.0},
            "C": {"strategic_position": -5.0, "growth": -3.0, "risk": 8.0, "burn": 0.0, "optionality": 4.0},
        },
        "reward_weights": {
            "strategic_position": 0.4,
            "growth": 0.25,
            "optionality": 0.25,
            "risk": -0.3,
            "burn": -0.25,
        },
        "requested_mode": "darbar",
        "metadata": {
            "constraints": [
                "Integration failures would damage management credibility.",
                "Capital discipline is under external scrutiny.",
            ]
        },
    },
    {
        "domain": "risk_management",
        "title": "Critical Vendor Exposure",
        "summary": "A critical third-party vendor shows signs of compliance weakness and delivery slippage.",
        "context": (
            "Operations rely on the vendor for continuity, but remaining exposed could create legal, "
            "reputational, and availability risk."
        ),
        "options": [
            {
                "label": "A",
                "title": "Dual-source immediately",
                "description": "Stand up a backup vendor and reduce concentration risk.",
            },
            {
                "label": "B",
                "title": "Enforce remediation",
                "description": "Keep the vendor but impose controls, audits, and recovery checkpoints.",
            },
            {
                "label": "C",
                "title": "Accept current risk",
                "description": "Avoid disruption and revisit after the next contract review.",
            },
        ],
        "simulated_outcomes": {
            "A": {"resilience": 16.0, "compliance": 13.0, "risk": 9.0, "burn": 10.0, "trust": 8.0},
            "B": {"resilience": 9.0, "compliance": 10.0, "risk": 14.0, "burn": 4.0, "trust": 6.0},
            "C": {"resilience": -8.0, "compliance": -12.0, "risk": 29.0, "burn": 0.0, "trust": -10.0},
        },
        "reward_weights": {
            "resilience": 0.4,
            "compliance": 0.35,
            "trust": 0.25,
            "risk": -0.45,
            "burn": -0.1,
        },
        "requested_mode": "meeting",
        "metadata": {
            "constraints": [
                "Any outage would be externally visible.",
                "Compliance failures could trigger contractual penalties.",
            ]
        },
    },
]
