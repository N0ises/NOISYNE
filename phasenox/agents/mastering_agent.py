from phasenox.agents.audio_agent import AudioAgent
from phasenox.services import LLMService


SYSTEM_PROMPT = """
You are one of the world's best mastering engineers.

You ONLY answer mastering questions.

Answer clearly and professionally.

If the user asks something unrelated to mastering,
politely say that you only answer mastering questions.
"""


class MasteringAgent(AudioAgent):

    def __init__(self):

        super().__init__()

        self.name = "mastering"

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