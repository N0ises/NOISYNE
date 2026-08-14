from __future__ import annotations


class CollectionNames:
    """
    Centralized vector collection naming.
    """

    @staticmethod
    def audio(
        model: str,
        dimension: int,
    ) -> str:

        model = model.replace("/", "_")

        return f"audio_{model}_{dimension}"

    @staticmethod
    def text(
        model: str,
        dimension: int,
    ) -> str:

        model = model.replace("/", "_")

        return f"text_{model}_{dimension}"