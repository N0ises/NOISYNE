from __future__ import annotations


def score_from_distance(
    distance: float,
    *,
    metric: str = "cosine",
) -> float:
    """Convert a Chroma distance into a bounded similarity score.

    Chroma's ``hnsw:space`` metric determines the meaning of ``distance``:

    * ``cosine`` — distance is ``1 - cosine_similarity``. Score is therefore
      ``1 - distance``, clamped to ``[0.0, 1.0]``.

    Other metrics are not used by the current RAG pipeline. Calling this
    helper with an unsupported metric is a programming error and raises
    ``ValueError`` rather than silently producing a misleading score.
    """

    metric = metric.lower().strip()

    if metric == "cosine":
        score = 1.0 - float(distance)
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    raise ValueError(
        f"Unsupported distance metric for scoring: {metric!r}. "
        "RAG is configured for cosine distance with normalized embeddings."
    )
