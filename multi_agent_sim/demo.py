"""Demo runner for the multi-agent simulation.
Run from the workspace root with Python to see a basic simulation using MockAgents or OllamaAgents if available.
"""
from .agents import OllamaAgent, MockAgent
from .orchestrator import Orchestrator
from .archetypes import USER_ARCHETYPES, PROGRAM_SYSTEM
from .logger import ConversationLogger
import os


def demo_with_mocks():
    user = MockAgent(lambda s, u: f"(user sim) I ask about {u.split()[:3]}", name="user_mock")
    program = MockAgent(lambda s, u: f"(program sim) answer to {u.split()[:3]}", name="program_mock")
    logger = ConversationLogger(path=os.path.join(os.getcwd(), "multi_agent_conversation.log"))
    orch = Orchestrator(user, program, logger=logger, max_turns=5)
    hist = orch.run(system_user=USER_ARCHETYPES['curious'], system_program=PROGRAM_SYSTEM)
    print("\nTranscript:\n", logger.get_transcript())


if __name__ == "__main__":
    demo_with_mocks()
