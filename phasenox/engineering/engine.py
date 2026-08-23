from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phasenox.reference.models import ReferenceMetric


@dataclass(slots=True)
class EngineeringRecommendation:
    """Simple recommendation produced by the reference engineering engine."""

    text: str
    metric: str = ""
    severity: str = ""
    confidence: float = 0.0


@dataclass(slots=True)
class EngineeringResult:
    """Result produced by EngineeringEngine.process()."""

    recommendations: list[EngineeringRecommendation] = field(
        default_factory=list,
    )


class EngineeringEngine:
    """Turns reference metric deltas into plain engineering recommendations.

    This is a thin compatibility layer used by `phasenox.reference.service`.
    It lives in `phasenox.engineering` to keep the reference service's dependency
    direction stable while the full engineering rule engine continues to
    evolve under `phasenox.audio.engineer`.
    """

    def process(
        self,
        metrics: list[ReferenceMetric],
    ) -> EngineeringResult:

        recommendations: list[EngineeringRecommendation] = []

        for metric in metrics:
            if metric.passed:
                continue

            recommendations.append(
                EngineeringRecommendation(
                    text=(
                        f"{metric.name}: "
                        f"adjust by {abs(metric.difference):.2f} "
                        f"({'reduce' if metric.difference > 0 else 'increase'})."
                    ),
                    metric=metric.name,
                    severity=metric.severity.value,
                    confidence=0.90,
                )
            )

        return EngineeringResult(
            recommendations=recommendations,
        )
