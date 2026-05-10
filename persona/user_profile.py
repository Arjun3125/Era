"""Persistent user profile — survives across API sessions."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


def _profile_dir() -> Path:
    base = os.environ.get("ERA_PROFILE_PATH") or str(
        Path(__file__).resolve().parent.parent / "data" / "user_profiles"
    )
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class UserProfile:
    user_id: str
    risk_tolerance: str = "moderate"       # cautious | moderate | bold
    recurring_themes: List[str] = field(default_factory=list)
    total_turns: int = 0
    successful_decisions: int = 0
    failed_decisions: int = 0
    last_active: Optional[str] = None
    notes: str = ""                        # free-text notes added by N

    def update_themes(self, new_domains: List[str]) -> None:
        """Append domains not already in the list."""
        for d in new_domains:
            if d and d not in self.recurring_themes:
                self.recurring_themes.append(d)

    def record_outcome(self, success: bool) -> None:
        if success:
            self.successful_decisions += 1
        else:
            self.failed_decisions += 1

    def success_rate(self) -> float:
        total = self.successful_decisions + self.failed_decisions
        return self.successful_decisions / total if total else 0.0

    def to_context_hint(self) -> str:
        """One-line string injected into the system prompt."""
        themes = ", ".join(self.recurring_themes[-5:]) if self.recurring_themes else "none yet"
        return (
            f"User profile: risk={self.risk_tolerance}, "
            f"themes={themes}, "
            f"turns={self.total_turns}, "
            f"success_rate={self.success_rate():.0%}"
        )


def save_profile(profile: UserProfile) -> None:
    path = _profile_dir() / f"{profile.user_id}.json"
    path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")


def load_profile(user_id: str) -> Optional[UserProfile]:
    path = _profile_dir() / f"{user_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserProfile(**data)
    except Exception:
        return None


def get_or_create_profile(user_id: str) -> UserProfile:
    profile = load_profile(user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        save_profile(profile)
    return profile
