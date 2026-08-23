from __future__ import annotations

from .collection import VectorCollection
from .factory import VectorFactory


class VectorDatabase:

    def __init__(
        self,
        provider: str | None = None,
    ):
        self.provider = VectorFactory.create(provider)

    def collection(
        self,
        name: str,
    ) -> VectorCollection:

        return VectorCollection(
            self.provider,
            name,
        )