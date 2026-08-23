from phasenox.infrastructure.config import settings
from phasenox.runtime import ModelRuntime

# Model name is owned by configuration; resolved by ModelRepository.
MODEL_NAME = settings.models.bge_reranker.name


def get_reranker(runtime: ModelRuntime | None = None):
    # Lazy import avoids a Windows segfault when sentence_transformers is
    # loaded at module import time alongside chromadb's EmbeddingFunction.
    from sentence_transformers import CrossEncoder

    assets = (runtime or ModelRuntime.shared()).load(
        model_name=MODEL_NAME,
        model_cls=CrossEncoder,
        backend="sentence-transformers",
        trust_remote_code=settings.models.bge_reranker.trust_remote_code,
    )
    return assets.model


def rerank(
    query: str,
    documents: list,
    top_k: int = 5,
):

    if not documents:
        return []

    pairs = [(query, doc["text"]) for doc in documents]

    scores = get_reranker().predict(
        pairs,
        show_progress_bar=False,
    )

    for doc, score in zip(documents, scores):
        doc["rerank_score"] = float(score)

    documents.sort(
        key=lambda x: x["rerank_score"],
        reverse=True,
    )

    return documents[:top_k]
