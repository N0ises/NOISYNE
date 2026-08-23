from __future__ import annotations

from openai import OpenAI

from phasenox.infrastructure.config import settings
from phasenox.llm.base import BaseLLM


class LMStudioLLM(BaseLLM):

    def __init__(self) -> None:

        config = settings.llm

        self.model = config.model

        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    @property
    def name(self) -> str:

        return "lmstudio"

    def initialize(self) -> None:

        pass

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        response = self.client.chat.completions.create(

            model=self.model,

            temperature=settings.llm.temperature,

            top_p=settings.llm.top_p,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return response.choices[0].message.content