from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from statistics import variance
from typing import Any

from phasenox.audio.analysis.analyzer import AudioAnalyzer
from phasenox.audio.io.loader import AudioLoader
from phasenox.audio.io.models import AudioData
from phasenox.engineering.engine import EngineeringEngine

from .comparator import ReferenceComparator
from .models import (
    ReferenceComparison,
    ReferenceIntent,
    ReferenceReport,
    SegmentDeviation,
    Severity,
)


class ReferenceService:
    """
    Reference Intelligence V1

    Workflow

    Reference Audio
            │
            ▼
       Audio Analysis

    Current Audio
            │
            ▼
       Audio Analysis

            ▼

      Metric Comparison

            ▼

    Engineering Decisions

            ▼

      Reference Report
    """

    def __init__(
        self,
        loader: AudioLoader | None = None,
        analyzer: AudioAnalyzer | None = None,
        engineering: EngineeringEngine | None = None,
        comparator: ReferenceComparator | None = None,
    ) -> None:

        self.loader = loader or AudioLoader()

        self.analyzer = analyzer or AudioAnalyzer()

        self.engineering = engineering or EngineeringEngine()

        self.comparator = comparator or ReferenceComparator()

    def compare_files(
        self,
        reference_audio: str | Path,
        current_audio: str | Path,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        reference = self.loader.load(reference_audio)

        current = self.loader.load(current_audio)

        return self.compare(
            reference,
            current,
            intent=intent,
            reference_paths=[str(reference_audio)],
        )

    def compare_files_multiple(
        self,
        reference_audio: Sequence[str | Path],
        current_audio: str | Path,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceReport:

        reference_paths = [str(path) for path in reference_audio]

        references = [self.loader.load(path) for path in reference_paths]

        current = self.loader.load(current_audio)

        return self.compare_multiple(
            references,
            current,
            intent=intent,
            reference_paths=reference_paths,
        )

    def compare_multiple(
        self,
        references: Sequence[AudioData],
        current: AudioData,
        *,
        intent: ReferenceIntent | None = None,
        reference_paths: list[str] | None = None,
    ) -> ReferenceReport:

        reference_paths = reference_paths or []

        reference_analyses = [self.analyzer.analyze(ref) for ref in references]

        current_analysis = self.analyzer.analyze(current)

        current_metrics = asdict(current_analysis)

        reference_similarities = self._per_reference_similarities(
            reference_analyses,
            current_analysis,
            reference_paths,
        )

        # Choose the reference most similar to the current mix as the primary
        # comparison target. Averaged/variance metrics are kept only for
        # informational reporting.
        if reference_analyses:
            primary_index = self._closest_reference_index(
                reference_similarities,
                reference_paths,
            )
            primary_reference = asdict(reference_analyses[primary_index])
        else:
            primary_reference = {}

        comparison = self._compare_metrics(
            reference=primary_reference,
            current=current_metrics,
            reference_paths=reference_paths,
            metric_variance=self._metric_variance(reference_analyses),
            current_audio=current,
        )

        comparison.reference_similarities = reference_similarities

        # Surface averaged metrics and variance in the report weaknesses for
        # informational purposes.
        averaged_metrics = self._average_analyses(reference_analyses)

        return self._build_report(
            comparison,
            intent=intent,
            averaged_metrics=averaged_metrics,
        )

    def _closest_reference_index(
        self,
        reference_similarities: dict[str, float],
        reference_paths: list[str],
    ) -> int:

        if not reference_paths:
            return 0

        best_path = max(
            reference_paths,
            key=lambda path: reference_similarities.get(path, -1.0),
        )

        return reference_paths.index(best_path)

    def compare(
        self,
        reference: AudioData,
        current: AudioData,
        *,
        intent: ReferenceIntent | None = None,
        reference_paths: list[str] | None = None,
    ) -> ReferenceReport:

        reference_analysis = self.analyzer.analyze(reference)

        current_analysis = self.analyzer.analyze(current)

        paths = reference_paths or []

        comparison = self._compare_metrics(
            reference=asdict(reference_analysis),
            current=asdict(current_analysis),
            reference_paths=paths,
            metric_variance={},
            current_audio=current,
        )

        if paths:
            reference_comparison = self.comparator.compare_metrics(
                asdict(reference_analysis),
                asdict(current_analysis),
            )
            comparison.reference_similarities = {paths[0]: reference_comparison.similarity}

        return self._build_report(
            comparison,
            intent=intent,
            averaged_metrics=None,
        )

    def _compare_metrics(
        self,
        reference: dict,
        current: dict,
        *,
        reference_paths: list[str],
        metric_variance: dict[str, float],
        current_audio: AudioData,
    ) -> ReferenceComparison:

        comparison = self.comparator.compare_metrics(
            reference,
            current,
        )

        comparison.references = reference_paths
        comparison.metric_variance = metric_variance
        comparison.segment_deviations = self._build_segment_deviations(
            comparison,
            current_audio,
        )

        return comparison

    def _build_segment_deviations(
        self,
        comparison: ReferenceComparison,
        current_audio: AudioData,
    ) -> list[SegmentDeviation]:

        duration = current_audio.metadata.duration

        deviations: list[SegmentDeviation] = []

        for metric in comparison.metrics:

            if metric.passed:
                continue

            deviations.append(
                SegmentDeviation(
                    start_time=0.0,
                    end_time=duration,
                    metric=metric.name,
                    reference_value=metric.reference,
                    current_value=metric.current,
                    severity=Severity(self.comparator._severity(metric.difference)).value,
                )
            )

        return deviations

    def _build_report(
        self,
        comparison: ReferenceComparison,
        intent: ReferenceIntent | None,
        averaged_metrics: dict | None = None,
    ) -> ReferenceReport:

        engineering_result = self.engineering.process(comparison.metrics)

        summary = self._build_summary(comparison.similarity)

        strengths: list[str] = []

        weaknesses: list[str] = []

        priorities: list[str] = []

        next_actions: list[str] = []

        for decision in comparison.engineer_decisions:

            priorities.append(decision.title)

            next_actions.append(decision.recommendation)

        if comparison.similarity >= 90:

            strengths.append("Reference quality is very close.")

        elif comparison.similarity >= 75:

            strengths.append("Overall mix balance is acceptable.")

            weaknesses.append("Fine tuning recommended.")

        else:

            weaknesses.append("Major engineering differences detected.")

        if comparison.reference_similarities:

            for path, similarity in comparison.reference_similarities.items():

                strengths.append(f"Reference {Path(path).name} " f"similarity: {similarity:.2f}%.")

        if hasattr(
            engineering_result,
            "recommendations",
        ):

            for recommendation in engineering_result.recommendations:

                text = getattr(
                    recommendation,
                    "text",
                    None,
                )

                if text:

                    next_actions.append(text)

        if averaged_metrics:
            weaknesses.append(
                f"Averaged reference LUFS: {averaged_metrics.get('lufs', 0.0):.2f}."
            )

        if comparison.metric_variance:
            high_variance = sorted(
                comparison.metric_variance.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]

            for name, value in high_variance:
                weaknesses.append(
                    f"Reference variance for {name}: {value:.4f}."
                )

        return ReferenceReport(
            comparison=comparison,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            priorities=priorities,
            next_actions=next_actions,
            intent=intent,
        )

    def _build_summary(
        self,
        similarity: float,
    ) -> str:

        if similarity >= 95:

            return "Reference match is excellent."

        if similarity >= 90:

            return "Reference match is very good."

        if similarity >= 80:

            return "Reference match is good with minor improvements required."

        if similarity >= 70:

            return "Reference match is moderate. Engineering adjustments are recommended."

        return "Reference differs significantly from the target mix."

    def _average_analyses(
        self,
        analyses: Sequence,
    ) -> dict:

        if not analyses:
            return {}

        numeric_sums: dict[str, float] = defaultdict(float)
        numeric_counts: dict[str, int] = defaultdict(int)

        for analysis in analyses:

            for key, value in asdict(analysis).items():

                if isinstance(value, (int, float)):

                    numeric_sums[key] += float(value)
                    numeric_counts[key] += 1

        averaged: dict[str, Any] = asdict(analyses[0]).copy()

        for key, total in numeric_sums.items():

            count = numeric_counts[key]

            averaged[key] = total / count if count else 0.0

        return averaged

    def _metric_variance(
        self,
        analyses: Sequence,
    ) -> dict[str, float]:

        values_by_key: dict[str, list[float]] = defaultdict(list)

        for analysis in analyses:

            for key, value in asdict(analysis).items():

                if isinstance(value, (int, float)):

                    values_by_key[key].append(float(value))

        return {key: variance(values) for key, values in values_by_key.items() if len(values) >= 2}

    def _per_reference_similarities(
        self,
        reference_analyses: Sequence,
        current_analysis,
        reference_paths: list[str],
    ) -> dict[str, float]:

        similarities: dict[str, float] = {}

        current_metrics = asdict(current_analysis)

        for path, ref_analysis in zip(
            reference_paths,
            reference_analyses,
        ):

            comparison = self.comparator.compare_metrics(
                asdict(ref_analysis),
                current_metrics,
            )

            similarities[path] = comparison.similarity

        return similarities
