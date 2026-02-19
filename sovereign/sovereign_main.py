import time
import threading
import random
import json
import os
from datetime import datetime

from hse.population_manager import PopulationManager
from hse.crisis_injector import CrisisInjector
from hse.analytics_server import start_server
from hse.personality_drift import PersonalityDrift
from hse.human_profile import SyntheticHuman, build_user_prompt
from ml.ml_orchestrator import MLWisdomOrchestrator

import subprocess


def call_model(model, prompt):
    # Dry-run safe wrapper; if Ollama not available this will error naturally
    proc = subprocess.Popen(["ollama", "run", model], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = proc.communicate(prompt)
    return (out or "").strip()


USER_MODEL = "deepseek-r1:8b"
PROGRAM_MODEL = "qwen3:14b"

# build managers
pop = PopulationManager()
humans = pop.create(n=3)
crisis = CrisisInjector(seed=123, base_rate=0.07)
ml_system = MLWisdomOrchestrator()
drift_engine = PersonalityDrift(seed=7)

feature_coverage = {f: 0 for f in [
    "Quick mode decision",
    "War mode confrontation",
    "Meeting structured planning",
    "DARBAR multi-perspective synthesis",
    "Risk analysis",
    "Long-term projection",
    "Behavioral correction",
    "Emotional stabilization",
    "Strategic reframing"
]} 

total_turns = 0
recent_crises = []

os.makedirs("logs", exist_ok=True)

# start analytics server in background
server_thread = threading.Thread(target=start_server, kwargs={"port":5006}, daemon=True)
server_thread.start()


def run_instance(hid):
    global total_turns
    human = pop.get(hid)
    turn = 0
    while True:
        turn += 1
        total_turns += 1

        # maybe inject crisis
        ev = crisis.maybe_inject(hid, human.__dict__, turn)
        if ev:
            recent_crises.append(ev)
            signals = {"stress": ev["crisis"]["severity"]}
        else:
            signals = {"stress": 0.0}

        # build user prompt
        unused = {k:v for k,v in feature_coverage.items()}
        user_prompt = build_user_prompt(human, domain=random.choice(["career","health","wealth"]), coverage=unused)
        try:
            user_msg = call_model(USER_MODEL, user_prompt)
        except Exception:
            user_msg = "[DRY_USER] simulated"

        # program prompt
        program_prompt = f"Mode: RANDOM\nHuman: {human.name}\nConversation: {user_msg}\n"
        try:
            program_msg = call_model(PROGRAM_MODEL, program_prompt)
        except Exception:
            program_msg = "[DRY_PROGRAM] simulated"

        # ML evaluation
        ml_result = ml_system.process_interaction(mode="RANDOM", user_input=user_msg, program_output=program_msg)

        # update coverage heuristically
        used_feature = ml_result.get("used_feature")
        if not used_feature:
            lm = program_msg.lower()
            if "attack" in lm or "fight" in lm:
                used_feature = "War mode confrontation"
            elif "agenda" in lm or "meeting" in lm:
                used_feature = "Meeting structured planning"
            elif "minister" in lm or "darbar" in lm:
                used_feature = "DARBAR multi-perspective synthesis"
            else:
                used_feature = "Quick mode decision"

        if used_feature in feature_coverage:
            feature_coverage[used_feature] += 1

        # apply personality drift
        signals["success_rate"] = ml_result.get("reward", {}).get("value", 0.5) if isinstance(ml_result.get("reward"), dict) else 0.5
        signals["repetition"] = human.repetition
        drift_record = drift_engine.apply(human.__dict__, signals)

        # persistence and logging
        with open(f"logs/{hid}.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.utcnow().isoformat()+"Z",
                "turn": turn,
                "user": user_msg,
                "program": program_msg,
                "ml": ml_result,
                "drift": drift_record,
                "crisis": ev
            }) + "\n")

        # occasionally save metrics
        if total_turns % 2 == 0:
            metrics = {
                "instances": len(pop.list_ids()),
                "total_turns": total_turns,
                "feature_coverage": feature_coverage,
                "recent_crises": recent_crises[-20:]
            }
            with open("live_metrics.json", "w", encoding="utf-8") as mf:
                mf.write(json.dumps(metrics))

        time.sleep(1.0)


if __name__ == "__main__":
    # spawn threads for each human
    threads = []
    for hid in pop.list_ids():
        t = threading.Thread(target=run_instance, args=(hid,), daemon=True)
        t.start()
        threads.append(t)

    print("Running population. Press CTRL+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all instances.")
