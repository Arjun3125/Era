"""Exogenous market dynamics and shocks for long-horizon simulations."""

from __future__ import annotations

from dataclasses import replace
import random

from .state_model import LongHorizonState, clamp_unit, clamp_cash, clamp_risk


def apply_market_shock(state: LongHorizonState, *, rng: random.Random) -> LongHorizonState:
    roll = rng.random()
    if roll < 0.1:
        return replace(
            state,
            competitor_strength=clamp_unit(state.competitor_strength + 0.1),
            market_share=clamp_unit(state.market_share - 0.02),
        )
    if roll < 0.2:
        return replace(
            state,
            market_share=clamp_unit(state.market_share - 0.03),
            cash=clamp_cash(state.cash - 50_000.0),
        )
    if roll < 0.3:
        return replace(
            state,
            reputation=clamp_unit(state.reputation - 0.04),
            risk_level=clamp_risk(state.risk_level + 0.05),
        )
    return state
