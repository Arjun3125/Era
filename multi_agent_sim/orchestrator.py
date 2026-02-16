"""
orchestrator.py
Implements the turn-based orchestrator that mediates between two agents.
Provides safety: agents never see each other directly; orchestrator controls prompts, memory injection, logging, and termination.
"""
from typing import Any, Dict, List, Optional
from .agents import BaseAgent
from .logger import ConversationLogger


class Orchestrator:
    def __init__(self, user_agent: BaseAgent, program_agent: BaseAgent, logger: Optional[ConversationLogger] = None, max_turns: int = 20):
        self.user = user_agent
        self.program = program_agent
        self.logger = logger or ConversationLogger()
        self.max_turns = int(max_turns)
        self.history: List[Dict[str, str]] = []

    def _build_program_prompt(self, system_prompt: str) -> str:
        # Build conversation so far as seen by program
        convo = "\n".join([f"{r}: {m}" for r, m in [(h['role'], h['msg']) for h in self.history]])
        return system_prompt + "\nConversation so far:\n" + convo + "\nRespond:" if convo else system_prompt + "\nRespond:"

    def _build_user_prompt(self, system_prompt: str) -> str:
        convo = "\n".join([f"{r}: {m}" for r, m in [(h['role'], h['msg']) for h in self.history]])
        return system_prompt + "\nConversation so far:\n" + convo + "\nContinue as the user:" if convo else system_prompt + "\nStart interacting with the system:"

    def run(self, system_user: str, system_program: str, initial_user_prompt: Optional[str] = None, stop_condition: Optional[callable] = None):
        user_prompt = initial_user_prompt or system_user + "\nStart interacting with the system."

        for turn in range(self.max_turns):
            # User turn
            user_msg = self.user.respond(system_user, user_prompt)
            self.history.append({"role": "USER", "msg": user_msg})
            self.logger.append("USER", user_msg)
            print(f"\n--- TURN {turn+1} ---")
            print("USER:", user_msg)

            # Program turn
            program_prompt = self._build_program_prompt(system_program)
            program_msg = self.program.respond(system_program, program_prompt)
            self.history.append({"role": "PROGRAM", "msg": program_msg})
            self.logger.append("PROGRAM", program_msg)
            print("PROGRAM:", program_msg)

            # Prepare next user prompt
            user_prompt = self._build_user_prompt(system_user)

            # Optional stop condition (inspect last two messages)
            if stop_condition and stop_condition(self.history):
                print("Stop condition met. Terminating simulation.")
                break

        return self.history
