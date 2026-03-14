"""Generate ERA-Bench scenarios with context-driven expected decisions."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def scale(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 0.0
    return clamp((value - min_value) / (max_value - min_value))


def cat_score(value: str, mapping: Dict[str, float]) -> float:
    return mapping.get(str(value).lower(), 0.5)


def pick_category(value: float, mapping: Dict[str, Tuple[float, float]]) -> str:
    for name, (low, high) in mapping.items():
        if low <= value <= high:
            return name
    return next(iter(mapping))


def difficulty_from_margin(margin: float) -> str:
    if margin >= 0.45:
        return "easy"
    if margin >= 0.25:
        return "medium"
    if margin >= 0.12:
        return "hard"
    return "expert"


def build_base_context(rng: random.Random) -> Dict[str, Any]:
    company_size = rng.choice(["small", "mid", "large"])
    cash_reserve_months = rng.randint(3, 24)
    brand_strength = rng.choice(["low", "medium", "high"])
    customer_loyalty = rng.choice(["low", "moderate", "high"])
    regulatory_pressure = rng.choice(["low", "medium", "high"])
    time_pressure_days = rng.randint(5, 60)
    urgency_rank = rng.randint(1, 3)
    growth_outlook = rng.choice(["low", "moderate", "high"])
    stake_level = rng.choice(["low", "medium", "high"])
    reversibility = rng.choice(["low", "medium", "high"])
    decision_horizon_months = rng.randint(3, 24)
    industry = rng.choice(["saas", "fintech", "health", "retail", "industrial", "media"])
    return {
        "company_size": company_size,
        "cash_reserve_months": cash_reserve_months,
        "brand_strength": brand_strength,
        "customer_loyalty": customer_loyalty,
        "regulatory_pressure": regulatory_pressure,
        "time_pressure_days": time_pressure_days,
        "urgency_rank": urgency_rank,
        "growth_outlook": growth_outlook,
        "stake_level": stake_level,
        "reversibility": reversibility,
        "decision_horizon_months": decision_horizon_months,
        "industry": industry,
    }


def derived_features(context: Dict[str, Any]) -> Dict[str, float]:
    return {
        "cash_reserve_score": scale(float(context.get("cash_reserve_months", 12)), 3, 24),
        "brand_strength_score": cat_score(
            context.get("brand_strength", "medium"),
            {"low": 0.2, "medium": 0.55, "high": 0.9},
        ),
        "customer_loyalty_score": cat_score(
            context.get("customer_loyalty", "moderate"),
            {"low": 0.25, "moderate": 0.55, "high": 0.85},
        ),
        "regulatory_pressure_score": cat_score(
            context.get("regulatory_pressure", "medium"),
            {"low": 0.2, "medium": 0.55, "high": 0.85},
        ),
        "time_pressure_score": 1.0 - scale(float(context.get("time_pressure_days", 30)), 5, 60),
        "growth_outlook_score": cat_score(
            context.get("growth_outlook", "moderate"),
            {"low": 0.2, "moderate": 0.55, "high": 0.85},
        ),
    }


def set_feature(context: Dict[str, Any], feature: str, value: float, rng: random.Random) -> None:
    value = clamp(value)
    if feature == "cash_reserve_score":
        context["cash_reserve_months"] = int(round(3 + value * (24 - 3)))
        return
    if feature == "time_pressure_score":
        context["time_pressure_days"] = int(round(60 - value * (60 - 5)))
        return
    if feature == "brand_strength_score":
        context["brand_strength"] = pick_category(
            value, {"low": (0.0, 0.33), "medium": (0.34, 0.66), "high": (0.67, 1.0)}
        )
        return
    if feature == "customer_loyalty_score":
        context["customer_loyalty"] = pick_category(
            value, {"low": (0.0, 0.33), "moderate": (0.34, 0.66), "high": (0.67, 1.0)}
        )
        return
    if feature == "regulatory_pressure_score":
        context["regulatory_pressure"] = pick_category(
            value, {"low": (0.0, 0.33), "medium": (0.34, 0.66), "high": (0.67, 1.0)}
        )
        return
    if feature == "growth_outlook_score":
        context["growth_outlook"] = pick_category(
            value, {"low": (0.0, 0.33), "moderate": (0.34, 0.66), "high": (0.67, 1.0)}
        )
        return
    context[feature] = round(value, 3)


def bias_context(
    context: Dict[str, Any],
    weights: Dict[str, float],
    rng: random.Random,
    strength: float = 0.25,
) -> None:
    for feature, weight in weights.items():
        if weight > 0:
            target = rng.uniform(0.7, 1.0)
        elif weight < 0:
            target = rng.uniform(0.0, 0.3)
        else:
            target = rng.uniform(0.35, 0.65)
        current = derived_features(context).get(feature, context.get(feature, rng.uniform(0.35, 0.65)))
        blended = clamp((1 - strength) * current + strength * target)
        set_feature(context, feature, blended, rng)


@dataclass
class Template:
    name: str
    category: str
    title: str
    option_keys: List[str]
    option_variants: Dict[str, List[str]]
    weights: Dict[str, Dict[str, float]]
    rubric_map: Dict[str, List[str]]
    context_builder: callable
    prompt_builder: callable


def score_options(template: Template, context: Dict[str, Any], rng: random.Random) -> Tuple[str, Dict[str, float]]:
    feature_values = derived_features(context)
    feature_values.update({k: float(v) for k, v in context.items() if isinstance(v, (int, float))})
    scores: Dict[str, float] = {}
    for option_key in template.option_keys:
        option_weights = template.weights[option_key]
        total = 0.0
        for feature, weight in option_weights.items():
            total += weight * feature_values.get(feature, 0.5)
        total += rng.uniform(-0.02, 0.02)
        scores[option_key] = total
    expected = max(scores.items(), key=lambda item: item[1])[0]
    return expected, scores


def build_price_war_template() -> Template:
    option_keys = ["cut_price", "differentiate", "marketing_push", "bundle", "focus_enterprise"]
    option_variants = {
        "cut_price": ["lower price", "discount aggressively", "temporary price cut"],
        "differentiate": ["add premium features", "increase differentiation", "improve product quality"],
        "marketing_push": ["increase marketing", "boost marketing spend", "run aggressive campaigns"],
        "bundle": ["bundle services", "offer product bundles", "package services"],
        "focus_enterprise": ["focus enterprise tier", "shift to enterprise buyers", "prioritize enterprise deals"],
    }
    weights = {
        "cut_price": {"cash_reserve_score": 0.5, "price_sensitivity": 0.5, "brand_strength_score": -0.3},
        "differentiate": {"r_and_d_capacity": 0.6, "brand_strength_score": 0.4},
        "marketing_push": {"market_awareness": -0.4, "cash_reserve_score": 0.4, "customer_loyalty_score": -0.2},
        "bundle": {"product_breadth": 0.6, "cash_reserve_score": 0.2},
        "focus_enterprise": {"enterprise_fit": 0.7, "brand_strength_score": 0.2},
    }
    rubric = {
        "cut_price": ["capture price-sensitive demand", "defend market share", "accept margin pressure"],
        "differentiate": ["avoid destructive price war", "protect margin", "increase differentiation"],
        "marketing_push": ["increase awareness", "defend share", "short-term demand boost"],
        "bundle": ["raise switching costs", "increase perceived value", "reduce churn"],
        "focus_enterprise": ["prioritize high-value accounts", "protect margin", "stabilize revenue"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "price_sensitivity": round(rng.uniform(0.1, 0.9), 3),
            "r_and_d_capacity": round(rng.uniform(0.1, 0.9), 3),
            "market_awareness": round(rng.uniform(0.1, 0.9), 3),
            "product_breadth": round(rng.uniform(0.1, 0.9), 3),
            "enterprise_fit": round(rng.uniform(0.1, 0.9), 3),
            "competitor_price_cut_pct": rng.randint(10, 70),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "A rival just cut price by "
            f"{context['competitor_price_cut_pct']}%. Users are churning and sales is feeling pressure. "
            "Decide the best competitive response."
        )

    return Template(
        name="price_war",
        category="strategy",
        title="Competitor price pressure",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_market_entry_template() -> Template:
    option_keys = ["launch_now", "delay_localize", "partner_local", "acquire_local", "abandon"]
    option_variants = {
        "launch_now": ["launch immediately", "enter the market now", "go live now"],
        "delay_localize": ["delay and localize", "localize before launch", "postpone for localization"],
        "partner_local": ["partner with a local firm", "form a local partnership", "joint venture with local player"],
        "acquire_local": ["acquire a local startup", "buy a local competitor", "strategic acquisition"],
        "abandon": ["abandon entry", "pause entry indefinitely", "exit the opportunity"],
    }
    weights = {
        "launch_now": {
            "strategic_importance": 0.5,
            "market_uncertainty": -0.4,
            "cash_reserve_score": 0.2,
            "regulatory_pressure_score": -0.3,
        },
        "delay_localize": {"market_uncertainty": 0.6, "regulatory_pressure_score": 0.3},
        "partner_local": {"local_partner_available": 0.6, "market_uncertainty": 0.2, "cash_reserve_score": -0.2},
        "acquire_local": {"cash_reserve_score": 0.6, "strategic_importance": 0.4, "market_uncertainty": -0.2},
        "abandon": {"market_uncertainty": 0.5, "strategic_importance": -0.5, "cash_reserve_score": -0.3},
    }
    rubric = {
        "launch_now": ["capture first-mover advantage", "accept execution risk", "move quickly"],
        "delay_localize": ["reduce regulatory risk", "adapt to local needs", "avoid premature launch"],
        "partner_local": ["share risk", "gain local expertise", "speed market access"],
        "acquire_local": ["buy market access", "accelerate entry", "use cash advantage"],
        "abandon": ["avoid sunk costs", "preserve focus", "exit low-value market"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "market_uncertainty": round(rng.uniform(0.1, 0.9), 3),
            "local_partner_available": float(rng.choice([0.0, 1.0])),
            "strategic_importance": round(rng.uniform(0.1, 0.9), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Your company is considering entry into a new region with uncertain demand and regulatory "
            "complexity. Decide the best market entry strategy."
        )

    return Template(
        name="market_entry",
        category="strategy",
        title="Market entry decision",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_security_breach_template() -> Template:
    option_keys = ["notify_regulators", "contain_and_patch", "public_disclosure", "shut_down_systems", "monitor_only"]
    option_variants = {
        "notify_regulators": ["notify regulators", "report to regulators", "file a regulatory disclosure"],
        "contain_and_patch": ["contain and patch", "isolate and fix quickly", "patch immediately"],
        "public_disclosure": ["publicly disclose", "issue a public statement", "notify customers publicly"],
        "shut_down_systems": ["shut down systems", "halt services temporarily", "freeze operations"],
        "monitor_only": ["monitor only", "watch and wait", "observe without action"],
    }
    weights = {
        "notify_regulators": {"severity": 0.6, "regulatory_pressure_score": 0.5, "data_sensitivity": 0.2},
        "contain_and_patch": {"severity": 0.4, "exploit_active": 0.5, "data_sensitivity": 0.2},
        "public_disclosure": {"customer_loyalty_score": 0.5, "severity": 0.4, "public_visibility": 0.3},
        "shut_down_systems": {"exploit_active": 0.6, "severity": 0.6, "cash_reserve_score": -0.3},
        "monitor_only": {"severity": -0.6, "data_sensitivity": -0.3, "regulatory_pressure_score": -0.3},
    }
    rubric = {
        "notify_regulators": ["regulatory compliance", "limit legal exposure", "document incident"],
        "contain_and_patch": ["stop the breach", "reduce ongoing harm", "restore security quickly"],
        "public_disclosure": ["maintain trust", "communicate transparently", "reduce reputational risk"],
        "shut_down_systems": ["contain rapidly", "prevent escalation", "accept short-term disruption"],
        "monitor_only": ["low severity", "avoid overreaction", "gather more data"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "severity": round(rng.uniform(0.1, 1.0), 3),
            "exploit_active": float(rng.choice([0.0, 1.0])),
            "data_sensitivity": round(rng.uniform(0.1, 1.0), 3),
            "public_visibility": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Your security team reports a breach impacting customer data. Assess the severity and decide the "
            "most responsible immediate response."
        )

    return Template(
        name="security_breach",
        category="risk",
        title="Security breach response",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_supply_chain_template() -> Template:
    option_keys = ["diversify_suppliers", "stockpile_inventory", "pause_sales", "expedite_alternative", "do_nothing"]
    option_variants = {
        "diversify_suppliers": ["diversify suppliers", "add backup suppliers", "dual-source components"],
        "stockpile_inventory": ["stockpile inventory", "build safety stock", "increase inventory buffer"],
        "pause_sales": ["pause sales", "slow order intake", "temporarily halt new orders"],
        "expedite_alternative": ["expedite alternative supply", "rush alternative sourcing", "fast-track substitutes"],
        "do_nothing": ["do nothing", "maintain current plan", "wait and reassess"],
    }
    weights = {
        "diversify_suppliers": {"supplier_concentration": 0.6, "lead_time_risk": 0.4},
        "stockpile_inventory": {"lead_time_risk": 0.5, "demand_volatility": 0.3, "cash_reserve_score": 0.2},
        "pause_sales": {"inventory_cover": -0.6, "lead_time_risk": 0.4, "demand_volatility": 0.2},
        "expedite_alternative": {"lead_time_risk": 0.5, "cash_reserve_score": 0.3, "demand_volatility": 0.2},
        "do_nothing": {"lead_time_risk": -0.5, "supplier_concentration": -0.4, "demand_volatility": -0.2},
    }
    rubric = {
        "diversify_suppliers": ["reduce single point of failure", "improve resilience", "manage supplier risk"],
        "stockpile_inventory": ["buffer against delays", "maintain service levels", "use cash strategically"],
        "pause_sales": ["avoid overcommitment", "match supply to demand", "protect reputation"],
        "expedite_alternative": ["reduce lead time risk", "maintain commitments", "pay for speed"],
        "do_nothing": ["risk is low", "avoid unnecessary cost", "monitor situation"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "supplier_concentration": round(rng.uniform(0.1, 1.0), 3),
            "lead_time_risk": round(rng.uniform(0.1, 1.0), 3),
            "demand_volatility": round(rng.uniform(0.1, 1.0), 3),
            "inventory_cover": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "A key supplier signals potential delays that could disrupt delivery timelines. Decide the best "
            "supply chain response."
        )

    return Template(
        name="supply_chain",
        category="risk",
        title="Supply chain disruption",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_ai_bias_template() -> Template:
    option_keys = ["pause_and_audit", "release_with_mitigation", "transparent_disclosure", "quiet_fix", "deny"]
    option_variants = {
        "pause_and_audit": ["pause and audit", "halt release for audit", "stop rollout for review"],
        "release_with_mitigation": ["release with mitigation", "ship with safeguards", "deploy with guardrails"],
        "transparent_disclosure": ["transparent disclosure", "publicly disclose issues", "open communication"],
        "quiet_fix": ["quietly fix", "fix internally first", "address silently"],
        "deny": ["deny claims", "reject allegations", "dismiss the report"],
    }
    weights = {
        "pause_and_audit": {"harm_level": 0.6, "evidence_strength": 0.5, "regulatory_pressure_score": 0.3},
        "release_with_mitigation": {"revenue_dependency": 0.5, "harm_level": -0.4},
        "transparent_disclosure": {"public_visibility": 0.5, "evidence_strength": 0.4, "customer_loyalty_score": 0.2},
        "quiet_fix": {"evidence_strength": 0.4, "public_visibility": -0.4, "revenue_dependency": 0.2},
        "deny": {"evidence_strength": -0.6, "public_visibility": -0.2, "regulatory_pressure_score": -0.3},
    }
    rubric = {
        "pause_and_audit": ["prevent harm", "validate evidence", "regain trust"],
        "release_with_mitigation": ["maintain momentum", "add safeguards", "monitor outcomes"],
        "transparent_disclosure": ["build trust", "show accountability", "reduce backlash"],
        "quiet_fix": ["address issue quickly", "avoid panic", "correct silently"],
        "deny": ["challenge weak evidence", "limit exposure", "avoid overreaction"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "harm_level": round(rng.uniform(0.1, 1.0), 3),
            "evidence_strength": round(rng.uniform(0.1, 1.0), 3),
            "revenue_dependency": round(rng.uniform(0.1, 1.0), 3),
            "public_visibility": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "An external report claims your AI model shows bias in a critical workflow. Decide the most "
            "ethical response."
        )

    return Template(
        name="ai_bias",
        category="ethics",
        title="AI bias allegation",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_layoff_template() -> Template:
    option_keys = ["layoff_now", "redeploy_staff", "pay_cuts", "hiring_freeze", "seek_financing"]
    option_variants = {
        "layoff_now": ["layoff now", "immediate layoffs", "reduce headcount"],
        "redeploy_staff": ["redeploy staff", "shift teams", "reassign employees"],
        "pay_cuts": ["implement pay cuts", "temporary salary reduction", "across-the-board cuts"],
        "hiring_freeze": ["hiring freeze", "pause hiring", "stop new hiring"],
        "seek_financing": ["seek financing", "raise bridge capital", "secure new funding"],
    }
    weights = {
        "layoff_now": {"cost_gap": 0.6, "cash_reserve_score": -0.4, "growth_outlook_score": -0.2},
        "redeploy_staff": {"hiring_friction": 0.4, "growth_outlook_score": 0.3, "morale_risk": 0.2},
        "pay_cuts": {"morale_risk": 0.5, "cost_gap": 0.3, "cash_reserve_score": -0.2},
        "hiring_freeze": {"cost_gap": 0.4, "cash_reserve_score": -0.3, "growth_outlook_score": -0.2},
        "seek_financing": {"growth_outlook_score": 0.5, "cash_reserve_score": -0.4, "cost_gap": 0.2},
    }
    rubric = {
        "layoff_now": ["extend runway", "reduce fixed costs", "accept morale impact"],
        "redeploy_staff": ["retain talent", "focus on priority work", "minimize disruption"],
        "pay_cuts": ["share burden", "avoid layoffs", "improve runway"],
        "hiring_freeze": ["control costs", "avoid immediate layoffs", "preserve optionality"],
        "seek_financing": ["protect growth", "extend runway", "use capital access"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "cost_gap": round(rng.uniform(0.1, 1.0), 3),
            "morale_risk": round(rng.uniform(0.1, 1.0), 3),
            "hiring_friction": round(rng.uniform(0.1, 1.0), 3),
            "growth_outlook": rng.choice(["low", "moderate", "high"]),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Revenue has slowed and expenses exceed plan. Leadership must choose a workforce strategy to "
            "stabilize finances while protecting long-term capability."
        )

    return Template(
        name="layoffs",
        category="ethics",
        title="Workforce reduction dilemma",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_budget_allocation_template() -> Template:
    option_keys = ["invest_engineering", "invest_marketing", "invest_sales", "invest_infra", "reduce_burn"]
    option_variants = {
        "invest_engineering": ["invest in engineering", "increase product investment", "fund engineering capacity"],
        "invest_marketing": ["invest in marketing", "boost marketing spend", "expand campaigns"],
        "invest_sales": ["invest in sales", "grow sales team", "expand sales coverage"],
        "invest_infra": ["invest in infrastructure", "increase reliability spend", "fund platform stability"],
        "reduce_burn": ["reduce burn", "cut discretionary spend", "slow spending"],
    }
    weights = {
        "invest_engineering": {"product_quality_gap": 0.6, "reliability_risk": 0.3},
        "invest_marketing": {"demand_gap": 0.6, "cash_reserve_score": 0.2},
        "invest_sales": {"conversion_gap": 0.6, "cash_reserve_score": 0.2},
        "invest_infra": {"reliability_risk": 0.7, "product_quality_gap": 0.2},
        "reduce_burn": {"cash_reserve_score": -0.6, "demand_gap": -0.2},
    }
    rubric = {
        "invest_engineering": ["fix product gaps", "improve retention", "build differentiation"],
        "invest_marketing": ["increase demand", "support growth", "build pipeline"],
        "invest_sales": ["improve conversion", "close deals", "expand revenue"],
        "invest_infra": ["protect uptime", "reduce risk", "support scale"],
        "reduce_burn": ["extend runway", "control costs", "prioritize survival"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "product_quality_gap": round(rng.uniform(0.1, 1.0), 3),
            "demand_gap": round(rng.uniform(0.1, 1.0), 3),
            "conversion_gap": round(rng.uniform(0.1, 1.0), 3),
            "reliability_risk": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Your annual budget is constrained. Decide where to allocate incremental spend for the next "
            "two quarters."
        )

    return Template(
        name="budget_allocation",
        category="resource_allocation",
        title="Budget allocation decision",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_staffing_allocation_template() -> Template:
    option_keys = ["hire_engineers", "hire_ops", "hire_sales", "use_contractors", "freeze_hiring"]
    option_variants = {
        "hire_engineers": ["hire engineers", "expand engineering team", "add developers"],
        "hire_ops": ["hire operations staff", "add reliability engineers", "grow ops team"],
        "hire_sales": ["hire sales reps", "grow sales team", "expand sales headcount"],
        "use_contractors": ["use contractors", "bring in contractors", "short-term contractors"],
        "freeze_hiring": ["freeze hiring", "pause hiring", "hold headcount steady"],
    }
    weights = {
        "hire_engineers": {"backlog_size": 0.6, "delivery_pressure": 0.3, "cash_reserve_score": 0.2},
        "hire_ops": {"incident_rate": 0.6, "reliability_risk": 0.3},
        "hire_sales": {"sales_pipeline": 0.6, "cash_reserve_score": 0.2},
        "use_contractors": {"delivery_pressure": 0.5, "backlog_size": 0.3, "cash_reserve_score": -0.2},
        "freeze_hiring": {"cash_reserve_score": -0.6, "backlog_size": -0.2, "sales_pipeline": -0.2},
    }
    rubric = {
        "hire_engineers": ["increase delivery capacity", "clear backlog", "ship faster"],
        "hire_ops": ["stabilize systems", "reduce incidents", "protect uptime"],
        "hire_sales": ["expand pipeline", "grow revenue", "improve coverage"],
        "use_contractors": ["move quickly", "avoid long-term costs", "meet deadlines"],
        "freeze_hiring": ["control costs", "preserve runway", "avoid overextension"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "backlog_size": round(rng.uniform(0.1, 1.0), 3),
            "incident_rate": round(rng.uniform(0.1, 1.0), 3),
            "sales_pipeline": round(rng.uniform(0.1, 1.0), 3),
            "delivery_pressure": round(rng.uniform(0.1, 1.0), 3),
            "reliability_risk": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Hiring capacity is limited this quarter. Decide how to allocate headcount to best support the "
            "company's priorities."
        )

    return Template(
        name="staffing_allocation",
        category="resource_allocation",
        title="Staffing allocation decision",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_growth_tradeoff_template() -> Template:
    option_keys = ["aggressive_expansion", "measured_growth", "optimize_cash", "invest_reliability", "exit_market"]
    option_variants = {
        "aggressive_expansion": ["aggressive expansion", "rapid expansion", "scale aggressively"],
        "measured_growth": ["measured growth", "steady growth", "balanced expansion"],
        "optimize_cash": ["optimize cash", "preserve cash", "maximize runway"],
        "invest_reliability": ["invest in reliability", "stabilize operations", "improve resiliency"],
        "exit_market": ["exit the market", "wind down presence", "leave the segment"],
    }
    weights = {
        "aggressive_expansion": {"market_opportunity": 0.6, "investor_pressure": 0.4, "burn_rate": -0.3},
        "measured_growth": {"market_opportunity": 0.4, "cash_reserve_score": 0.2, "reliability_risk": 0.2},
        "optimize_cash": {"burn_rate": 0.6, "cash_reserve_score": -0.4},
        "invest_reliability": {"reliability_risk": 0.6, "customer_loyalty_score": 0.2},
        "exit_market": {"market_opportunity": -0.6, "cash_reserve_score": -0.3, "burn_rate": 0.4},
    }
    rubric = {
        "aggressive_expansion": ["capture market share", "accept higher burn", "move fast"],
        "measured_growth": ["balance growth and risk", "maintain optionality", "avoid overreach"],
        "optimize_cash": ["extend runway", "reduce burn", "protect downside"],
        "invest_reliability": ["sustain trust", "reduce risk", "support long-term stability"],
        "exit_market": ["avoid sunk costs", "refocus resources", "limit downside"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "market_opportunity": round(rng.uniform(0.1, 1.0), 3),
            "burn_rate": round(rng.uniform(0.1, 1.0), 3),
            "reliability_risk": round(rng.uniform(0.1, 1.0), 3),
            "investor_pressure": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "The market opportunity is changing rapidly, and leadership must decide how aggressively to "
            "grow versus protect stability."
        )

    return Template(
        name="growth_tradeoff",
        category="long_term_tradeoffs",
        title="Growth vs stability",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def build_innovation_tradeoff_template() -> Template:
    option_keys = ["launch_innovative", "stabilize_core", "split_team", "beta_release", "delay"]
    option_variants = {
        "launch_innovative": ["launch innovative product", "ship major innovation", "release breakthrough"],
        "stabilize_core": ["stabilize core", "focus on reliability", "harden the core product"],
        "split_team": ["split team", "dual-track execution", "two-track delivery"],
        "beta_release": ["beta release", "limited beta launch", "pilot release"],
        "delay": ["delay the launch", "postpone release", "wait for readiness"],
    }
    weights = {
        "launch_innovative": {"competitive_threat": 0.6, "roadmap_pressure": 0.4, "cash_reserve_score": 0.2},
        "stabilize_core": {"defect_rate": 0.6, "customer_expectations": 0.3, "reliability_risk": 0.2},
        "split_team": {"competitive_threat": 0.4, "defect_rate": 0.3, "cash_reserve_score": 0.2},
        "beta_release": {"competitive_threat": 0.4, "customer_expectations": -0.2, "roadmap_pressure": 0.3},
        "delay": {"defect_rate": 0.5, "cash_reserve_score": -0.3, "competitive_threat": -0.3},
    }
    rubric = {
        "launch_innovative": ["beat competition", "capture attention", "accept execution risk"],
        "stabilize_core": ["reduce defects", "protect customers", "build trust"],
        "split_team": ["balance innovation and stability", "parallel execution", "manage risk"],
        "beta_release": ["test demand", "limit exposure", "gather feedback"],
        "delay": ["avoid poor quality", "reduce risk", "wait for readiness"],
    }

    def context_builder(rng: random.Random) -> Dict[str, Any]:
        return {
            "competitive_threat": round(rng.uniform(0.1, 1.0), 3),
            "defect_rate": round(rng.uniform(0.1, 1.0), 3),
            "customer_expectations": round(rng.uniform(0.1, 1.0), 3),
            "roadmap_pressure": round(rng.uniform(0.1, 1.0), 3),
            "reliability_risk": round(rng.uniform(0.1, 1.0), 3),
        }

    def prompt_builder(context: Dict[str, Any]) -> str:
        return (
            "Engineering leadership is split between shipping a major innovation and improving reliability. "
            "Decide the best approach."
        )

    return Template(
        name="innovation_tradeoff",
        category="long_term_tradeoffs",
        title="Innovation vs reliability",
        option_keys=option_keys,
        option_variants=option_variants,
        weights=weights,
        rubric_map=rubric,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
    )


def generate_scenarios(
    root: Path,
    *,
    seed: int,
    counts: Dict[str, int],
    version: str,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    id_prefixes = {
        "strategy": "strat",
        "risk": "risk",
        "ethics": "eth",
        "resource_allocation": "res",
        "long_term_tradeoffs": "lt",
    }
    templates = {
        "strategy": [build_price_war_template(), build_market_entry_template()],
        "risk": [build_security_breach_template(), build_supply_chain_template()],
        "ethics": [build_ai_bias_template(), build_layoff_template()],
        "resource_allocation": [build_budget_allocation_template(), build_staffing_allocation_template()],
        "long_term_tradeoffs": [build_growth_tradeoff_template(), build_innovation_tradeoff_template()],
    }

    for category, total in counts.items():
        category_dir = root / "scenarios" / category
        category_dir.mkdir(parents=True, exist_ok=True)
        for path in category_dir.glob("*.json"):
            path.unlink()
        per_template = total // len(templates[category])
        remainder = total % len(templates[category])
        scenario_index = 1
        width = max(3, len(str(total)))

        for idx, template in enumerate(templates[category]):
            target_count = per_template + (1 if idx < remainder else 0)
            option_cycle = list(template.option_keys)
            for i in range(target_count):
                target_option = option_cycle[i % len(option_cycle)]
                context = build_base_context(rng)
                context.update(template.context_builder(rng))
                bias_context(context, template.weights[target_option], rng)

                expected, scores = score_options(template, context, rng)
                attempts = 0
                while expected != target_option and attempts < 8:
                    bias_context(context, template.weights[target_option], rng, strength=0.4)
                    expected, scores = score_options(template, context, rng)
                    attempts += 1

                options = []
                for key in template.option_keys:
                    options.append(rng.choice(template.option_variants[key]))

                expected_text = rng.choice(template.option_variants[expected])
                if expected_text not in options:
                    options[rng.randrange(len(options))] = expected_text

                sorted_scores = sorted(scores.values(), reverse=True)
                margin = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0])
                difficulty = difficulty_from_margin(margin)

                rubric = template.rubric_map.get(expected, [])
                id_prefix = id_prefixes[category]
                scenario_id = f"{id_prefix.upper()}_{scenario_index:0{width}d}"
                scenario = {
                    "scenario_id": scenario_id,
                    "category": category,
                    "difficulty": difficulty,
                    "title": template.title,
                    "prompt": template.prompt_builder(context),
                    "context": context,
                    "decision_options": options,
                    "expected_decision": expected_text,
                    "reasoning_rubric": rubric,
                    "evaluation": {"decision_weight": 0.55, "reasoning_weight": 0.45},
                }
                path = category_dir / f"{id_prefix}_{scenario_index:0{width}d}.json"
                path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
                scenario_index += 1

    index = {
        "version": version,
        "scenario_count": sum(counts.values()),
        "categories": counts,
    }
    (root / "benchmark_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ERA-Bench scenarios.")
    parser.add_argument("--root", default="era_benchmark", help="Benchmark root directory.")
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument("--total", type=int, default=None, help="Total scenarios across all categories.")
    parser.add_argument("--scale", type=float, default=None, help="Scale factor for default counts.")
    parser.add_argument("--counts-json", default=None, help="JSON file with category counts overrides.")
    parser.add_argument("--version", default="1.2", help="Benchmark version string.")
    args = parser.parse_args()

    base_counts = {
        "strategy": 80,
        "risk": 60,
        "ethics": 50,
        "resource_allocation": 60,
        "long_term_tradeoffs": 50,
    }
    counts = dict(base_counts)
    if args.counts_json:
        payload = json.loads(Path(args.counts_json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("counts-json must contain a JSON object of category counts.")
        counts = {str(k): int(v) for k, v in payload.items()}
    elif args.total is not None:
        total = int(args.total)
        base_total = sum(base_counts.values())
        counts = {}
        remaining = total
        categories = list(base_counts.keys())
        for idx, category in enumerate(categories):
            if idx == len(categories) - 1:
                counts[category] = remaining
            else:
                scaled = int(round(base_counts[category] / base_total * total))
                counts[category] = max(1, scaled)
                remaining -= counts[category]
    elif args.scale is not None:
        scale = float(args.scale)
        counts = {k: max(1, int(round(v * scale))) for k, v in base_counts.items()}

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "scenarios").mkdir(parents=True, exist_ok=True)
    generate_scenarios(root, seed=args.seed, counts=counts, version=args.version)


if __name__ == "__main__":
    main()
