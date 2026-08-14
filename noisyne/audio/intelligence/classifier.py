from __future__ import annotations

import numpy as np

from .models import (
    AudioSemanticResult,
    SemanticLabel,
)

from .prompts import (
    AUDIO_PROMPT_BANK,
)


class AudioSemanticClassifier:


    def __init__(
        self,
        embedding_model,
    ) -> None:

        self._embedding_model = embedding_model



    def _cosine_similarity(
        self,
        a,
        b,
    ) -> float:


        a = np.asarray(
            a,
            dtype=np.float32,
        )


        b = np.asarray(
            b,
            dtype=np.float32,
        )


        denominator = (
            np.linalg.norm(a)
            *
            np.linalg.norm(b)
        )


        if denominator == 0:

            return 0.0


        return float(
            np.dot(a, b)
            /
            denominator
        )



    def classify(
        self,
        embedding: list[float],
    ) -> AudioSemanticResult:


        category_scores = []


        for category, prompts in AUDIO_PROMPT_BANK.items():


            text_embeddings = (
                self._embedding_model.encode_text(
                    prompts
                )
            )


            scores = []


            for text_embedding in text_embeddings:


                score = (
                    self._cosine_similarity(
                        embedding,
                        text_embedding,
                    )
                )


                scores.append(
                    score
                )


            category_score = (
                sum(scores)
                /
                len(scores)
            )


            category_scores.append(

                SemanticLabel(

                    name=category,

                    confidence=category_score,

                )

            )


        category_scores.sort(
            key=lambda x: x.confidence,
            reverse=True,
        )


        top = category_scores[:5]


        return AudioSemanticResult(

            labels=top,

            embedding=embedding,

            confidence=(
                top[0].confidence
                if top
                else 0.0
            ),

        )