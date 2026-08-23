from __future__ import annotations

from .base import BaseVectorProvider


class VectorCollection:

    def __init__(
        self,
        provider: BaseVectorProvider,
        name: str,
    ):
        self.provider = provider
        self.name = name

        self.provider.create_collection(name)

    def count(self):
        return self.provider.count(self.name)

    def delete(
        self,
        ids: list[str],
    ):
        self.provider.delete(
            self.name,
            ids,
        )