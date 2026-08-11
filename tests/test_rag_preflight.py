from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import chromadb
import pytest
from chromadb.api.types import EmbeddingFunction

from brain.infrastructure.config import get_application_root
from brain.rag.ingestion import _chunk_id, _source_fingerprint, ingest_chunks
from brain.rag.scoring import score_from_distance
from brain.services.rag_service import RAGService


# ---------------------------------------------------------------------------
# Distance-to-score semantics
# ---------------------------------------------------------------------------


class _FixedEmbeddingFunction(EmbeddingFunction):
    """Return a deterministic, normalized embedding for a query string."""

    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        return [self._vector for _ in input]


def _norm(v: list[float]) -> list[float]:
    import math

    length = math.sqrt(sum(x * x for x in v))
    return [x / length for x in v]


def test_score_from_distance_cosine_boundary():
    assert score_from_distance(0.0, metric="cosine") == 1.0
    assert score_from_distance(0.5, metric="cosine") == 0.5
    assert score_from_distance(1.0, metric="cosine") == 0.0


def test_score_from_distance_clamps_out_of_range():
    assert score_from_distance(-0.1, metric="cosine") == 1.0
    assert score_from_distance(1.5, metric="cosine") == 0.0


def test_score_from_distance_rejects_unsupported_metric():
    with pytest.raises(ValueError):
        score_from_distance(0.5, metric="l2")


@pytest.fixture
def temp_rag_collection(tmp_path: Path):
    """Create a temporary Chroma collection configured for cosine distance."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    query_vector = _norm([1.0, 0.0, 0.0, 0.0])
    ef = _FixedEmbeddingFunction(query_vector)
    col = client.get_or_create_collection(
        name="test_rag",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    # Add three documents with known embeddings. The query vector is identical
    # to doc[0], orthogonal-ish to doc[2], and in between for doc[1].
    col.add(
        ids=["d0", "d1", "d2"],
        documents=["alpha", "beta", "gamma"],
        metadatas=[{"source": "s"}, {"source": "s"}, {"source": "s"}],
        embeddings=[
            query_vector,
            _norm([0.9, 0.1, 0.0, 0.0]),
            _norm([0.0, 1.0, 0.0, 0.0]),
        ],
    )
    return col


def test_retrieval_scores_are_valid_cosine_similarities(
    temp_rag_collection,
    monkeypatch,
):
    from brain.rag import retriever

    monkeypatch.setattr(retriever, "collection", temp_rag_collection)

    results = retriever.retrieve("query", k=3)

    scores = [r["score"] for r in results]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0, abs=1e-4)
    assert scores[1] > scores[2]


def test_chroma_collection_uses_cosine_distance(tmp_path: Path):
    """A fresh Chroma collection must advertise cosine distance."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_or_create_collection(
        name="cosine_test",
        metadata={"hnsw:space": "cosine"},
    )
    assert col.metadata.get("hnsw:space") == "cosine"


# ---------------------------------------------------------------------------
# Idempotent ingestion
# ---------------------------------------------------------------------------


class _FakeChromaCollection:
    """In-memory stand-in for a Chroma collection with metadata filtering."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def get(self, where: dict[str, Any] | None = None):
        ids = []
        for id_, record in self._records.items():
            if where is None or all(record["metadata"].get(k) == v for k, v in where.items()):
                ids.append(id_)
        return {"ids": [ids]}

    def delete(self, ids: list[str] | None = None) -> None:
        for id_ in ids or []:
            self._records.pop(id_, None)

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        for id_, doc, meta in zip(ids, documents, metadatas):
            self._records[id_] = {"document": doc, "metadata": meta}

    def count(self) -> int:
        return len(self._records)


class _Chunk:
    def __init__(self, text: str, metadata: dict[str, Any]) -> None:
        self.page_content = text
        self.metadata = metadata


def test_ingest_chunks_are_idempotent_across_re_ingestion():
    col = _FakeChromaCollection()
    chunks = [
        _Chunk("first chunk from A", {"source": "docA.pdf"}),
        _Chunk("second chunk from A", {"source": "docA.pdf"}),
        _Chunk("chunk from B", {"source": "docB.pdf"}),
    ]

    sources, total = ingest_chunks(col, chunks)
    assert sources == 2
    assert total == 3
    assert col.count() == 3

    # Re-ingest the same chunks. No duplicate ids should be created.
    sources, total = ingest_chunks(col, chunks)
    assert sources == 2
    assert total == 3
    assert col.count() == 3

    # Verify the deterministic ids are exactly what we expect. Each source
    # starts its own chunk index at zero.
    for idx in range(2):
        expected_id = _chunk_id("docA.pdf", idx)
        assert expected_id in col._records
    assert _chunk_id("docB.pdf", 0) in col._records


def test_ingest_chunks_replace_stale_chunks_for_source():
    col = _FakeChromaCollection()
    first = [
        _Chunk("old A1", {"source": "docA.pdf"}),
        _Chunk("old A2", {"source": "docA.pdf"}),
        _Chunk("B1", {"source": "docB.pdf"}),
    ]
    ingest_chunks(col, first)
    assert col.count() == 3

    second = [
        _Chunk("new A1", {"source": "docA.pdf"}),
        _Chunk("B1", {"source": "docB.pdf"}),
    ]
    ingest_chunks(col, second)
    assert col.count() == 2

    # Stale A chunks are gone; only the new A chunk and the updated B chunk remain.
    a_docs = [r["document"] for r in col._records.values() if r["metadata"]["source"] == "docA.pdf"]
    assert a_docs == ["new A1"]
    b_docs = [r["document"] for r in col._records.values() if r["metadata"]["source"] == "docB.pdf"]
    assert b_docs == ["B1"]


def test_chunk_id_is_deterministic():
    a = _chunk_id("source.pdf", 3)
    b = _chunk_id("source.pdf", 3)
    assert a == b
    assert a.startswith(_source_fingerprint("source.pdf"))


# ---------------------------------------------------------------------------
# Redundant retrieve/rerank
# ---------------------------------------------------------------------------


def test_ask_reuses_search_results_without_second_retrieval(monkeypatch):
    calls = []

    def fake_retrieve(query, k=10):
        calls.append(("retrieve", query, k))
        return [
            {
                "text": "result one",
                "source": "src.pdf",
                "page": 1,
                "score": 0.9,
            },
        ]

    def fake_rerank(query, documents, top_k):
        calls.append(("rerank", query, len(documents), top_k))
        return documents[:top_k]

    monkeypatch.setattr("brain.services.rag_service.retrieve", fake_retrieve)
    monkeypatch.setattr("brain.services.rag_service.rerank", fake_rerank)

    service = RAGService(retrieve_k=10, rerank_k=5)
    answer = service.ask("what is mixing?")

    retrieve_calls = [c for c in calls if c[0] == "retrieve"]
    rerank_calls = [c for c in calls if c[0] == "rerank"]
    assert len(retrieve_calls) == 1
    assert len(rerank_calls) == 1
    assert answer["count"] == 1
    assert answer["context"]


# ---------------------------------------------------------------------------
# CWD-independent persistence
# ---------------------------------------------------------------------------


def test_persistence_paths_are_absolute_and_cwd_independent():
    from brain.audio.catalog.database import DATABASE_PATH
    from brain.memory.vector.config import PERSIST_DIRECTORY

    root = get_application_root()
    assert Path(PERSIST_DIRECTORY).is_absolute()
    assert Path(PERSIST_DIRECTORY).is_relative_to(root)
    assert DATABASE_PATH.is_absolute()
    assert DATABASE_PATH.is_relative_to(root)


def test_persistence_paths_stable_from_different_cwd(tmp_path: Path):
    """Importing from a different cwd must resolve the same absolute paths."""
    script = """
import sys
from pathlib import Path
sys.path.insert(0, r"{root}")
from brain.infrastructure.config import get_application_root
from brain.memory.vector.config import PERSIST_DIRECTORY
from brain.audio.catalog.database import DATABASE_PATH
root = get_application_root()
print(PERSIST_DIRECTORY)
print(DATABASE_PATH)
print(Path(PERSIST_DIRECTORY).is_relative_to(root))
print(DATABASE_PATH.is_relative_to(root))
""".format(root=get_application_root())

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.strip().splitlines()
    persist_dir = Path(lines[0])
    catalog_path = Path(lines[1])
    assert persist_dir.is_absolute()
    assert catalog_path.is_absolute()
    assert lines[2] == "True"
    assert lines[3] == "True"
