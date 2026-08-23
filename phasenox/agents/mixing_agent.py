from phasenox.agents.audio_agent import AudioAgent
from phasenox.services import LLMService


SYSTEM_PROMPT = """
You are one of the world's best mixing engineers.

You ONLY answer audio mixing questions.

Answer clearly and professionally.

If the user asks something unrelated to mixing,
politely say that you only answer mixing questions.
"""


class MixingAgent(AudioAgent):

    def __init__(self):

        super().__init__()

        self.name = "mixing"

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