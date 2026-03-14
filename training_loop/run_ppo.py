"""Run PPO training on the long-horizon decision environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from decision_env.environment import LongHorizonDecisionEnvironment
from decision_env.scenario_generator import ScenarioGenerator
from modules.rl import PPOConfig, PPOTrainer, PolicyNetwork, ValueNetwork


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PPO policy/value on ERA decision environment.")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--max-steps", type=int, default=24)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--lam", type=float, default=0.95)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--policy-lr", type=float, default=3e-4)
    parser.add_argument("--value-lr", type=float, default=1e-3)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--reward-scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/rl/ppo")
    parser.add_argument("--domain", default=None)
    args = parser.parse_args()

    env = LongHorizonDecisionEnvironment(
        generator=ScenarioGenerator(seed=args.seed),
        default_domain=args.domain,
        max_steps=args.max_steps,
    )
    action_space = ["launch_feature", "increase_marketing", "cut_price", "focus_profit"]

    feature_dim = 9
    policy = PolicyNetwork.initialize(
        num_actions=len(action_space),
        feature_dim=feature_dim,
        action_labels=action_space,
    )
    value = ValueNetwork.initialize(feature_dim=feature_dim)

    trainer = PPOTrainer(
        environment=env,
        policy=policy,
        value=value,
        action_space=action_space,
        config=PPOConfig(
            episodes=args.episodes,
            max_steps=args.max_steps,
            gamma=args.gamma,
            lam=args.lam,
            clip=args.clip,
            policy_lr=args.policy_lr,
            value_lr=args.value_lr,
            epochs=args.epochs,
            entropy_coef=args.entropy_coef,
            reward_scale=args.reward_scale,
        ),
        seed=args.seed,
    )
    metrics = trainer.train()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    policy.save(output_root / "policy.json")
    value.save(output_root / "value.json")
    (output_root / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_root / "config.json").write_text(
        json.dumps(
            {
                "episodes": args.episodes,
                "max_steps": args.max_steps,
                "gamma": args.gamma,
                "lam": args.lam,
                "clip": args.clip,
                "policy_lr": args.policy_lr,
                "value_lr": args.value_lr,
                "epochs": args.epochs,
                "entropy_coef": args.entropy_coef,
                "reward_scale": args.reward_scale,
                "seed": args.seed,
                "domain": args.domain,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote PPO artifacts to {output_root}")


if __name__ == "__main__":
    main()
