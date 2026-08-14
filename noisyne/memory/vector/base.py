from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseVectorProvider(ABC):
    """
    Base interface for every Vector Database provider.
    """

    @abstractmethod
    def create_collection(self, name: str) -> Any:
        ...

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        ...

    @abstractmethod
    def get_collection(self, name: str) -> Any:
        ...

    @abstractmethod
    def add(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        ...

    @abstractmethod
    def update(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        ...

    @abstractmethod
    def delete(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        ...

    @abstractmethod
    def query(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 5,
    ) -> Any:
        ...

    @abstractmethod
    def count(self, collection: str) -> int:
        ...