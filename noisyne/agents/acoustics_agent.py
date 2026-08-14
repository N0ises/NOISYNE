from noisyne.agents.audio_agent import AudioAgent
from noisyne.services import LLMService


SYSTEM_PROMPT = """
You are an acoustics expert.

You answer questions about acoustics and room treatment.

Always use the provided context.

If the answer is not in the context say:

I don't know based on my knowledge base.
"""


class AcousticsAgent(AudioAgent):

    def __init__(self):

        super().__init__()

        self.name = "acoustics"

        self.llm = LLMService()

    def run(
        self,
        question: str,
        context: str = "",
    ) -> str:

        prompt = f"""
{SYSTEM_PROMPT}

Context:

{context}

User Question:

{question}
"""

        return self.llm.ask(prompt)