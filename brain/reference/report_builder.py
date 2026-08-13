from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import (
    EngineerDecision,
    ReferenceReport,
)

logger = logging.getLogger(__name__)


class ReferenceReportBuilder:

    def build_json(
        self,
        report: ReferenceReport,
    ) -> dict:

        return asdict(report)

    def save_json(
        self,
        report: ReferenceReport,
        output: str | Path,
    ) -> Path:

        output = Path(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = self._sanitize_nonfinite(self.build_json(report))

        with output.open(
            "w",
            encoding="utf-8",
        ) as fp:

            json.dump(
                data,
                fp,
                indent=4,
                ensure_ascii=False,
                allow_nan=False,
            )

        return output

    def _sanitize_nonfinite(
        self,
        data: Any,
    ) -> Any:

        if isinstance(data, float):
            if math.isfinite(data):
                return data
            logger.warning("Replacing non-finite float %r with None for JSON export.", data)
            return None

        if isinstance(data, list):
            return [self._sanitize_nonfinite(item) for item in data]

        if isinstance(data, dict):
            return {key: self._sanitize_nonfinite(value) for key, value in data.items()}

        return data

    def build_markdown(
        self,
        report: ReferenceReport,
    ) -> str:

        c = report.comparison

        lines: list[str] = []

        lines.append("# NØISYNE Reference Report")
        lines.append("")

        lines.append("## Overall")
        lines.append("")
        lines.append(f"- Similarity: **{c.similarity:.2f}%**")
        lines.append(f"- Confidence: **{c.confidence:.2f}**")
        lines.append("")
        lines.append(report.summary)
        lines.append("")

        lines.append("## Scores")
        lines.append("")
        lines.append("| Category | Score |")
        lines.append("|---|---:|")
        lines.append(f"| Frequency | {c.frequency_score:.2f} |")
        lines.append(f"| Dynamics | {c.dynamic_score:.2f} |")
        lines.append(f"| Stereo | {c.stereo_score:.2f} |")
        lines.append(f"| Loudness | {c.loudness_score:.2f} |")
        lines.append(f"| Transient | {c.transient_score:.2f} |")
        lines.append(f"| Phase | {c.phase_score:.2f} |")
        lines.append(f"| Tonal | {c.tonal_score:.2f} |")
        lines.append(f"| Semantic | {c.semantic_score:.2f} |")
        lines.append("")

        lines.append("## Frequency Bands")
        lines.append("")
        lines.append("| Band | Ref | Current | Δ dB | Severity |")
        lines.append("|---|---:|---:|---:|---|")

        for band in c.band_differences:

            lines.append(
                f"| {band.band} | "
                f"{band.reference_energy:.2f} | "
                f"{band.current_energy:.2f} | "
                f"{band.difference_db:.2f} | "
                f"{band.severity.value} |"
            )

        lines.append("")
        lines.append("## Engineer Decisions")
        lines.append("")

        for decision in c.engineer_decisions:

            lines.extend(self._decision_block(decision))

        lines.append("")
        lines.append("## Strengths")
        lines.append("")

        for item in report.strengths:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Weaknesses")
        lines.append("")

        for item in report.weaknesses:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Priorities")
        lines.append("")

        for item in report.priorities:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Next Actions")
        lines.append("")

        for item in report.next_actions:
            lines.append(f"- {item}")

        return "\n".join(lines)

    def save_markdown(
        self,
        report: ReferenceReport,
        output: str | Path,
    ) -> Path:

        output = Path(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            self.build_markdown(report),
            encoding="utf-8",
        )

        return output

    def _decision_block(
        self,
        decision: EngineerDecision,
    ) -> list[str]:

        lines = []

        lines.append(f"### {decision.title}")

        lines.append(f"- Category: {decision.category.value}")

        lines.append(f"- Severity: {decision.severity.value}")

        lines.append(f"- Confidence: {decision.confidence:.2f}")

        lines.append(f"- Description: {decision.description}")

        lines.append(f"- Recommendation: {decision.recommendation}")

        if decision.plugin:

            lines.append(f"- Plugin: {decision.plugin}")

        if decision.parameters:

            lines.append("")
            lines.append("Parameters:")

            for key, value in decision.parameters.items():

                lines.append(f"- {key}: {value}")

        lines.append("")

        return lines
