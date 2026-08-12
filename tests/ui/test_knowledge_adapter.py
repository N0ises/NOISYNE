from __future__ import annotations

from types import SimpleNamespace

import pytest

from brain.ui.adapters.v1 import V1ApplicationAdapter
from brain.ui.contracts import KnowledgeQuery


class FakeRagService:
    def __init__(self) -> None:
        self.query = None

    def search(self, query):
        self.query = query
        return [
            SimpleNamespace(
                text="Keep headroom before limiting.",
                source="mastering-guide.pdf",
                page=12,
                score=0.8123,
                rerank_score=-1.25,
            )
        ]


def test_v1_adapter_maps_rag_service_result_to_stable_dto(product_metadata) -> None:
    service = FakeRagService()
    adapter = V1ApplicationAdapter(
        metadata=product_metadata,
        rag_service_factory=lambda: service,
    )

    result = adapter.search_knowledge(KnowledgeQuery("  headroom  "))

    assert service.query == "headroom"
    assert result.query == "headroom"
    assert result.reasoning_context is None
    assert result.items[0].content == "Keep headroom before limiting."
    assert result.items[0].source == "mastering-guide.pdf"
    assert result.items[0].page == 12
    assert result.items[0].raw_score == 0.8123
    assert result.items[0].raw_rerank_score == -1.25


def test_v1_adapter_rejects_empty_query_before_service_call(product_metadata) -> None:
    service = FakeRagService()
    adapter = V1ApplicationAdapter(
        metadata=product_metadata,
        rag_service_factory=lambda: service,
    )

    with pytest.raises(ValueError):
        adapter.search_knowledge(KnowledgeQuery("  "))

    assert service.query is None
