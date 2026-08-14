from __future__ import annotations

from abc import abstractmethod

from noisyne.infrastructure.providers.base import Provider


class LLMProvider(Provider):

    @abstractmethod
    def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Generate a completion.
        """