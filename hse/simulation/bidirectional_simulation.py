"""
Bidirectional LLM simulation: User LLM talks to Persona LLM.

Both sides are autonomous for stress testing and long-horizon evaluation.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from hse.crisis_injector import CrisisInjector
from hse.human_profile import SyntheticHuman
from hse.personality_drift import PersonalityDrift
from persona.state import CognitiveState


class BidirectionalSimulation:
    """
    Orchestrates autonomous conversation between:
    - User LLM (realistic synthetic human input)
    - Persona LLM (program response)
    """

    def __init__(
        self,
        human: SyntheticHuman,
        user_llm: Any,
        persona_llm: Any,
        council: Any = None,
        episodic_memory: Any = None,
        performance_metrics: Any = None,
    ):
        self.human = human
        self.user_llm = user_llm
        self.persona_llm = persona_llm
        self.council = council
        self.episodic_memory = episodic_memory
        self.performance_metrics = performance_metrics

        self.crisis_injector = CrisisInjector(seed=getattr(human, "seed", None))
        self.personality_drift = PersonalityDrift(seed=getattr(human, "seed", None))

        self.turn = 0
        self.current_mode = "quick"
        self.emotional_load = 0.30
        self.unresolved_issues: List[str] = []
        self.conversation_history: List[Tuple[str, str]] = []
        self.episode_log: List[Dict[str, Any]] = []

        # Crisis + drift modules use a dict profile; keep one synchronized with object state.
        self.human_profile = self._build_human_profile()

        self.metrics: Dict[str, Any] = {
            "total_turns": 0,
            "successful_turns": 0,
            "failed_turns": 0,
            "average_confidence": 0.0,
            "mode_switches": 0,
            "crises_triggered": 0,
        }

    def _build_human_profile(self) -> Dict[str, Any]:
        if hasattr(self.human, "profile"):
            profile = dict(self.human.profile())
        elif isinstance(self.human, dict):
            profile = dict(self.human)
        else:
            profile = {}

        profile.setdefault("id", getattr(self.human, "name", "synthetic_human"))
        profile.setdefault("name", getattr(self.human, "name", "Synthetic Human"))
        profile.setdefault("age", getattr(self.human, "age", 30))
        profile.setdefault("profession", getattr(self.human, "profession", "unknown"))
        profile.setdefault("wealth", getattr(self.human, "wealth", "unknown"))
        profile.setdefault("traits", dict(getattr(self.human, "traits", {})))
        profile.setdefault("biases", list(getattr(self.human, "biases", [])))
        profile.setdefault("repetition", float(getattr(self.human, "repetition", 0.0)))
        profile.setdefault("unresolved_issues", list(getattr(self.human, "unresolved_issues", [])))
        profile.setdefault("unresolved", list(profile.get("unresolved_issues", [])))
        self.unresolved_issues = list(profile.get("unresolved_issues", []))
        return profile

    def _sync_human_object(self) -> None:
        # Keep object state aligned for external consumers.
        if hasattr(self.human, "traits"):
            self.human.traits = dict(self.human_profile.get("traits", {}))
        if hasattr(self.human, "biases"):
            self.human.biases = list(self.human_profile.get("biases", []))
        if hasattr(self.human, "repetition"):
            self.human.repetition = float(self.human_profile.get("repetition", 0.0))
        if hasattr(self.human, "unresolved_issues"):
            self.human.unresolved_issues = list(self.unresolved_issues)
        if hasattr(self.human, "wealth"):
            self.human.wealth = self.human_profile.get("wealth", getattr(self.human, "wealth", "unknown"))

    def run_conversation(self, num_turns: int = 100, verbose: bool = True) -> Dict[str, Any]:
        if verbose:
            print(f"\n{'=' * 80}")
            print("BIDIRECTIONAL SIMULATION: User LLM <-> Persona LLM")
            print(f"{'=' * 80}")
            print(
                f"Human: {self.human_profile.get('name')} "
                f"(age {self.human_profile.get('age')}, {self.human_profile.get('profession')})"
            )
            print(f"Turns: {num_turns}")
            print(f"Start time: {datetime.now().isoformat()}")
            print(f"{'=' * 80}\n")

        for turn_num in range(1, num_turns + 1):
            self.turn = turn_num

            user_input = self._generate_user_input(turn_num=turn_num, verbose=verbose)
            persona_response, metadata = self._generate_persona_response(user_input=user_input, verbose=verbose)
            self._update_human_state(user_input=user_input, persona_response=persona_response, metadata=metadata)
            crisis = self._maybe_inject_crisis(turn_num=turn_num, verbose=verbose)
            episode = self._record_episode(
                turn_num=turn_num,
                user_input=user_input,
                persona_response=persona_response,
                metadata=metadata,
                crisis=crisis,
            )
            self._update_metrics(episode=episode)
            self._maybe_switch_mode(turn_num=turn_num, verbose=verbose)

            if verbose and turn_num % 10 == 0:
                self._print_turn_summary(turn_num=turn_num)

            time.sleep(0.05)

        if verbose:
            self._print_final_summary()

        return self._generate_final_report()

    def _generate_user_input(self, turn_num: int, verbose: bool = False) -> str:
        recent_response = self.conversation_history[-1][1] if self.conversation_history else None

        unresolved_block = "\n".join(f"  - {issue}" for issue in (self.unresolved_issues or ["None yet"]))
        context = f"""
You are {self.human_profile.get("name")}, a synthetic human navigating real life.

Background:
- Age: {self.human_profile.get("age")}
- Profession: {self.human_profile.get("profession")}
- Wealth: {self.human_profile.get("wealth")}
- Personality: {json.dumps(self.human_profile.get("traits", {}), indent=2)}
- Current emotional load: {self.emotional_load:.0%}

Unresolved issues:
{unresolved_block}

Turn: {turn_num}

{f'Persona just said: "{recent_response}"' if recent_response else "Starting a new conversation."}

Generate your next realistic human input:
- 1-3 sentences
- Natural conversational tone
- Follow up on unresolved issues if relevant
- Show emotional reaction to recent advice
- You may agree, push back, or ask for clarification

Return only the user message.
"""

        try:
            user_input = (self.user_llm.speak("", context) or "").strip()
        except Exception:
            user_input = "I am still uncertain. Can you help me choose a concrete next step?"

        if not user_input:
            user_input = "I need help deciding what to do next."

        if verbose:
            print(f"[Turn {turn_num}] USER: {user_input}")

        return user_input

    def _generate_persona_response(self, user_input: str, verbose: bool = False) -> Tuple[str, Dict[str, Any]]:
        from persona.context import build_system_context

        state = CognitiveState(mode=self.current_mode)
        state.turn_count = self.turn
        state.recent_turns = list(self.conversation_history[-6:])
        state.user_frequency = "medium"
        state.emotional_metrics = {"emotional_intensity": self.emotional_load}

        system_context = build_system_context(state)
        if self.current_mode == "quick":
            system_context += "\nQUICK MODE: direct, personal mentoring."
        elif self.current_mode == "war":
            system_context += "\nWAR MODE: prioritize advantage and decisive action."
        elif self.current_mode == "meeting":
            system_context += "\nMEETING MODE: balance perspectives and tradeoffs."
        elif self.current_mode == "darbar":
            system_context += "\nDARBAR MODE: full-spectrum, doctrine-aware deliberation."

        council_metadata: Dict[str, Any] = {}
        if self.current_mode in {"war", "meeting", "darbar"} and self.council is not None:
            council_context = {
                "domains": ["general"],
                "turn_count": self.turn,
                "recent_turns": self.conversation_history[-6:],
                "emotional_metrics": {"emotional_load": self.emotional_load},
                "mode": self.current_mode,
            }
            try:
                if hasattr(self.council, "convene_for_mode"):
                    council_metadata = self.council.convene_for_mode(self.current_mode, user_input, council_context) or {}
                elif hasattr(self.council, "convene"):
                    legacy = self.council.convene(user_input, council_context)
                    council_metadata = {
                        "recommendation": getattr(legacy, "recommendation", "unknown"),
                        "consensus_strength": float(getattr(legacy, "consensus_strength", 0.0) or 0.0),
                        "ministers_involved": list((getattr(legacy, "minister_positions", {}) or {}).keys()),
                        "red_line_concerns": list(getattr(legacy, "red_line_concerns", []) or []),
                    }
            except Exception as exc:
                council_metadata = {"error": str(exc), "ministers_involved": []}

            if council_metadata.get("recommendation"):
                system_context += f"\nCouncil recommendation: {council_metadata.get('recommendation')}."
            if council_metadata.get("red_line_concerns"):
                red_lines = ", ".join(council_metadata.get("red_line_concerns", []))
                system_context += f"\nRed line concerns: {red_lines}."

        try:
            response = (self.persona_llm.speak(system_context, user_input) or "").strip()
        except Exception as exc:
            response = f"I understand the concern. Let us proceed step by step. [LLM error: {exc}]"

        if not response:
            response = "I hear you. Let us map the next best action together."

        confidence = float(council_metadata.get("consensus_strength", 0.7) or 0.7)
        confidence = max(0.0, min(1.0, confidence))
        metadata = {
            "mode": self.current_mode,
            "council_involved": bool(council_metadata.get("ministers_involved")),
            "council_metadata": council_metadata,
            "confidence": confidence,
        }

        if verbose:
            print(f"[Turn {self.turn}] PERSONA ({self.current_mode}): {response}")
            if metadata["council_involved"]:
                ministers = ", ".join(council_metadata.get("ministers_involved", []))
                print(f"            [Ministers: {ministers}]")

        return response, metadata

    def _update_human_state(self, user_input: str, persona_response: str, metadata: Dict[str, Any]) -> None:
        self.conversation_history.append((user_input, persona_response))

        response_lower = persona_response.lower()
        if any(token in response_lower for token in ["understand", "valid", "important", "clear plan"]):
            self.emotional_load = max(0.0, self.emotional_load - 0.08)
        if any(token in response_lower for token in ["risk", "danger", "problem", "urgent"]):
            self.emotional_load = min(1.0, self.emotional_load + 0.05)

        input_lower = user_input.lower()
        if any(token in input_lower for token in ["stuck", "overwhelmed", "scared", "worried", "stress", "uncertain"]):
            issue = user_input[:140]
            if issue and issue not in self.unresolved_issues:
                self.unresolved_issues.append(issue)

        if self.emotional_load < 0.35 and self.unresolved_issues:
            self.unresolved_issues.pop(0)

        self.human_profile["unresolved_issues"] = list(self.unresolved_issues)
        self.human_profile["unresolved"] = list(self.unresolved_issues)
        self.human_profile["repetition"] = min(1.0, float(self.human_profile.get("repetition", 0.0)) + 0.01)

        signals = {
            "stress": self.emotional_load,
            "success_rate": 1.0 - self.emotional_load,
            "repetition": float(self.human_profile.get("repetition", 0.0)),
        }
        self.personality_drift.apply(self.human_profile, signals)
        self._sync_human_object()

    def _maybe_inject_crisis(self, turn_num: int, verbose: bool = False) -> Optional[Dict[str, Any]]:
        hid = self.human_profile.get("id", self.human_profile.get("name", "synthetic_human"))
        crisis = self.crisis_injector.maybe_inject(hid, self.human_profile, turn_num)

        if crisis:
            severity = float(crisis.get("crisis", {}).get("severity", 0.5) or 0.5)
            self.emotional_load = min(1.0, self.emotional_load + (0.15 + severity * 0.15))
            unresolved = list(self.human_profile.get("unresolved", []))
            for issue in unresolved:
                if issue not in self.unresolved_issues:
                    self.unresolved_issues.append(issue)

            if verbose:
                label = crisis.get("crisis", {}).get("label", "unknown_crisis")
                print(f"            [CRISIS] {label}")

        return crisis

    def _record_episode(
        self,
        turn_num: int,
        user_input: str,
        persona_response: str,
        metadata: Dict[str, Any],
        crisis: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        outcome = "success" if self.emotional_load < 0.5 else "failure"
        episode = {
            "turn": turn_num,
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "persona_response": persona_response,
            "mode": metadata.get("mode", self.current_mode),
            "council_involved": bool(metadata.get("council_involved", False)),
            "emotional_load": self.emotional_load,
            "crisis_triggered": crisis is not None,
            "confidence": float(metadata.get("confidence", 0.7)),
            "outcome": outcome,
            "domain": "general",
        }
        self.episode_log.append(episode)

        if self.episodic_memory is not None:
            try:
                from persona.learning.episodic_memory import Episode

                council_meta = metadata.get("council_metadata", {}) or {}
                ep = Episode(
                    episode_id=None,
                    turn_id=turn_num,
                    domain="general",
                    user_input=user_input,
                    persona_recommendation=persona_response,
                    confidence=float(metadata.get("confidence", 0.7)),
                    minister_stance=str(council_meta.get("recommendation", "unknown")),
                    council_recommendation=str(council_meta.get("outcome", "simulated")),
                    outcome=outcome,
                    regret_score=max(0.0, min(1.0, self.emotional_load)),
                )
                self.episodic_memory.store_episode(ep)
            except Exception:
                # Episodic storage must not break simulation flow.
                pass

        return episode

    def _update_metrics(self, episode: Dict[str, Any]) -> None:
        self.metrics["total_turns"] += 1
        if episode.get("crisis_triggered"):
            self.metrics["crises_triggered"] += 1

        if episode.get("outcome") == "success":
            self.metrics["successful_turns"] += 1
        else:
            self.metrics["failed_turns"] += 1

        n = self.metrics["total_turns"]
        prev_avg = float(self.metrics.get("average_confidence", 0.0))
        conf = float(episode.get("confidence", 0.7))
        self.metrics["average_confidence"] = ((prev_avg * (n - 1)) + conf) / n

        if self.performance_metrics is not None:
            try:
                self.performance_metrics.record_decision(
                    turn=int(episode["turn"]),
                    domain=str(episode["domain"]),
                    recommendation=str(episode["persona_response"])[:100],
                    confidence=float(episode["confidence"]),
                    outcome=str(episode["outcome"]),
                    regret=max(0.0, min(1.0, self.emotional_load)),
                )
            except Exception:
                pass

    def _maybe_switch_mode(self, turn_num: int, verbose: bool = False) -> None:
        if turn_num < 20 or turn_num % 20 != 0:
            return

        old_mode = self.current_mode
        if self.emotional_load >= 0.75:
            new_mode = "darbar"
        elif self.emotional_load >= 0.55:
            new_mode = "meeting"
        elif self.emotional_load >= 0.40:
            new_mode = "war"
        else:
            new_mode = "quick"

        if new_mode != old_mode:
            self.current_mode = new_mode
            if self.council is not None and hasattr(self.council, "set_mode"):
                try:
                    self.council.set_mode(new_mode)
                except Exception:
                    pass
            self.metrics["mode_switches"] += 1
            if verbose:
                print(f"            [MODE SWITCH] {old_mode.upper()} -> {new_mode.upper()}")

    def _print_turn_summary(self, turn_num: int) -> None:
        success_rate = self.metrics["successful_turns"] / max(1, self.metrics["total_turns"])
        print(f"\n--- TURN {turn_num} SUMMARY ---")
        print(f"Emotional load: {self.emotional_load:.0%}")
        print(f"Mode: {self.current_mode}")
        print(f"Crises so far: {self.metrics['crises_triggered']}")
        print(f"Success rate: {success_rate:.0%}")
        print(f"Mode switches: {self.metrics['mode_switches']}")

    def _print_final_summary(self) -> None:
        success_rate = self.metrics["successful_turns"] / max(1, self.metrics["total_turns"])
        print(f"\n{'=' * 80}")
        print(f"SIMULATION COMPLETE: {self.metrics['total_turns']} turns")
        print(f"{'=' * 80}")
        print(f"Success rate: {success_rate:.0%}")
        print(f"Failed turns: {self.metrics['failed_turns']}")
        print(f"Crises triggered: {self.metrics['crises_triggered']}")
        print(f"Mode switches: {self.metrics['mode_switches']}")
        print(f"Final emotional load: {self.emotional_load:.0%}")
        print(f"Conversation length: {len(self.conversation_history)} exchanges")
        print(f"{'=' * 80}\n")

    def _human_state_snapshot(self) -> Dict[str, Any]:
        base = self.human.profile() if hasattr(self.human, "profile") else {}
        return {
            "base_profile": base,
            "runtime_profile": self.human_profile,
            "unresolved_issues": list(self.unresolved_issues),
        }

    def _generate_final_report(self) -> Dict[str, Any]:
        return {
            "simulation_metrics": self.metrics,
            "conversation_history": self.conversation_history,
            "episode_log": self.episode_log,
            "final_emotional_load": self.emotional_load,
            "human_final_state": self._human_state_snapshot(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def save_report(self, filepath: str = "data/memory/simulation_report.json") -> None:
        report = self._generate_final_report()
        try:
            from pathlib import Path

            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"[OK] Report saved to {filepath}")
        except Exception as exc:
            print(f"[ERROR] Failed to save report: {exc}")
