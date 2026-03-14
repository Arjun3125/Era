"""Human Simulation Engine (HSE) modules.

Provides synthetic human population simulation with:
- SyntheticHuman: persona with traits, wealth, decisions
- PopulationManager: manages cohorts of humans
- CrisisInjector: injects random life events
- PersonalityDrift: tracks evolving traits
- AnalyticsServer: live metrics streaming (Flask SSE)
"""
from .human_profile import SyntheticHuman, build_user_prompt
from .population_manager import PopulationManager
from .crisis_injector import CrisisInjector
from .personality_drift import PersonalityDrift

__all__ = ["SyntheticHuman", "build_user_prompt", "PopulationManager", "CrisisInjector", "PersonalityDrift"]
