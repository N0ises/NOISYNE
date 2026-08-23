from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ReportSection:

    title: str

    status: str

    description: str

    recommendation: str | None = None


@dataclass(slots=True)
class ComparisonReport:

    overall_score: float

    summary: str

    strengths: list[ReportSection] = field(default_factory=list)

    warnings: list[ReportSection] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)