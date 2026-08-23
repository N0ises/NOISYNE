from phasenox.agents.audio_agent import AudioAgent
from phasenox.services import LLMService


SYSTEM_PROMPT = """
You are SoundBrain.

You are an expert audio engineer.

You answer general audio engineering questions.

Always answer clearly and professionally.
"""


class AssistantAgent(AudioAgent):

    def __init__(self):

        super().__init__()

        self.name = "assistant"

        self.llm = LLMService()

    def run(
        self,
        question: str,
    ) -> str:

        prompt = f"""
{SYSTEM_PROMPT}

User Question:

{question}
"""

        return self.llm.ask(prompt)