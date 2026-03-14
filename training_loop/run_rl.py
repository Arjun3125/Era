"""Standalone RL training loop over the multi-step decision environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from decision_env import MultiStepDecisionEnvironment, ScenarioGenerator
from training_loop.rl.features import build_feature_spec
from training_loop.rl.trainer import RLConfig, RLTrainer, initialize_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RL training over the decision environment.")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--lr-policy", type=float, default=0.05)
    parser.add_argument("--lr-value", type=float, default=0.1)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/rl")
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()

    env = MultiStepDecisionEnvironment(
        generator=ScenarioGenerator(seed=args.seed),
        default_domain=args.domain,
        max_steps=args.max_steps,
    )
    scenario = env.reset(domain=args.domain)
    action_labels: List[str] = [option.label for option in scenario.options]
    feature_spec = build_feature_spec(max_steps=args.max_steps)

    agent = initialize_agent(
        feature_spec=feature_spec,
        action_labels=action_labels,
        seed=args.seed,
    )
    trainer = RLTrainer(
        environment=env,
        agent=agent,
        config=RLConfig(
            episodes=args.episodes,
            gamma=args.gamma,
            lr_policy=args.lr_policy,
            lr_value=args.lr_value,
            temperature=args.temperature,
            max_steps=args.max_steps,
            entropy_coef=args.entropy_coef,
        ),
    )
    metrics = trainer.train()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    agent.policy.save(output_root / "policy_model.json")
    agent.value.save(output_root / "value_model.json")
    (output_root / "training_metrics.json").write_text(
        json.dumps([item.as_dict() for item in metrics], indent=2),
        encoding="utf-8",
    )
    (output_root / "config.json").write_text(
        json.dumps(
            {
                "episodes": args.episodes,
                "max_steps": args.max_steps,
                "gamma": args.gamma,
                "lr_policy": args.lr_policy,
                "lr_value": args.lr_value,
                "temperature": args.temperature,
                "seed": args.seed,
                "domain": args.domain,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote RL artifacts to {output_root}")


if __name__ == "__main__":
    main()
