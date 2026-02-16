"""Small CLI runner to demonstrate runtime components."""
from .predictive import PredictionEngine
from .consciousness import ConsciousnessThreshold
from .action_spiral import ActionSelection
from .dopamine import LearningSignal
from .memory import MemoryReplay
from .diagnostics import RuntimeObserver


def demo():
    engine = PredictionEngine(lambda s: {k: (v * 0.9 if isinstance(v, (int, float)) else v) for k, v in s.items()})
    thresh = ConsciousnessThreshold(threshold=0.5)
    selector = ActionSelection(habit_threshold=0.8)
    learner = LearningSignal(learning_rate=0.2)
    replay = MemoryReplay()
    obs = RuntimeObserver()

    state = {"value": 1.0, "noise": 0.1}
    pred = engine.predict(state)
    err = engine.update({"value": 1.2, "noise": 0.05})
    obs.trace_event("prediction_error", {"err": err})

    conscious = thresh.is_conscious(err, attention_bias=0.0)
    print("Conscious?:", conscious)

    actions = {
        "press": {"value": 0.5, "habit_strength": 0.1},
        "wait": {"value": 0.2, "habit_strength": 0.9},
    }
    act, mode = selector.select_action(actions)
    print("Selected:", act, mode)

    # reinforce chosen action
    learner_delta = learner.compute_delta(prediction_error=err, activity=1.0)
    print("Learner delta:", learner_delta)
    selector.reinforce_habit(actions, act, reward=0.5, lr=0.1)
    obs.record_habit(act, actions[act].get("habit_strength", 0.0))

    # simulate memory replay
    consolidated = replay.consolidate(["event1", "event2", "event3"])
    print("Consolidated:", consolidated)

    print("Diagnostics:", obs.summary())


if __name__ == "__main__":
    demo()
