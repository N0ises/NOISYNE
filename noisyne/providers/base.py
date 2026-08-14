from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from .models import GenerateRequest, GenerateResponse


class BaseAIProvider(ABC):
    """Abstract contract for all AI providers in SoundBrain."""

    name: ClassVar[str]

    def initialize(self) -> None:
        """Optional lifecycle hook for loading models or clients."""

    @abstractmethod
    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a text completion from the provider."""
        ...
