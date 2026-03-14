from __future__ import annotations

import numpy as np

from decision_env.environment import LongHorizonDecisionEnvironment
from modules.rl.advantage import compute_advantages, compute_returns
from modules.rl.policy_network import PolicyNetwork
from modules.rl.ppo_trainer import PPOConfig, PPOTrainer, featurize_long_state
from modules.rl.trajectory_buffer import TrajectoryBuffer
from modules.rl.value_network import ValueNetwork


def test_advantage_and_returns_lengths() -> None:
    rewards = [1.0, 0.5]
    values = [0.2, 0.1]
    dones = [False, True]
    advantages = compute_advantages(rewards, values, dones, gamma=0.9, lam=0.95)
    returns = compute_returns(values, advantages)
    assert len(advantages) == 2
    assert len(returns) == 2


def test_trajectory_buffer_add_clear_as_arrays() -> None:
    buffer = TrajectoryBuffer()
    buffer.add(np.array([0.1, 0.2]), 1, 0.5, -0.2, 0.1, False)
    buffer.add(np.array([0.3, 0.4]), 0, -0.1, -0.7, -0.2, True)
    arrays = buffer.as_arrays()
    assert arrays["states"].shape == (2, 2)
    assert arrays["actions"].tolist() == [1, 0]
    assert arrays["dones"].tolist() == [False, True]

    buffer.clear()
    arrays = buffer.as_arrays()
    assert arrays["states"].shape == (0,)


def test_policy_network_probs_and_update() -> None:
    policy = PolicyNetwork.initialize(num_actions=2, feature_dim=3, action_labels=["a", "b"])
    features = np.array([0.1, 0.2, 0.3], dtype=float)
    probs = policy.action_probs(features)
    assert probs.shape == (2,)
    assert np.isclose(probs.sum(), 1.0)

    rng = np.random.default_rng(0)
    action, logp, _ = policy.sample_action(features, rng)
    assert action in (0, 1)
    assert np.isfinite(logp)

    states = np.vstack([features, features * 1.1])
    actions = np.array([action, action], dtype=int)
    old_log_probs = np.array([logp, logp], dtype=float)
    advantages = np.array([0.5, -0.2], dtype=float)
    loss = policy.update_ppo(
        states,
        actions,
        old_log_probs,
        advantages,
        clip=0.2,
        lr=0.1,
        entropy_coef=0.01,
    )
    assert np.isfinite(loss)
    assert not np.allclose(policy.weights, 0.0)


def test_value_network_update_changes_weights() -> None:
    value = ValueNetwork.initialize(feature_dim=3)
    states = np.array([[0.2, 0.1, 0.0], [0.4, 0.1, 0.2]], dtype=float)
    returns = np.array([0.5, 0.2], dtype=float)
    before = value.weights.copy()
    mse = value.update(states, returns, lr=0.1)
    assert np.isfinite(mse)
    assert not np.allclose(before, value.weights)


def test_ppo_trainer_smoke() -> None:
    env = LongHorizonDecisionEnvironment(max_steps=2)
    state = env.reset()
    feature_dim = len(featurize_long_state(state))
    policy = PolicyNetwork.initialize(num_actions=3, feature_dim=feature_dim, action_labels=["a", "b", "c"])
    value = ValueNetwork.initialize(feature_dim=feature_dim)
    config = PPOConfig(episodes=1, max_steps=2, epochs=1)
    trainer = PPOTrainer(
        environment=env,
        policy=policy,
        value=value,
        action_space=["a", "b", "c"],
        config=config,
        seed=1,
    )
    metrics = trainer.train()
    assert len(metrics) == 1
    assert {"episode", "total_reward", "policy_loss", "value_loss"} <= set(metrics[0].keys())
