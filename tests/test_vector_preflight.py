from __future__ import annotations

from typing import Any

from phasenox.memory.vector.manager import VectorManager
from phasenox.memory.vector.models import VectorRecord
from phasenox.memory.vector.providers.chroma import ChromaProvider


class _FakeProvider(ChromaProvider):
    """Records provider calls without a real Chroma client."""

    def __init__(self) -> None:
        self.adds: list[dict[str, Any]] = []
        self.upserts: list[dict[str, Any]] = []

    def create_collection(self, name: str):
        return name

    def delete_collection(self, name: str) -> None:
        pass

    def get_collection(self, name: str):
        return name

    def add(self, collection, ids, embeddings, metadatas=None, documents=None):
        self.adds.append(
            {
                "collection": collection,
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas,
                "documents": documents,
            }
        )

    def upsert(self, collection, ids, embeddings=None, metadatas=None, documents=None):
        self.upserts.append(
            {
                "collection": collection,
                "ids": ids,
                "embeddings": embeddings,
                "metadatas": metadatas,
                "documents": documents,
            }
        )

    def update(self, collection, ids, embeddings=None, metadatas=None, documents=None):
        pass

    def delete(self, collection, ids):
        pass

    def query(self, collection, embedding, top_k=5):
        return []

    def count(self, collection):
        return 0


class _FakeDatabase:
    def __init__(self, provider):
        self.provider = provider

    def collection(self, name: str):
        from phasenox.memory.vector.collection import VectorCollection

        return VectorCollection(self.provider, name)


def test_vector_manager_add_uses_upsert_for_idempotency():
    provider = _FakeProvider()
    manager = VectorManager.__new__(VectorManager)
    manager.database = _FakeDatabase(provider)
    manager.collection = manager.database.collection("test")

    record = VectorRecord(
        id="rec-1",
        embedding=[0.1, 0.2, 0.3],
        metadata={"source": "x"},
        document="text",
    )

    manager.add(record)

    assert len(provider.adds) == 0
    assert len(provider.upserts) == 1
    assert provider.upserts[0]["ids"] == ["rec-1"]

    manager.add(record)
    assert len(provider.adds) == 0
    assert len(provider.upserts) == 2
