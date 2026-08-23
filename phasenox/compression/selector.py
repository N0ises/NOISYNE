from __future__ import annotations

from phasenox.compression.compressor import compress


def select_context(
    question: str,
    documents: list,
) -> str:

    return compress(
        question,
        documents,
    )