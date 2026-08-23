from __future__ import annotations

from dataclasses import dataclass

from .base import AudioEmbeddingModel
from .models import EmbeddingCapability


@dataclass(slots=True)
class RegisteredEmbedding:

    capability: EmbeddingCapability

    provider: AudioEmbeddingModel


class EmbeddingRegistry:

    def __init__(self):

        self._providers: dict[
            str,
            RegisteredEmbedding,
        ] = {}

    def register(

        self,

        capability: EmbeddingCapability,

        provider: AudioEmbeddingModel,

    ) -> None:

        self._providers[
            capability.name
        ] = RegisteredEmbedding(

            capability=capability,

            provider=provider,

        )

    def get(

        self,

        name: str,

    ) -> AudioEmbeddingModel:

        return self._providers[
            name
        ].provider

    def capability(

        self,

        name: str,

    ) -> EmbeddingCapability:

        return self._providers[
            name
        ].capability

    def supports(

        self,

        task: str,

    ) -> list[str]:

        return [

            item.capability.name

            for item in self._providers.values()

            if task in item.capability.tasks

        ]

    def names(self) -> list[str]:

        return sorted(

            self._providers.keys()

        )