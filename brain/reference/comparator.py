from __future__ import annotations

from typing import Iterable

from .models import (
    BandDifference,
    Category,
    EngineerDecision,
    ReferenceComparison,
    ReferenceMetric,
    Severity,
)


class ReferenceComparator:

    BAND_LIMITS = (
        ("Sub", 20, 60),
        ("Bass", 60, 120),
        ("Low Mid", 120, 500),
        ("Mid", 500, 2000),
        ("High Mid", 2000, 6000),
        ("High", 6000, 12000),
        ("Air", 12000, 20000),
    )

    # Per-metric tolerance table. Keys are normalized metric names.
    METRIC_TOLERANCES = {
        "lufs": (1.0, "LU"),
        "peak": (1.0, "dB"),
        "rms": (1.0, "dB"),
        "tempo": (1.0, "BPM"),
        "spectral_centroid": (100.0, "Hz"),
        "spectral_bandwidth": (100.0, "Hz"),
        "spectral_rolloff": (100.0, "Hz"),
        "stereo_width": (0.1, "normalized"),
        "phase": (0.1, "normalized"),
        "spectral_flatness": (0.1, "normalized"),
        "zero_crossing_rate": (0.1, "normalized"),
        "dynamic_range": (2.0, "dB"),
        "crest_factor": (2.0, "dB"),
        "onset_count": (10.0, "count"),
    }

    # Fallback tolerances when a metric is not explicitly configured.
    DEFAULT_TOLERANCE = 1.0
    DEFAULT_UNIT = ""

    def compare_metrics(
        self,
        reference: dict,
        current: dict,
    ) -> ReferenceComparison:

        metrics: list[ReferenceMetric] = []
        decisions: list[EngineerDecision] = []
        bands: list[BandDifference] = []

        scores: list[float] = []
        category_scores: dict[Category, list[float]] = {
            category: [] for category in Category
        }

        for key, ref_value in reference.items():

            if key not in current:
                continue

            cur_value = current[key]

            if not isinstance(ref_value, (int, float)):
                continue

            if not isinstance(cur_value, (int, float)):
                continue

            diff = cur_value - ref_value

            tolerance, unit = self._tolerance_and_unit(key)

            passed = abs(diff) <= tolerance

            severity = self._severity(diff)

            metrics.append(
                ReferenceMetric(
                    name=key,
                    reference=float(ref_value),
                    current=float(cur_value),
                    difference=float(diff),
                    tolerance=tolerance,
                    passed=passed,
                    unit=unit,
                    severity=severity,
                )
            )

            similarity = max(
                0.0,
                100.0 - abs(diff) * 10,
            )

            scores.append(similarity)

            category = self._category(key)
            category_scores[category].append(similarity)

            if not passed:

                decisions.append(
                    EngineerDecision(
                        title=f"{key} Adjustment",
                        description=f"{key} differs by {diff:.2f} {unit}",
                        category=category,
                        severity=severity,
                        confidence=0.90,
                        recommendation=self._recommendation(
                            key,
                            diff,
                            unit,
                        ),
                    )
                )

        if "bands" in reference and "bands" in current:

            bands = self._compare_bands(
                reference["bands"],
                current["bands"],
            )

        overall = (
            sum(scores) / len(scores)
            if scores
            else 100.0
        )

        def _category_score(category: Category) -> float:
            values = category_scores[category]
            return sum(values) / len(values) if values else overall

        return ReferenceComparison(
            similarity=overall,
            confidence=0.95,
            frequency_score=_category_score(Category.FREQUENCY),
            dynamic_score=_category_score(Category.DYNAMICS),
            stereo_score=_category_score(Category.STEREO),
            loudness_score=_category_score(Category.LOUDNESS),
            transient_score=_category_score(Category.TRANSIENT),
            phase_score=_category_score(Category.PHASE),
            tonal_score=_category_score(Category.TONAL),
            semantic_score=overall,
            band_differences=bands,
            engineer_decisions=decisions,
            metrics=metrics,
        )

    def _tolerance_and_unit(
        self,
        metric: str,
    ) -> tuple[float, str]:

        key = metric.lower()
        return self.METRIC_TOLERANCES.get(
            key,
            (self.DEFAULT_TOLERANCE, self.DEFAULT_UNIT),
        )

    def _compare_bands(
        self,
        reference: dict,
        current: dict,
    ) -> list[BandDifference]:

        result = []

        for name, low, high in self.BAND_LIMITS:

            ref = float(reference.get(name, 0.0))
            cur = float(current.get(name, 0.0))

            diff = cur - ref

            result.append(
                BandDifference(
                    band=name,
                    start_hz=low,
                    end_hz=high,
                    reference_energy=ref,
                    current_energy=cur,
                    difference_db=diff,
                    severity=self._severity(diff),
                )
            )

        return result

    def _severity(
        self,
        difference: float,
    ) -> Severity:

        value = abs(difference)

        if value < 1:
            return Severity.INFO

        if value < 2:
            return Severity.LOW

        if value < 4:
            return Severity.MEDIUM

        if value < 6:
            return Severity.HIGH

        return Severity.CRITICAL

    def _category(
        self,
        metric: str,
    ) -> Category:

        metric = metric.lower()

        if "lufs" in metric:
            return Category.LOUDNESS

        if "peak" in metric:
            return Category.LOUDNESS

        if "rms" in metric:
            return Category.DYNAMICS

        if "crest" in metric:
            return Category.DYNAMICS

        if "dynamic" in metric:
            return Category.DYNAMICS

        if "stereo" in metric:
            return Category.STEREO

        if "phase" in metric:
            return Category.PHASE

        if "transient" in metric or "onset" in metric:
            return Category.TRANSIENT

        if "spectral" in metric or "zero_crossing" in metric:
            return Category.FREQUENCY

        if "tempo" in metric or "pitch" in metric or "key" in metric:
            return Category.TONAL

        return Category.TONAL

    def _recommendation(
        self,
        metric: str,
        difference: float,
        unit: str,
    ) -> str:

        if difference > 0:

            return (
                f"Reduce {metric} "
                f"by approximately {abs(difference):.2f} {unit}"
            )

        return (
            f"Increase {metric} "
            f"by approximately {abs(difference):.2f} {unit}"
        )
