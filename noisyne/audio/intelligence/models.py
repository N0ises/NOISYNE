from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SemanticLabel:

    name: str

    confidence: float



@dataclass(slots=True)
class AudioSemanticResult:

    labels: list[SemanticLabel] = field(
        default_factory=list
    )

    embedding: list[float] | None = None

    confidence: float = 0.0


    def top_labels(
        self,
        limit: int = 5,
    ) -> list[SemanticLabel]:

        return sorted(
            self.labels,
            key=lambda x: x.confidence,
            reverse=True,
        )[:limit]