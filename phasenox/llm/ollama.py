from __future__ import annotations

import requests

from phasenox.llm.base import BaseLLM


class OllamaLLM(BaseLLM):

    def __init__(
        self,
        model: str = "qwen3:8b",
        host: str = "http://localhost:11434",
    ):

        self.model = model
        self.host = host

    def generate(
        self,
        prompt: str,
    ) -> str:

        response = requests.post(

            f"{self.host}/api/generate",

            json={

                "model": self.model,

                "prompt": prompt,

                "stream": False,

            },

            timeout=600,

        )

        response.raise_for_status()

        return response.json()["response"]