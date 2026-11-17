"""Central council execution engine for mode-aware minister deliberation."""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from modules.council_router.mode_orchestrator import ExecutionConfig, ModeOrchestrator
from modules.expert_router.aggregator import aggregate_weighted_positions

from persona.llm_errors import QuotaExhaustedError


_MEETING_MINISTERS = ["risk", "grand_strategist", "optionality", "psychology", "timing"]
_DARBAR_MINISTERS = [
    "risk", "grand_strategist", "power", "optionality", "psychology",
    "timing", "legitimacy", "truth", "data", "conflict",
    "diplomacy", "technology", "intelligence", "narrative",
    "discipline", "adaptation", "sovereign", "war_mode", "resources",
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
        try:
            _ct_mod = __import__("persona.learning.minister_confidence", fromlist=["MinisterConfidenceTracker"])
            self._confidence_tracker = _ct_mod.MinisterConfidenceTracker()
        except Exception:
            self._confidence_tracker = None

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

        if self.llm is not None:
            if mode in {"darbar", "full_council", "board"}:
                minister_names = _DARBAR_MINISTERS
            elif mode in {"war", "war_mode"}:
                minister_names = ["war_mode", "risk", "grand_strategist", "power", "timing"]
            elif mode in {"quick", "quick_mode", "fast"}:
                minister_names = ["risk", "grand_strategist", "adaptation"]
            else:
                try:
                    from modules.council_router.mode_orchestrator import ModeOrchestrator
                    r_context = dict(context)
                    r_context["user_input"] = user_input
                    selected = ModeOrchestrator().get_ministers_for_mode("meeting", r_context)
                    minister_names = selected[:4] if selected else _MEETING_MINISTERS[:4]
                except Exception:
                    minister_names = _MEETING_MINISTERS[:4]
            return self._llm_deliberate(user_input, context, minister_names)
        else:
            return self._keyword_deliberate(user_input, context)

    def _llm_deliberate(self, user_input: str, context: dict, minister_names: list) -> dict:
        """Call each minister via MinisterVoice, aggregate stances."""
        try:
            _mv_mod = __import__("persona.council.minister_voice", fromlist=["MinisterVoice"])
            MinisterVoice = _mv_mod.MinisterVoice
        except ImportError:
            res = self._keyword_deliberate(user_input, context)
            res["fallback_triggered"] = True
            res.setdefault("fallback_reasons", []).append("MinisterVoice module import failed; fell back to keyword scoring.")
            return res

        def _deliberate_one(name: str, ctx: dict, entries: list) -> tuple:
            """Deliberate a single minister. Returns (name, result_dict)."""
            voice = MinisterVoice(minister_name=name, llm=self.llm)
            result = voice.deliberate(user_input, ctx, knowledge_entries=entries, scenario_context=scenario_context)
            result["kis_entries"] = entries
            return name, result

        mode = str(context.get("mode", "meeting")).lower()
        active_domains = context.get("domains", [])

        # Extract scenario memory context for ministers
        extra_ctx = context.get("extra_context") or []
        if isinstance(extra_ctx, list):
            scenario_lines = [str(x) for x in extra_ctx if x]
        elif isinstance(extra_ctx, str):
            scenario_lines = [extra_ctx] if extra_ctx.strip() else []
        else:
            scenario_lines = []
        scenario_context = "\n".join(scenario_lines) if scenario_lines else ""
        
        def _get_minister_domain(m_name: str) -> str:
            mapping = {
                "grand_strategist": "strategy",
                "war_mode": "conflict",
                "intelligence": "data",
                "sovereign": "legitimacy",
                "narrative": "truth",
            }
            return mapping.get(m_name, m_name)

        minister_kis_map = {}
        all_cited_kis = []
        seen_global = set()
        try:
            _ke_mod = __import__("persona.knowledge_engine", fromlist=["synthesize_knowledge"])
            synthesize_knowledge = _ke_mod.synthesize_knowledge
            for name in minister_names:
                m_dom = _get_minister_domain(name)
                m_kis = synthesize_knowledge(
                    user_input=user_input,
                    active_domains=[m_dom],
                    domain_confidence=0.8,
                    max_items=15,  # ~3 of each category (rules, claims, warnings, principles, advice)
                )
                m_entries = m_kis.get("synthesized_knowledge", [])[:15]
                minister_kis_map[name] = m_entries
                for e in m_entries:
                    c_clean = str(e.get("content", "")).strip().lower()
                    if c_clean and c_clean not in seen_global:
                        seen_global.add(c_clean)
                        all_cited_kis.append(e)
        except Exception:
            pass

        # Round 1: all ministers deliberate (parallel)
        stances = {}
        with ThreadPoolExecutor(max_workers=min(len(minister_names), 4)) as pool:
            futures = {
                pool.submit(_deliberate_one, name, context, minister_kis_map.get(name, [])): name
                for name in minister_names
            }
            for future in as_completed(futures):
                try:
                    name, result = future.result(timeout=180)
                    stances[name] = result
                except QuotaExhaustedError:
                    raise
                except Exception as exc:
                    name = futures[future]
                    stances[name] = {
                        "stance": "neutral",
                        "reasoning": f"[{name} timed out: {exc}]",
                        "advice": f"[{name} unavailable]",
                        "questions": [],
                        "confidence": 0.2,
                        "warning": "",
                        "knowledge_cited": "",
                        "kis_entries": minister_kis_map.get(name, []),
                        "fallback_triggered": True,
                    }

        rounds = [{"round": 1, "stances": {n: r["stance"] for n, r in stances.items()}}]
        peer_challenges: Dict[str, str] = {}

        # Round 2 (darbar only): directed peer challenge — each minister sees peer arguments
        if mode == "darbar":
            # Build per-minister R2 contexts first (needs Round 1 stances)
            r2_contexts = {}
            for name in minister_names:
                my_r1 = stances[name]
                my_stance = my_r1["stance"]
                my_reason = my_r1["reasoning"]

                peers_to_cite = [
                    (peer, r)
                    for peer, r in stances.items()
                    if peer != name
                ]

                r2_ctx = dict(context)
                if peers_to_cite:
                    challenge_lines = []
                    for peer_name, peer_r in peers_to_cite:
                        q_str = f" | Questions asked: {'; '.join(peer_r.get('questions', []))}" if peer_r.get("questions") else ""
                        challenge_lines.append(
                            f"  - {peer_name.replace('_', ' ').title()} ({peer_r['stance']}): "
                            f"{peer_r['reasoning'][:200]}{q_str}"
                        )
                    r2_ctx["peer_challenge"] = (
                        f"Your Round 1 position: {my_stance} — {my_reason[:200]}\n\n"
                        f"Fellow ministers in this Darbar session:\n" + "\n".join(challenge_lines) + "\n\n"
                        f"Converse and debate directly! Address your colleagues by name, critique their assumptions, and argue vigorously from your own domain's doctrine!\n"
                        f"CRITICAL REQUIREMENT: Evolve your argument, formulate actionable advice, and answer peer questions!"
                    )
                else:
                    r2_ctx["peer_challenge"] = (
                        f"Your Round 1 position: {my_stance}. No peer stances available — confirm or refine."
                    )
                r2_contexts[name] = (r2_ctx, my_stance)

            # Parallel Round 2
            stances_r2 = {}
            with ThreadPoolExecutor(max_workers=min(len(minister_names), 4)) as pool:
                futures = {}
                for name in minister_names:
                    r2_ctx, _ = r2_contexts[name]
                    futures[pool.submit(_deliberate_one, name, r2_ctx, minister_kis_map.get(name, []))] = name
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        _, result = future.result(timeout=180)
                        stances_r2[name] = result
                        r1_stance = r2_contexts[name][1]
                        shift_note = f"[{r1_stance} -> {result['stance']}] " if result["stance"] != r1_stance else f"[{result['stance']}] "
                        peer_challenges[name] = f"{shift_note}{result['reasoning']}"
                    except QuotaExhaustedError:
                        raise
                    except Exception as exc:
                        stances_r2[name] = {
                            "stance": "neutral",
                            "reasoning": f"[{name} timed out in Round 2: {exc}]",
                            "advice": f"[{name} unavailable]",
                            "questions": [],
                            "confidence": 0.2,
                            "warning": "",
                            "knowledge_cited": "",
                            "kis_entries": minister_kis_map.get(name, []),
                            "fallback_triggered": True,
                        }

            rounds.append({"round": 2, "stances": {n: r["stance"] for n, r in stances_r2.items()}})
            stances = stances_r2  # final stances from round 2

        # Round 3 (darbar only, when dissent persists): Consensus & Reconciliation Round
        if mode == "darbar" and len(rounds) == 2:
            s_count = sum(1 for r in stances.values() if r["stance"] == "support")
            o_count = sum(1 for r in stances.values() if r["stance"] == "oppose")
            if s_count > 0 and o_count > 0:
                # Build per-minister R3 contexts first
                r3_contexts = {}
                for name in minister_names:
                    my_r2 = stances[name]
                    peers_to_cite = [(peer, r) for peer, r in stances.items() if peer != name]
                    challenge_lines = [
                        f"  - {peer_name.replace('_', ' ').title()} ({peer_r['stance']}): {peer_r['reasoning'][:200]}" + (f" | Questions: {'; '.join(peer_r.get('questions', []))}" if peer_r.get("questions") else "")
                        for peer_name, peer_r in peers_to_cite
                    ]
                    r3_ctx = dict(context)
                    r3_ctx["peer_challenge"] = (
                        f"Your Round 2 position: {my_r2['stance']} — {my_r2['reasoning'][:200]}\n\n"
                        f"Current Council Dissent after Round 2:\n" + "\n".join(challenge_lines) + "\n\n"
                        f"This is Round 3 (Consensus Reconciliation). Re-evaluate your position. Find synthesis, identify redlines, or defend your doctrine!\n"
                        f"CRITICAL REQUIREMENT: Evolve your advice to contribute to a unified execution plan. Answer peer questions!"
                    )
                    r3_contexts[name] = (r3_ctx, my_r2["stance"])

                # Parallel Round 3
                stances_r3 = {}
                with ThreadPoolExecutor(max_workers=min(len(minister_names), 4)) as pool:
                    futures = {}
                    for name in minister_names:
                        r3_ctx, _ = r3_contexts[name]
                        futures[pool.submit(_deliberate_one, name, r3_ctx, minister_kis_map.get(name, []))] = name
                    for future in as_completed(futures):
                        name = futures[future]
                        try:
                            _, result = future.result(timeout=180)
                            stances_r3[name] = result
                            my_r2_stance = r3_contexts[name][1]
                            shift_note = f"[{my_r2_stance} -> {result['stance']}] " if result["stance"] != my_r2_stance else f"[{result['stance']}] "
                            peer_challenges[name] = f"Round 3: {shift_note}{result['reasoning']}"
                        except QuotaExhaustedError:
                            raise
                        except Exception as exc:
                            stances_r3[name] = {
                                "stance": "neutral",
                                "reasoning": f"[{name} timed out in Round 3: {exc}]",
                                "advice": f"[{name} unavailable]",
                                "questions": [],
                                "confidence": 0.2,
                                "warning": "",
                                "knowledge_cited": "",
                                "kis_entries": minister_kis_map.get(name, []),
                                "fallback_triggered": True,
                            }
                    
                rounds.append({"round": 3, "stances": {n: r["stance"] for n, r in stances_r3.items()}})
                stances = stances_r3

        # Weighted vote tally — minister weight from Bayesian confidence tracker
        domain = context.get("domains", ["general"])[0] if context.get("domains") else "general"
        support = oppose = neutral = 0.0
        for name, r in stances.items():
            w = self._confidence_tracker.get_weight(name, domain) if self._confidence_tracker else 1.0
            stance = r["stance"]
            if stance == "support":
                support += w
            elif stance == "oppose":
                oppose += w
            else:
                neutral += w
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

        # Generate Dynamic Conversational Council Dialogue & KIS Advisory Synthesis
        dialogue_lines = [
            "=== ROYAL CABINET DEBATE (DARBAR DIALOGUE) ===\n"
        ]
        if all_cited_kis:
            kis_rules = [f"* [{e.get('_domain', 'general').upper()}] {e.get('content', '').strip()}" for e in all_cited_kis[:5]]
            dialogue_lines.append("[COUNCIL KIS DOCTRINE SYNTHESIS]:\n" + "\n".join(kis_rules) + "\n")
        
        dialogue_lines.append("[MINISTERIAL DELIBERATION & DOMAIN KIS]:")
        for n, r in stances.items():
            d_name = n.replace("_", " ").title()
            stance_tag = r["stance"].upper()
            reason = r["reasoning"].strip()
            r2_rebuttal = f"\n   -> Evolved Argument & Peer Rebuttal: \"{peer_challenges[n].strip()}\"" if n in peer_challenges else ""
            
            m_kis = r.get("kis_entries", [])
            kis_str = ""
            if m_kis:
                grouped_kis = {}
                for e in m_kis[:10]:
                    c = str(e.get('content', '')).strip()
                    if not c:
                        continue
                    cat = str(e.get('type', 'principle')).upper()
                    if not cat.endswith("S") and cat != "ADVICE":
                        cat += "S"
                    if cat not in grouped_kis:
                        grouped_kis[cat] = []
                    grouped_kis[cat].append(f"        * {c}")
                kis_lines = []
                for cat, items in grouped_kis.items():
                    kis_lines.append(f"      [{cat}]:")
                    kis_lines.extend(items)
                if kis_lines:
                    kis_str = "\n   [Domain KIS Doctrine Input to LLM Brain]:\n" + "\n".join(kis_lines)
            
            dialogue_lines.append(f"* {d_name} Minister [{stance_tag}]:{kis_str}\n   \"{reason}\"{r2_rebuttal}")
        
        dialogue_lines.append(f"\n[SOVEREIGN FINAL VERDICT]: {outcome.upper()}")
        if dissent_summary:
            dialogue_lines.append(f"[TRADE-OFF ANALYSIS]: {dissent_summary}")
        
        dialogue_lines.append("\n=== UNIFIED SOVEREIGN STRATEGIC ADVICE PLAN ===")
        dialogue_lines.append("An integrated execution plan formed by each minister contributing an actionable domain directive (evolved through peer debate while preserving core doctrine):")
        for n, r in stances.items():
            d_name = n.replace("_", " ").title()
            adv = r.get("advice") or r.get("reasoning", "")
            dialogue_lines.append(f"  * [{d_name} Directive]: {adv.strip()}")

        all_user_questions = []
        peers_to_check = [p for p in self.ministers.keys() if p != "sovereign"]
        for n, r in stances.items():
            d_name = n.replace("_", " ").title()
            qs = r.get("questions", [])
            for q in qs:
                if not (q and isinstance(q, str) and str(q).strip()):
                    continue
                q_clean = str(q).strip()
                # Filter out internal peer-to-peer cabinet questions so User/Sovereign only sees user-directed inquiries
                lower_q = q_clean.lower()
                is_peer_question = any(
                    lower_q.startswith(f"to {peer.replace('_', ' ')}") or f"to the {peer.replace('_', ' ')}" in lower_q or f"{peer.replace('_', ' ')} minister:" in lower_q
                    for peer in peers_to_check
                )
                if not is_peer_question:
                    all_user_questions.append(f"  * [{d_name} Minister asks Sovereign]: {q_clean}")

        if all_user_questions:
            dialogue_lines.append("\n=== MINISTERIAL INQUIRIES & CLARIFICATIONS FOR THE SOVEREIGN ===")
            dialogue_lines.append("To ensure precision and eliminate ambiguity, your cabinet respectfully requests clarification on the following domain points:")
            dialogue_lines.extend(all_user_questions[:8])

        advisory_dialogue = "\n".join(dialogue_lines)

        fallback_reasons = []
        for m_name, s_res in stances.items():
            if isinstance(s_res, dict) and s_res.get("fallback_triggered"):
                fallback_reasons.extend(s_res.get("fallback_reasons", []))

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
            "advisory_dialogue": advisory_dialogue,
            "user_questions": all_user_questions,
            "fallback_triggered": bool(fallback_reasons),
            "fallback_reasons": sorted(list(set(fallback_reasons))),
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
        is_fallback = (self.llm is None) or context.get("force_fallback", False)
        reasons = ["LLM service offline or unavailable; council defaulted to heuristic keyword scoring."] if is_fallback else []
        return {
            "outcome": outcome,
            "recommendation": outcome,
            "stances": stances,
            "consensus_strength": round(max(support, oppose) / total, 3),
            "red_line_concerns": [],
            "ministers_involved": list(self.ministers.keys()),
            "fallback_triggered": is_fallback,
            "fallback_reasons": reasons,
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

        # ── LLM-backed deliberation path ──────────────────────────────────
        # When an LLM is available, delegate to NativeCouncil.deliberate()
        # which runs parallel minister deliberation with KIS context, peer
        # challenge rounds, and generates the advisory_dialogue.
        council = self.base_council
        if self.llm is not None and hasattr(council, "deliberate"):
            deliberation_ctx = dict(context_map)
            deliberation_ctx["mode"] = resolved_mode
            try:
                delib_result = council.deliberate(user_input, deliberation_ctx)
                return self._map_deliberation_result(
                    delib_result,
                    resolved_mode=resolved_mode,
                    warnings=warnings,
                )
            except QuotaExhaustedError:
                raise
            except Exception as exc:
                warnings.append(
                    f"LLM deliberation failed ({type(exc).__name__}: {exc}); "
                    "falling back to keyword scoring."
                )

        # ── Keyword-based fallback path ───────────────────────────────────
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

    def _map_deliberation_result(
        self,
        delib_result: Dict[str, Any],
        *,
        resolved_mode: str,
        warnings: List[str],
    ) -> Dict[str, Any]:
        """Map NativeCouncil.deliberate() output to the convene() result envelope."""
        stances = delib_result.get("stances", {})
        minister_positions: Dict[str, Dict[str, Any]] = {}
        for name, raw in stances.items():
            if isinstance(raw, dict):
                minister_positions[name] = {
                    "stance": raw.get("stance", "neutral"),
                    "confidence": raw.get("confidence", 0.5),
                    "reasoning": raw.get("reasoning", ""),
                    "red_line_triggered": bool(raw.get("red_line_triggered", False)),
                }

        support_count = sum(1 for r in minister_positions.values() if r["stance"] == "support")
        oppose_count = sum(1 for r in minister_positions.values() if r["stance"] == "oppose")
        neutral_count = len(minister_positions) - support_count - oppose_count

        red_lines = [
            name for name, pos in minister_positions.items()
            if pos.get("red_line_triggered")
        ]

        council_positions = [
            {
                "minister": name,
                "stance": pos["stance"],
                "confidence": pos["confidence"],
                "reasoning": pos["reasoning"],
                "red_line_triggered": pos["red_line_triggered"],
            }
            for name, pos in minister_positions.items()
        ]

        # Propagate any fallback warnings from deliberation
        if delib_result.get("fallback_triggered"):
            for reason in delib_result.get("fallback_reasons", []):
                warnings.append(str(reason))

        deduped_warnings = self._dedupe_warnings(warnings)

        return {
            "outcome": delib_result.get("outcome", "deadlocked"),
            "recommendation": delib_result.get("recommendation", "defer"),
            "mode": resolved_mode,
            "ministers_involved": list(minister_positions.keys()),
            "ministers_failed": delib_result.get("ministers_failed", []),
            "minister_positions": minister_positions,
            "minister_outputs": minister_positions,
            "council_positions": council_positions,
            "mode_metadata": {},
            "weighted_aggregation": {},
            "support_count": support_count,
            "oppose_count": oppose_count,
            "neutral_count": neutral_count,
            "red_line_concerns": red_lines,
            "consensus_strength": delib_result.get("consensus_strength", 0.0),
            "total_ministers_consulted": len(minister_positions),
            "reasoning": delib_result.get("dissent_summary", ""),
            "requested_ministers": delib_result.get("ministers_involved", []),
            "warnings": deduped_warnings,
            "warning_count": len(deduped_warnings),
            # Carry through LLM-specific fields for response extraction
            "advisory_dialogue": delib_result.get("advisory_dialogue", ""),
            "peer_challenges": delib_result.get("peer_challenges", {}),
            "rounds": delib_result.get("rounds", []),
            "user_questions": delib_result.get("user_questions", []),
            "minority_alert": delib_result.get("minority_alert", ""),
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
