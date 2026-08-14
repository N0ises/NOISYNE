from __future__ import annotations

from noisyne.compression.compressor import compress


def select_context(
    question: str,
    documents: list,
) -> str:

    return compress(
        question,
        documents,
    )