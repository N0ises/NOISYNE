from __future__ import annotations


def test_rag_imports_do_not_crash():
    """RAG modules import cleanly without loading any model."""
    from noisyne.rag.reranker import get_reranker, rerank
    from noisyne.rag.vectordb import get_collection
    from noisyne.rag.splitter import split_documents

    assert callable(get_reranker)
    assert callable(rerank)
    assert callable(get_collection)
    assert callable(split_documents)
