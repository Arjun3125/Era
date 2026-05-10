"""Central council execution engine for mode-aware minister deliberation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from modules.council_router.mode_orchestrator import ExecutionConfig, ModeOrchestrator
from modules.expert_router.aggregator import aggregate_weighted_positions
from modules.expert_router.aggregator import aggregate_weighted_positions


_MEETING_MINISTERS = ["risk", "grand_strategist", "optionality", "psychology", "timing"]
_DARBAR_MINISTERS = [
    "risk", "grand_strategist", "power", "optionality", "psychology",
    "timing", "legitimacy", "truth", "data", "conflict",
    "diplomacy", "technology", "intelligence", "narrative",
    "discipline", "adaptation", "sovereign", "war_mode",
]

CouncilFactory = Callable[[Any], Any]
_SUPPORTED_STANCES = {"support", "oppose", "neutral"}
_MODE_ALIASES = {
    "quick_mode": "quick",
    "fast": "quick",
    "normal": "meeting",
    "standard": "meeting",
    "default": "meeting",
    "war_mode": "war",
    "full_council": "darbar",
    "board": "darbar",
}
_MINISTER_ALIASES = {
    "resource": "risk_resources",
    "resources": "risk_resources",
    "risk_resource": "risk_resources",
    "grand_strategy": "grand_strategist",
    "grandstrategy": "grand_strategist",
    "optional": "optionality",
    "sovereignty": "sovereign",
}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_NATIVE_RISK_KEYWORDS = (
    "risk",
    "loss",
    "bankrupt",
    "legal",
    "irreversible",
    "debt",
    "downside",
)
_NATIVE_SPEED_KEYWORDS = ("urgent", "deadline", "immediately", "now", "fast")
_NATIVE_UNCERTAINTY_KEYWORDS = ("uncertain", "unknown", "ambiguous", "guess")

import os as _os
import re as _re
try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

_DOCTRINE_ROOT = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
    "data", "doctrine", "locked"
)

_MINISTER_YAML_NAMES = {
    "risk": "risk_resources",
    "risk_resources": "risk_resources",
    "power": "power",
    "grand_strategist": "grand_strategist",
    "technology": "technology",
    "timing": "timing",
    "optionality": "optionality",
    "data": "data",
    "diplomacy": "diplomacy",
    "psychology": "psychology",
    "legitimacy": "legitimacy",
    "conflict": "conflict",
    "truth": "truth",
    "discipline": "discipline",
    "intelligence": "intelligence",
    "narrative": "narrative",
    "sovereign": "n",
    "adaptation": "adaptation",
    "war_mode": "war_mode",
}


def _load_doctrine_keywords(minister_name: str):
    """Return (speak_keywords, silent_keywords) extracted from the minister's doctrine YAML."""
    if not _YAML_AVAILABLE:
        return [], []
    yaml_name = _MINISTER_YAML_NAMES.get(minister_name)
    if not yaml_name:
        return [], []
    yaml_path = _os.path.join(_DOCTRINE_ROOT, f"{yaml_name}.yaml")
    if not _os.path.isfile(yaml_path):
        return [], []
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            doc = _yaml.safe_load(f)
        triggers = (doc.get("doctrine") or {}).get("triggers") or {}
        speak_raw = triggers.get("speak") or []
        silent_raw = triggers.get("silent") or []

        def _extract(items):
            keywords = []
            for item in (items if isinstance(items, list) else [str(items)]):
                # Extract 4+-char words from each trigger phrase
                words = _re.findall(r"\b[a-z]{4,}\b", str(item).lower())
                keywords.extend(words)
            return list(set(keywords))

        return _extract(speak_raw), _extract(silent_raw)
    except Exception:
        return [], []


@dataclass
class _NativeMinister:
    name: str
    bias: str = "neutral"
    strict_on_risk: bool = False
    doctrine_speak_keywords: list = field(default_factory=list)
    doctrine_silent_keywords: list = field(default_factory=list)

    @property
    def doctrine_keywords(self):
        """Combined view for backward compat."""
        return set(self.doctrine_speak_keywords) | set(self.doctrine_silent_keywords)

    def analyze(self, user_input: str, context: Mapping[str, Any]) -> Dict[str, Any]:
        text = str(user_input or "").lower()
        option_text = ""
        if "option:" in text:
            option_text = text.split("option:", 1)[-1].strip()
            option_text = option_text.splitlines()[0].strip()
        domains = {str(item).strip().lower() for item in (context.get("domains") or [])}
        urgency = _native_keyword_score(text, _NATIVE_SPEED_KEYWORDS)
        risk_score = _native_keyword_score(text, _NATIVE_RISK_KEYWORDS)
        uncertainty = _native_keyword_score(text, _NATIVE_UNCERTAINTY_KEYWORDS)

        stance = self.bias
        if self.strict_on_risk and risk_score >= 0.25:
            stance = "oppose"
        elif "risk" in domains and self.name in {"risk", "risk_resources"} and risk_score >= 0.15:
            stance = "oppose"
        elif urgency >= 0.25 and self.name in {"timing", "technology", "grand_strategist"}:
            stance = "support"
        elif uncertainty >= 0.35:
            stance = "neutral"

        # Doctrine-keyword override: if doctrine says speak and text matches, push toward bias
        if self.doctrine_speak_keywords:
            if any(kw in text for kw in self.doctrine_speak_keywords):
                if stance == "neutral":
                    stance = self.bias if self.bias != "neutral" else "support"

        if option_text:
            support_terms = {
                "risk": ["contain", "patch", "audit", "shut", "mitigate", "harden", "pause", "halt", "stop"],
                "risk_resources": ["diversify", "backup", "buffer", "stockpile", "dual-source"],
                "grand_strategist": ["expand", "acquire", "partner", "launch", "enter", "differentiate", "growth"],
                "timing": ["launch now", "immediately", "move fast", "now"],
                "technology": ["reliability", "infrastructure", "stability", "platform"],
                "legitimacy": ["disclose", "transparent", "audit", "compliance", "communicate", "open"],
                "truth": ["disclose", "transparent", "communicate", "open"],
                "optionality": ["pilot", "beta", "limited", "experiment", "pause", "delay"],
                "data": ["monitor", "measure", "analyze", "report", "review"],
                "power": ["aggressive", "attack", "price cut", "dominate"],
            }
            oppose_terms = {
                "risk": ["ignore", "deny", "do nothing", "monitor only", "release", "ship", "launch"],
                "legitimacy": ["deny", "quiet", "cover", "ignore", "dismiss"],
                "truth": ["deny", "quiet", "cover", "dismiss"],
                "timing": ["delay", "pause", "wait"],
                "power": ["retreat", "exit", "abandon", "withdraw"],
            }
            for term in support_terms.get(self.name, []):
                if term in option_text:
                    stance = "support"
                    break
            for term in oppose_terms.get(self.name, []):
                if term in option_text:
                    stance = "oppose"
                    break

        confidence = 0.55
        if stance == "support":
            confidence = 0.65 + urgency * 0.2
        elif stance == "oppose":
            confidence = 0.65 + risk_score * 0.25
        confidence = max(0.0, min(1.0, confidence))

        return {
            "stance": stance,
            "confidence": round(confidence, 4),
            "reasoning": _native_reasoning_for(self.name, stance, urgency, risk_score, uncertainty),
            "red_line_triggered": bool(self.strict_on_risk and risk_score >= 0.35),
        }


import sqlite3
import threading

class NativeCouncil:
    """Simple in-process council compatible with CouncilExecutionEngine expectations."""

    def __init__(self, llm: Any = None):
        self.llm = llm
        self.ministers = self._build_ministers()
        self._local = threading.local()

    @property
    def db(self):
        if not hasattr(self._local, "db"):
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.db = conn
            self._initialize_schema(conn)
        return self._local.db

    def _initialize_schema(self, conn):
        conn.execute('''
            CREATE TABLE IF NOT EXISTS council_decisions (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                decision_type TEXT,
                rationale TEXT
            )
        ''')

    def deliberate(self, user_input: str, context: dict) -> dict:
        """Run council deliberation. Uses LLM voice for meeting/darbar if LLM available.

        Falls back to keyword scoring for quick/war modes or when no LLM present.
        """
        mode = str(context.get("mode", "meeting")).lower()

        if self.llm is not None and mode in {"meeting", "darbar"}:
            minister_names = _DARBAR_MINISTERS if mode == "darbar" else _MEETING_MINISTERS
            return self._llm_deliberate(user_input, context, minister_names)
        else:
            return self._keyword_deliberate(user_input, context)

    def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
        """Call each minister via MinisterVoice, aggregate stances."""
        try:
            _mv_mod = __import__("persona.council.minister_voice", fromlist=["MinisterVoice"])
            MinisterVoice = _mv_mod.MinisterVoice
        except ImportError:
            return self._keyword_deliberate(user_input, context)

        mode = str(context.get("mode", "meeting")).lower()
        active_domains = context.get("domains", [])
        knowledge_entries: list = []
        try:
            _ke_mod = __import__("persona.knowledge_engine", fromlist=["synthesize_knowledge"])
            synthesize_knowledge = _ke_mod.synthesize_knowledge
            if active_domains:
                kis = synthesize_knowledge(
                    user_input=user_input,
                    active_domains=active_domains,
                    domain_confidence=0.7,
                )
                knowledge_entries = kis.get("synthesized_knowledge", [])[:6]
        except Exception:
            pass

        # Round 1: all ministers deliberate
        stances = {}
        for name in minister_names:
            voice = MinisterVoice(minister_name=name, llm=self.llm)
            result = voice.deliberate(user_input, context, knowledge_entries=knowledge_entries)
            stances[name] = result

        rounds = [{"round": 1, "stances": {n: r["stance"] for n, r in stances.items()}}]
        peer_challenges: Dict[str, str] = {}

        # Round 2 (darbar only): ministers see peer summary and can revise
        if mode == "darbar":
            peer_summary = "Peer stances from Round 1: " + ", ".join(
                f"{n}={r['stance']}({r['confidence']:.0%})"
                for n, r in stances.items()
            )
            r2_context = dict(context)
            r2_context["peer_summary"] = peer_summary

            stances_r2 = {}
            for name in minister_names:
                voice = MinisterVoice(minister_name=name, llm=self.llm)
                r1_stance = stances[name]["stance"]
                result = voice.deliberate(user_input, r2_context, knowledge_entries=knowledge_entries)
                stances_r2[name] = result
                # Track if minister changed position
                if result["stance"] != r1_stance:
                    peer_challenges[name] = (
                        f"Changed from {r1_stance} to {result['stance']}: {result['reasoning'][:120]}"
                    )

            rounds.append({"round": 2, "stances": {n: r["stance"] for n, r in stances_r2.items()}})
            stances = stances_r2  # final stances from round 2

        support = sum(1 for r in stances.values() if r["stance"] == "support")
        oppose = sum(1 for r in stances.values() if r["stance"] == "oppose")
        neutral = sum(1 for r in stances.values() if r["stance"] == "neutral")
        warnings = [f"{n}: {r['warning']}" for n, r in stances.items() if r.get("warning")]

        total = max(1, support + oppose + neutral)
        if support > oppose:
            outcome = "proceed"
        elif oppose > support:
            outcome = "reconsider"
        else:
            outcome = "defer"

        consensus_strength = max(support, oppose) / total

        # Dissent summary when meaningful disagreement exists
        dissent_summary = ""
        if support > 0 and oppose > 0:
            supporters = [n for n, r in stances.items() if r["stance"] == "support"]
            opposers = [n for n, r in stances.items() if r["stance"] == "oppose"]
            top_support_reason = stances[supporters[0]]["reasoning"] if supporters else ""
            top_oppose_reason = stances[opposers[0]]["reasoning"] if opposers else ""
            dissent_summary = (
                f"{', '.join(supporters[:2])} advocate proceeding: {top_support_reason[:120]} | "
                f"{', '.join(opposers[:2])} urge caution: {top_oppose_reason[:120]}"
            )

        MINORITY_CONFIDENCE_THRESHOLD = 0.85
        minority_alert = ""
        for name, result in stances.items():
            majority_stance = "support" if outcome == "proceed" else ("oppose" if outcome == "reconsider" else "neutral")
            if result["confidence"] >= MINORITY_CONFIDENCE_THRESHOLD and result["stance"] != majority_stance:
                minority_alert = (
                    f"MINORITY ALERT — {name} ({result['confidence']:.0%} confident): "
                    f"{result['reasoning'][:200]}"
                )
                if result.get("warning"):
                    minority_alert += f" | Warning: {result['warning']}"
                break

        return {
            "outcome": outcome,
            "recommendation": outcome,
            "stances": stances,
            "consensus_strength": round(consensus_strength, 3),
            "red_line_concerns": warnings,
            "ministers_involved": minister_names,
            "dissent_summary": dissent_summary,
            "minority_alert": minority_alert,
            "rounds": rounds,
            "peer_challenges": peer_challenges,
        }

    def _keyword_deliberate(self, user_input: str, context: dict) -> dict:
        """Keyword-based fallback when no LLM or in quick/war mode."""
        stances = {}
        support, oppose, neutral = 0, 0, 0
        for name, minister in self.ministers.items():
            result = minister.analyze(user_input, context)
            stances[name] = result
            s = result["stance"]
            if s == "support": support += 1
            elif s == "oppose": oppose += 1
            else: neutral += 1

        total = max(1, support + oppose + neutral)
        outcome = "proceed" if support > oppose else ("reconsider" if oppose > support else "defer")
        return {
            "outcome": outcome,
            "recommendation": outcome,
            "stances": stances,
            "consensus_strength": round(max(support, oppose) / total, 3),
            "red_line_concerns": [],
            "ministers_involved": list(self.ministers.keys()),
        }

    @staticmethod
    def _build_ministers() -> Dict[str, _NativeMinister]:
        specs_raw = {
            "risk": dict(bias="oppose", strict_on_risk=True),
            "risk_resources": dict(bias="neutral", strict_on_risk=True),
            "power": dict(bias="support"),
            "grand_strategist": dict(bias="support"),
            "technology": dict(bias="support"),
            "timing": dict(bias="support"),
            "optionality": dict(bias="support"),
            "data": dict(bias="neutral"),
            "diplomacy": dict(bias="neutral"),
            "psychology": dict(bias="neutral"),
            "legitimacy": dict(bias="neutral", strict_on_risk=True),
            "conflict": dict(bias="oppose"),
            "truth": dict(bias="neutral"),
            "discipline": dict(bias="support"),
            "intelligence": dict(bias="neutral"),
            "narrative": dict(bias="neutral"),
            "sovereign": dict(bias="support"),
            "adaptation": dict(bias="support"),
            "war_mode": dict(bias="support"),
        }
        ministers = {}
        for name, kwargs in specs_raw.items():
            speak_kw, silent_kw = _load_doctrine_keywords(name)
            ministers[name] = _NativeMinister(
                name=name,
                doctrine_speak_keywords=speak_kw,
                doctrine_silent_keywords=silent_kw,
                **kwargs,
            )
        return ministers


def _default_council_factory(llm: Any) -> Any:
    """Resolve native council implementation lazily to avoid import-time coupling."""
    return NativeCouncil(llm=llm)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _coerce_iterable_items(
    value: Iterable[Any],
    *,
    preserve_partial: bool,
) -> tuple[List[Any], bool]:
    collected: List[Any] = []
    iterator = iter(value)
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            return collected, False
        except Exception:
            if preserve_partial:
                return collected, True
            return [], True
        collected.append(item)


def _coerce_mapping_like(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, Mapping):
        try:
            source_items = value.items()
        except Exception:
            return {}
        items, _ = _coerce_iterable_items(source_items, preserve_partial=True)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        raw_items, failed = _coerce_iterable_items(value, preserve_partial=False)
        if failed:
            return None
        items = []
        for raw_item in raw_items:
            if isinstance(raw_item, Mapping):
                return None
            try:
                key, item_value = raw_item
            except Exception:
                return None
            items.append((key, item_value))
    else:
        return None

    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in items:
        key = _normalize_text(raw_key)
        if not key or key in normalized:
            continue
        normalized[key] = raw_value
    return normalized


@dataclass
class CouncilExecutionEngine:
    """Single execution API for council invocation across decision modes."""

    orchestrator: ModeOrchestrator
    llm: Any = None
    council_factory: CouncilFactory = _default_council_factory
    disabled: bool = False
    _base_council: Any = field(default=None, init=False, repr=False)

    @classmethod
    def create(
        cls,
        *,
        llm: Any = None,
        config: ExecutionConfig | None = None,
        council_factory: CouncilFactory = _default_council_factory,
    ) -> "CouncilExecutionEngine":
        return cls(
            orchestrator=ModeOrchestrator(config=config),
            llm=llm,
            council_factory=council_factory,
        )

    @property
    def base_council(self) -> Any:
        if self._base_council is None:
            self._base_council = self.council_factory(self.llm)
        return self._base_council

    def set_mode(self, mode: str) -> bool:
        normalized = self._normalize_mode(mode)
        if not normalized:
            return False
        return self.orchestrator.set_mode(normalized)

    def get_current_mode(self) -> str:
        return self.orchestrator.get_current_mode()

    def list_modes(self) -> List[str]:
        return self.orchestrator.list_modes()

    def get_mode_description(self, mode: str) -> str:
        return self.orchestrator.get_mode_description(mode)

    def convene(
        self,
        mode: str,
        user_input: str,
        context: Dict[str, Any],
        *,
        selected_ministers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run council execution for a mode and return a stable result envelope."""
        warnings: List[str] = []
        context_map = self._normalize_context(context, warnings)

        requested_mode, mode_reason, raw_mode = self._normalize_requested_mode(mode)
        if mode_reason == "missing":
            warnings.append("Missing mode normalized to 'meeting'.")
        elif mode_reason == "unsupported":
            warnings.append(f"Unsupported mode '{raw_mode}' normalized to 'meeting'.")
        elif mode_reason == "alias":
            warnings.append(f"Mode alias '{raw_mode}' normalized to '{requested_mode}'.")

        if not self.orchestrator.set_mode(requested_mode):
            warnings.append(
                f"Resolved mode '{requested_mode}' unsupported by orchestrator; fallback to 'meeting'."
            )
            self.orchestrator.set_mode("meeting")
        resolved_mode = self.orchestrator.get_current_mode()

        if self.disabled:
            return self._empty_council_result(
                outcome="council_disabled_ablation",
                recommendation="no_council_response",
                mode=resolved_mode,
                reasoning="Council disabled for ablation study",
                warnings=warnings,
            )

        if not self.orchestrator.should_invoke_council(resolved_mode):
            return self._empty_council_result(
                outcome="quick_mode_direct_response",
                recommendation="use_direct_llm_response",
                mode=resolved_mode,
                reasoning="Mode does not invoke ministerial council",
                warnings=warnings,
            )

        council = self.base_council
        ministers_raw = getattr(council, "ministers", {})
        if not isinstance(ministers_raw, Mapping):
            warnings.append("Council ministers registry was invalid; normalized to empty mapping.")
            ministers_map: Dict[Any, Any] = {}
        else:
            minister_items, failed = _coerce_iterable_items(
                ministers_raw.items(),
                preserve_partial=True,
            )
            ministers_map = {}
            for raw_key, raw_minister in minister_items:
                if raw_key in ministers_map:
                    continue
                ministers_map[raw_key] = raw_minister
            if failed:
                warnings.append(
                    "Council ministers registry iteration failed; partial registry preserved."
                )
        minister_key_map = {
            str(name).strip().lower(): name
            for name in ministers_map.keys()
            if str(name).strip()
        }
        available_ministers = set(minister_key_map.keys())
        if not available_ministers:
            warnings.append("No ministers are registered in council; execution will return empty positions.")

        minister_names = self._resolve_minister_names(
            selected_ministers=selected_ministers,
            resolved_mode=resolved_mode,
            context=context_map,
            available_ministers=available_ministers,
            warnings=warnings,
        )

        learned_ministers = self._load_learned_ministers(
            minister_names,
            context_map,
            warnings,
        )
        if learned_ministers is not None:
            ministers_map = learned_ministers
            minister_key_map = {
                str(name).strip().lower(): name
                for name in ministers_map.keys()
                if str(name).strip()
            }
            available_ministers = set(minister_key_map.keys())
            minister_names = self._resolve_minister_names(
                selected_ministers=selected_ministers,
                resolved_mode=resolved_mode,
                context=context_map,
                available_ministers=available_ministers,
                warnings=warnings,
            )
        minister_positions, failed_ministers, execution_warnings = self._collect_minister_positions(
            ministers=ministers_map,
            minister_key_map=minister_key_map,
            minister_names=minister_names,
            user_input=user_input,
            context=context_map,
        )
        warnings.extend(execution_warnings)

        mode_aggregation_raw = self.orchestrator.aggregate_for_mode(minister_positions, resolved_mode)
        mode_aggregation = self._normalize_context(mode_aggregation_raw, warnings=[])

        support_count, oppose_count, neutral_count = self._count_stances(minister_positions)
        recommendation = self._determine_recommendation(
            resolved_mode,
            support_count,
            oppose_count,
            neutral_count,
            minister_positions,
        )
        weighted_aggregation = None
        expert_weights = context_map.get("expert_weights") if isinstance(context_map, Mapping) else None
        if isinstance(expert_weights, Mapping):
            weighted_aggregation = aggregate_weighted_positions(
                minister_positions=minister_positions,
                expert_weights={str(k).lower(): float(v) for k, v in expert_weights.items()},
            )
            recommendation = weighted_aggregation.get("recommendation", recommendation)

        red_lines = [
            name
            for name, position in minister_positions.items()
            if bool(position.get("red_line_triggered", False))
        ]
        total_consulted = len(minister_positions)
        consensus_strength = (
            max(support_count, oppose_count) / total_consulted if total_consulted else 0.0
        )
        if weighted_aggregation and weighted_aggregation.get("consensus_strength") is not None:
            consensus_strength = float(weighted_aggregation["consensus_strength"])
        if total_consulted == 0:
            warnings.append("No ministers produced positions; consensus defaults to 0.0.")
        council_positions = self._build_council_positions(minister_positions)
        reasoning = (
            f"{support_count} support, {oppose_count} oppose, {neutral_count} neutral"
            f" across {total_consulted} consulted ministers."
        )

        deduped_warnings = self._dedupe_warnings(warnings)
        return {
            "outcome": str(mode_aggregation.get("recommendation_type", "standard_consensus")),
            "recommendation": recommendation,
            "mode": resolved_mode,
            "ministers_involved": list(minister_positions.keys()),
            "ministers_failed": failed_ministers,
            "minister_positions": minister_positions,
            "minister_outputs": minister_positions,
            "council_positions": council_positions,
            "mode_metadata": mode_aggregation,
            "weighted_aggregation": weighted_aggregation or {},
            "support_count": support_count,
            "oppose_count": oppose_count,
            "neutral_count": neutral_count,
            "red_line_concerns": red_lines,
            "consensus_strength": consensus_strength,
            "total_ministers_consulted": total_consulted,
            "reasoning": reasoning,
            "requested_ministers": list(minister_names),
            "warnings": deduped_warnings,
            "warning_count": len(deduped_warnings),
        }

    def _collect_minister_positions(
        self,
        *,
        ministers: Mapping[str, Any],
        minister_key_map: Mapping[str, str],
        minister_names: List[str],
        user_input: str,
        context: Dict[str, Any],
    ) -> tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
        context_payload = dict(context)
        context_payload["user_input"] = _normalize_text(user_input)

        positions: Dict[str, Dict[str, Any]] = {}
        failed: List[str] = []
        warnings: List[str] = []

        for minister_name in minister_names:
            key = minister_key_map.get(minister_name, minister_name)
            minister = ministers.get(key)
            if minister is None:
                failed.append(f"{minister_name}:not_registered")
                continue

            analyze = getattr(minister, "analyze", None)
            if not callable(analyze):
                failed.append(f"{minister_name}:analyze_unavailable")
                continue

            try:
                raw_position = analyze(user_input, context_payload)
                normalized_position, position_warnings = self._normalize_position(
                    raw_position,
                    minister_name=minister_name,
                )
                positions[minister_name] = normalized_position
                warnings.extend(position_warnings)
            except Exception as exc:  # pragma: no cover - defensive guard
                failed.append(f"{minister_name}:{type(exc).__name__}")
                warnings.append(
                    f"{minister_name}:execution failed with {type(exc).__name__}."
                )

        return positions, failed, warnings

    @staticmethod
    def _load_learned_ministers(
        minister_names: List[str],
        context: Dict[str, Any],
        warnings: List[str],
    ) -> Dict[str, Any] | None:
        enable = context.get("use_learned_ministers") or context.get("minister_policy_path")
        if not enable:
            return None
        policy_root = context.get("minister_policy_path") or "data/minister_policies"
        try:
            from pathlib import Path

            from modules.minister_policies import MinisterPolicyPredictor, PolicyMinister
        except Exception as exc:
            warnings.append(f"Failed to load minister policies: {exc}")
            return None

        root = Path(str(policy_root))
        if not root.exists():
            warnings.append(f"Minister policy path not found: {root}")
            return None

        learned: Dict[str, Any] = {}
        for name in minister_names:
            model_dir = root / name
            if not model_dir.exists():
                warnings.append(f"Minister policy missing for '{name}', fallback to native.")
                return None
            try:
                predictor = MinisterPolicyPredictor(model_dir=model_dir)
                learned[name] = PolicyMinister(name=name, predictor=predictor)
            except Exception as exc:
                warnings.append(f"Failed to load policy for {name}: {exc}")
                return None
        return learned

    @staticmethod
    def _normalize_position(
        position: Any,
        *,
        minister_name: str,
    ) -> tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        if isinstance(position, dict):
            stance_raw = _normalize_text(position.get("stance", "neutral")).lower()
            stance = stance_raw if stance_raw in _SUPPORTED_STANCES else "neutral"
            if stance != stance_raw:
                warnings.append(
                    f"{minister_name}:unsupported stance '{stance_raw}' normalized to 'neutral'."
                )
            confidence_raw = position.get("confidence", 0.0)
            reasoning = _normalize_text(position.get("reasoning", ""))
            red_line = CouncilExecutionEngine._to_bool(
                position.get(
                    "red_line_triggered",
                    position.get("red_line", False),
                )
            )
            confidence = CouncilExecutionEngine._normalize_confidence(
                confidence_raw,
                warnings=warnings,
                minister_name=minister_name,
            )
            return {
                "stance": stance,
                "confidence": confidence,
                "reasoning": reasoning,
                "red_line_triggered": bool(red_line),
            }, warnings

        stance_raw = _normalize_text(getattr(position, "stance", "neutral")).lower()
        stance = stance_raw if stance_raw in _SUPPORTED_STANCES else "neutral"
        if stance != stance_raw:
            warnings.append(
                f"{minister_name}:unsupported stance '{stance_raw}' normalized to 'neutral'."
            )
        confidence_raw = getattr(position, "confidence", 0.0)
        confidence = CouncilExecutionEngine._normalize_confidence(
            confidence_raw,
            warnings=warnings,
            minister_name=minister_name,
        )
        red_line_raw = getattr(position, "red_line_triggered", getattr(position, "red_line", False))
        return {
            "stance": stance,
            "confidence": confidence,
            "reasoning": _normalize_text(getattr(position, "reasoning", "")),
            "red_line_triggered": bool(CouncilExecutionEngine._to_bool(red_line_raw)),
        }, warnings

    @staticmethod
    def _normalize_confidence(
        value: Any,
        *,
        warnings: List[str],
        minister_name: str,
    ) -> float:
        try:
            numeric = float(value if value is not None else 0.0)
        except Exception:
            warnings.append(f"{minister_name}:invalid confidence normalized to 0.0.")
            return 0.0
        if not math.isfinite(numeric):
            warnings.append(f"{minister_name}:non-finite confidence normalized to 0.0.")
            return 0.0
        if numeric < 0.0:
            warnings.append(f"{minister_name}:confidence below 0.0 clamped to 0.0.")
            return 0.0
        if numeric > 1.0:
            warnings.append(f"{minister_name}:confidence above 1.0 clamped to 1.0.")
            return 1.0
        return numeric

    def _resolve_minister_names(
        self,
        *,
        selected_ministers: Optional[List[str]],
        resolved_mode: str,
        context: Dict[str, Any],
        available_ministers: set[str],
        warnings: List[str],
    ) -> List[str]:
        default_candidates = self.orchestrator.get_ministers_for_mode(resolved_mode, context)
        preferred = selected_ministers if selected_ministers is not None else default_candidates
        normalized = self._normalize_minister_candidates(
            preferred,
            available_ministers=available_ministers,
            warnings=warnings,
            emit_alias_warnings=(selected_ministers is not None),
            emit_unknown_warnings=True,
        )
        if normalized:
            return normalized

        if selected_ministers is not None:
            warnings.append("selected_ministers produced no valid names; fallback to mode defaults.")
            fallback = self._normalize_minister_candidates(
                default_candidates,
                available_ministers=available_ministers,
                warnings=warnings,
                emit_alias_warnings=False,
                emit_unknown_warnings=True,
            )
            if fallback:
                return fallback

        warnings.append("No valid ministers resolved; council execution may degrade.")
        return []

    @staticmethod
    def _normalize_minister_candidates(
        candidates: Any,
        *,
        available_ministers: set[str],
        warnings: List[str],
        emit_alias_warnings: bool,
        emit_unknown_warnings: bool,
    ) -> List[str]:
        if isinstance(candidates, str):
            raw = [part.strip() for part in candidates.split(",")]
        elif isinstance(candidates, (bytes, bytearray)):
            raw = [bytes(candidates).decode("utf-8", errors="replace").strip()]
        elif isinstance(candidates, Mapping):
            raw = [_normalize_text(item) for item in candidates.keys()]
            warnings.append("selected_ministers mapping normalized to its keys.")
        elif isinstance(candidates, (list, tuple, set)):
            raw = [_normalize_text(item) for item in candidates]
        elif isinstance(candidates, Iterable):
            raw_items, failed = _coerce_iterable_items(candidates, preserve_partial=True)
            raw = [_normalize_text(item) for item in raw_items]
            if failed:
                warnings.append(
                    "selected_ministers iterable iteration failed; partial values preserved."
                )
        else:
            if candidates not in (None, "", []):
                warnings.append("Invalid selected_ministers payload ignored.")
            raw = []

        normalized: List[str] = []
        seen = set()
        for item in raw:
            if not item:
                continue
            lowered = item.lower()
            canonical = _MINISTER_ALIASES.get(lowered, lowered)
            if canonical != lowered and emit_alias_warnings:
                warnings.append(f"minister alias '{lowered}' normalized to '{canonical}'.")
            if canonical not in available_ministers:
                if emit_unknown_warnings:
                    warnings.append(f"unknown minister '{lowered}' ignored.")
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            normalized.append(canonical)
        return normalized

    @staticmethod
    def _count_stances(positions: Dict[str, Dict[str, Any]]) -> tuple[int, int, int]:
        support_count = sum(
            1 for item in positions.values() if str(item.get("stance", "")).lower() == "support"
        )
        oppose_count = sum(
            1 for item in positions.values() if str(item.get("stance", "")).lower() == "oppose"
        )
        neutral_count = len(positions) - support_count - oppose_count
        return support_count, oppose_count, neutral_count

    @staticmethod
    def _build_council_positions(
        positions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return [
            {
                "minister": name,
                "stance": details.get("stance"),
                "confidence": details.get("confidence"),
                "reasoning": details.get("reasoning", ""),
                "red_line_triggered": details.get("red_line_triggered", False),
            }
            for name, details in positions.items()
        ]

    @staticmethod
    def _determine_recommendation(
        mode: str,
        support: int,
        oppose: int,
        neutral: int,
        positions: Dict[str, Dict[str, Any]],
    ) -> str:
        total = support + oppose + neutral
        if total == 0:
            return "insufficient_data"

        if mode == "war":
            if any(position.get("red_line_triggered") for position in positions.values()):
                return "red_line_block_override_needed"
            return "aggressive_proceed" if support >= oppose else "defensive_hold_or_pivot"

        if mode == "meeting":
            if support > oppose + neutral:
                return "strong_consensus_support"
            if oppose > support + neutral:
                return "strong_consensus_oppose"
            return "mixed_consensus_with_tradeoffs"

        if mode == "darbar":
            if any(position.get("red_line_triggered") for position in positions.values()):
                return "red_line_blocks_recommendation"

            consensus_pct = max(support, oppose) / total
            if consensus_pct >= 0.8:
                return "strong_doctrine_aligned_consensus"
            if consensus_pct >= 0.6:
                return "consensus_with_noted_dissent"
            return "deep_disagreement_defer_decision"

        if mode in {"quick", "baseline"}:
            return "direct_response"

        return "unknown_mode"

    def _normalize_requested_mode(self, mode: Any) -> tuple[str, str, str]:
        raw = _normalize_text(mode).lower()
        if not raw:
            return "meeting", "missing", raw

        normalized = self._normalize_mode(raw)
        valid = set(self.orchestrator.list_modes())
        if normalized not in valid:
            return "meeting", "unsupported", raw
        if normalized != raw:
            return normalized, "alias", raw
        return normalized, "direct", raw

    @staticmethod
    def _normalize_mode(mode: Any) -> str:
        raw = _normalize_text(mode).lower()
        if not raw:
            return ""
        return _MODE_ALIASES.get(raw, raw)

    def _normalize_context(self, value: Any, warnings: List[str]) -> Dict[str, Any]:
        payload = _coerce_mapping_like(value)
        if payload is None:
            if value not in (None, ""):
                warnings.append("Invalid council context payload normalized to empty mapping.")
            return {}

        sanitized: Dict[str, Any] = {}
        for key, raw_item in dict(payload).items():
            normalized_key = _normalize_text(key)
            if not normalized_key:
                continue
            item = self._to_jsonable(
                raw_item,
                warnings=warnings,
                path=f"context.{normalized_key}",
            )
            if item is None:
                continue
            sanitized[normalized_key] = item
        return sanitized

    def _to_jsonable(self, value: Any, *, warnings: List[str], path: str) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if math.isfinite(value):
                return value
            warnings.append(f"{path} had non-finite float and was dropped.")
            return None
        if isinstance(value, (bytes, bytearray)):
            return bytes(value).decode("utf-8", errors="replace")
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, Mapping):
            result: Dict[str, Any] = {}
            items, failed = _coerce_iterable_items(value.items(), preserve_partial=True)
            if failed:
                warnings.append(f"{path} mapping iteration failed; partial values preserved.")
            for raw_key, raw_item in items:
                item = self._to_jsonable(
                    raw_item,
                    warnings=warnings,
                    path=f"{path}.{_normalize_text(raw_key)}",
                )
                if item is None:
                    continue
                key = _normalize_text(raw_key)
                if not key:
                    continue
                result[key] = item
            return result
        if isinstance(value, (list, tuple, set)):
            result: List[Any] = []
            raw_items, failed = _coerce_iterable_items(value, preserve_partial=True)
            if failed:
                warnings.append(f"{path} iterable iteration failed; partial values preserved.")
            for index, raw_item in enumerate(raw_items):
                item = self._to_jsonable(
                    raw_item,
                    warnings=warnings,
                    path=f"{path}[{index}]",
                )
                if item is None:
                    continue
                result.append(item)
            return result

        warnings.append(f"{path} used non-serializable value and was stringified.")
        return str(value)

    @staticmethod
    def _to_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        text = _normalize_text(value).lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
        return None

    @staticmethod
    def _dedupe_warnings(warnings: List[str]) -> List[str]:
        deduped: List[str] = []
        seen = set()
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            deduped.append(warning)
        return deduped

    @staticmethod
    def _empty_council_result(
        *,
        outcome: str,
        recommendation: str,
        mode: str,
        reasoning: str,
        warnings: List[str],
    ) -> Dict[str, Any]:
        deduped_warnings = CouncilExecutionEngine._dedupe_warnings(warnings)
        return {
            "outcome": outcome,
            "recommendation": recommendation,
            "mode": mode,
            "ministers_involved": [],
            "ministers_failed": [],
            "minister_positions": {},
            "minister_outputs": {},
            "council_positions": [],
            "reasoning": reasoning,
            "consensus_strength": 0.0,
            "red_line_concerns": [],
            "total_ministers_consulted": 0,
            "support_count": 0,
            "oppose_count": 0,
            "neutral_count": 0,
            "warnings": deduped_warnings,
            "warning_count": len(deduped_warnings),
        }


def _native_keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    if not text:
        return 0.0
    hits = sum(1 for token in keywords if token in text)
    return min(1.0, hits / max(1, len(keywords)))


def _native_reasoning_for(
    minister: str,
    stance: str,
    urgency: float,
    risk_score: float,
    uncertainty: float,
) -> str:
    if stance == "oppose":
        if risk_score > 0.0:
            return f"{minister}: downside and irreversibility risk require a defensive posture."
        return f"{minister}: available evidence does not justify proceeding."
    if stance == "support":
        if urgency > 0.0:
            return f"{minister}: timing pressure favors decisive action with guardrails."
        return f"{minister}: expected upside and strategic alignment support proceeding."
    if uncertainty > 0.0:
        return f"{minister}: uncertainty is elevated; gather signal before commitment."
    return f"{minister}: maintain optionality while tracking new evidence."
