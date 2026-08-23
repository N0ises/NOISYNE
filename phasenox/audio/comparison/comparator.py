from __future__ import annotations

from phasenox.audio.analysis.models import AnalysisResult

from .config import METRIC_RULES
from .models import (
    ComparisonResult,
    MetricDifference,
)


class AudioComparator:

    _FIELDS = [

        ("LUFS", "lufs"),

        ("Peak", "peak"),

        ("RMS", "rms"),

        ("Dynamic Range", "dynamic_range"),

        ("Crest Factor", "crest_factor"),

        ("Stereo Width", "stereo_width"),

        ("Phase", "phase"),

        ("Spectral Centroid", "spectral_centroid"),

        ("Spectral Bandwidth", "spectral_bandwidth"),

        ("Spectral Rolloff", "spectral_rolloff"),

        ("Spectral Flatness", "spectral_flatness"),

        ("Spectral Contrast", "spectral_contrast"),

        ("Zero Crossing Rate", "zero_crossing_rate"),

        ("Tempo", "tempo"),

    ]

    def _metric_score(
        self,
        field: str,
        difference: float,
    ) -> float:

        rule = METRIC_RULES.get(field)

        if rule is None:
            return 100.0

        if abs(difference) <= rule.tolerance:
            return 100.0

        overflow = abs(difference) - rule.tolerance

        penalty = (
            overflow
            / rule.tolerance
        ) * 100.0

        return max(
            0.0,
            100.0 - penalty,
        )

    def compare(
        self,
        reference: AnalysisResult,
        current: AnalysisResult,
    ) -> ComparisonResult:

        metrics = []

        weighted_score = 0.0

        total_weight = 0.0

        recommendations = []

        for title, field in self._FIELDS:

            ref = float(
                getattr(reference, field)
            )

            cur = float(
                getattr(current, field)
            )

            difference = cur - ref

            percent = 0.0

            if abs(ref) > 1e-9:

                percent = (
                    abs(difference)
                    / abs(ref)
                ) * 100.0

            metric = MetricDifference(

                name=title,

                reference=ref,

                current=cur,

                difference=difference,

                percent=percent,

            )

            metrics.append(metric)

            rule = METRIC_RULES.get(field)

            if rule is None:
                continue

            score = self._metric_score(
                field,
                difference,
            )

            weighted_score += (
                score
                * rule.weight
            )

            total_weight += rule.weight

        if total_weight == 0:

            overall = 100.0

        else:

            overall = (
                weighted_score
                / total_weight
            )

        #
        # Recommendations
        #

        if current.peak > reference.peak:

            recommendations.append(
                "Reduce output gain."
            )

        if current.lufs > reference.lufs + 1.0:

            recommendations.append(
                "Reduce integrated loudness."
            )

        if current.stereo_width < reference.stereo_width - 0.05:

            recommendations.append(
                "Increase stereo width."
            )

        if current.dynamic_range < reference.dynamic_range - 1.0:

            recommendations.append(
                "Increase dynamic range."
            )

        if current.phase < reference.phase - 0.10:

            recommendations.append(
                "Check mono compatibility."
            )

        return ComparisonResult(

            score=round(
                overall,
                2,
            ),

            metrics=metrics,

            recommendations=recommendations,

        )