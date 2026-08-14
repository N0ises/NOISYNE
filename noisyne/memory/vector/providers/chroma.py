from __future__ import annotations

import chromadb
from chromadb.config import Settings

from noisyne.memory.vector.base import BaseVectorProvider
from noisyne.memory.vector.config import PERSIST_DIRECTORY


class ChromaProvider(BaseVectorProvider):
    """
    ChromaDB Vector Provider.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=PERSIST_DIRECTORY,
            settings=Settings(anonymized_telemetry=False),
        )

    def create_collection(self, name: str):
        return self.client.get_or_create_collection(name)

    def delete_collection(self, name: str):
        self.client.delete_collection(name)

    def get_collection(self, name: str):
        return self.client.get_collection(name)

    def add(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas=None,
        documents=None,
    ):
        col = self.get_collection(collection)

        col.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def upsert(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas=None,
        documents=None,
    ):
        col = self.get_collection(collection)

        col.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def update(
        self,
        collection: str,
        ids: list[str],
        embeddings=None,
        metadatas=None,
        documents=None,
    ):
        col = self.get_collection(collection)

        col.update(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    def delete(
        self,
        collection: str,
        ids: list[str],
    ):
        col = self.get_collection(collection)

        col.delete(ids=ids)

    def query(
        self,
        collection: str,
        embedding: list[float],
        top_k: int = 5,
    ):
        col = self.get_collection(collection)

        return col.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )

    def count(self, collection: str):
        return self.get_collection(collection).count()