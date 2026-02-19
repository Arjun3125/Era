# persona/ollama_runtime.py
"""
OllamaRuntime — runtime wrapper including the boot-time availability handshake.

Handshakes implemented:
- Boot-time ollama.list() availability check (hard fail unless SKIP_OLLAMA_CHECK=1)
- analyze() and speak() functions (use configured models)
- Deterministic sampling via temperature=0, top_p=1.0, and global seed control for reproducibility
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
import ollama

# Thread pool for async analyze/speak
executor = ThreadPoolExecutor(max_workers=4)


class OllamaRuntime:
    def __init__(self, speak_model=None, analyze_model=None, global_seed=None):
        default_speak_model = os.getenv("USER_MODEL", "llama3.1:8b-instruct-q4_0")
        default_analyze_model = os.getenv("PROGRAM_MODEL", "huihui_ai/deepseek-r1-abliterated:8b")

        # Allow explicit args to override env; treat empty strings as "not provided".
        self.speak_model = speak_model or default_speak_model
        self.analyze_model = analyze_model or default_analyze_model
        self.global_seed = global_seed or os.getenv("EVAL_SEED", None)
        self.messages = []
        self.max_pairs = 10  # keep last N user/assistant pairs

        # EVALUATION MODE: Lock temperature for reproducibility
        self.eval_temperature = 0.0
        self.eval_top_p = 1.0
        
        # Boot-time handshake: verify Ollama daemon reachable.
        # Honor environment override SKIP_OLLAMA_CHECK to allow development without daemon.
        skip_check = os.getenv("SKIP_OLLAMA_CHECK", "").lower() in {"1", "true", "yes"}
        if not skip_check:
            try:
                # raise on failure to ensure hard fail at startup
                ollama.list()
            except Exception as e:
                # Fail hard (consistent with spec). Caller may catch.
                print("FATAL: Ollama not reachable:", e)
                # Use SystemExit for hard exit semantics similar to original script.
                raise SystemExit(1)

    def analyze(self, system_prompt, user_prompt):
        """
        Silent analysis handshake — expected to return free-form text (usually JSON).
        
        EVALUATION MODE: Uses temperature=0, top_p=1.0 for deterministic sampling
        when global_seed is set (reproducible results across 5 seeds).
        """
        try:
            # Build call options - deterministic if in evaluation mode
            options = {
                "temperature": self.eval_temperature,
                "top_p": self.eval_top_p,
            }
            
            # Inject seed if available
            if self.global_seed is not None:
                options["seed"] = int(self.global_seed)
            
            response = ollama.chat(
                model=self.analyze_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options=options,
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[LLM analyze error: {e}]"

    def analyze_async(self, system_prompt, user_prompt):
        """Return a Future wrapping analyze() so callers can run it in the threadpool."""
        return executor.submit(self.analyze, system_prompt, user_prompt)

    def speak(self, system_context, user_input):
        """
        Primary speak handshake — user-visible. Blocking.
        Maintains conversation history and trims it.
        
        EVALUATION MODE: Uses temperature=0, top_p=1.0 for deterministic sampling
        when global_seed is set (reproducible results across 5 seeds).
        """
        # Ensure single system context
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = system_context
        else:
            self.messages.insert(0, {"role": "system", "content": system_context})
        # append new user message
        self.messages.append({"role": "user", "content": user_input})

        # trim history to preserve system + last N pairs
        max_msgs = 1 + (self.max_pairs * 2)
        if len(self.messages) > max_msgs:
            tail = self.messages[-(max_msgs - 1):]
            self.messages = [self.messages[0]] + tail

        try:
            # Build call options - deterministic if in evaluation mode
            options = {
                "temperature": self.eval_temperature,
                "top_p": self.eval_top_p,
            }
            
            # Inject seed if available
            if self.global_seed is not None:
                options["seed"] = int(self.global_seed)
            
            response = ollama.chat(
                model=self.speak_model,
                messages=self.messages,
                options=options,
            )
            assistant_text = response["message"]["content"]
        except Exception as e:
            assistant_text = f"[LLM speak error: {e}]"

        # append assistant response and trim again if needed
        self.messages.append({"role": "assistant", "content": assistant_text})
        if len(self.messages) > max_msgs:
            tail = self.messages[-(max_msgs - 1):]
            self.messages = [self.messages[0]] + tail

        return assistant_text

    def speak_async(self, system_context, user_input):
        """Return a Future wrapping speak() so callers can run it in the threadpool."""
        return executor.submit(self.speak, system_context, user_input)
