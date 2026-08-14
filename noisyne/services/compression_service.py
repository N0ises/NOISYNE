from __future__ import annotations

from noisyne.compression.compressor import compress


class CompressionService:

    def compress(
        self,
        question: str,
        documents: list,
    ) -> str:

        return compress(
            question,
            documents,
        )