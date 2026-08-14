from __future__ import annotations

from .models import (
    Category,
    DecisionType,
    EngineerDecision,
    ReferenceComparison,
    ReferenceIntent,
    Severity,
)


class ReferenceReasoner:
    """
    Converts raw comparison metrics into
    professional engineering decisions.

    This is the first reasoning layer.

    Future versions will integrate:

    - AES knowledge
    - Mix engineering rules
    - RAG
    - LLM reasoning
    - Learning system
    """

    def reason(
        self,
        comparison: ReferenceComparison,
        *,
        intent: ReferenceIntent | None = None,
    ) -> ReferenceComparison:

        decisions: list[EngineerDecision] = []

        decisions.extend(self._frequency(comparison))

        decisions.extend(self._loudness(comparison))

        decisions.extend(self._dynamics(comparison))

        decisions.extend(self._stereo(comparison))

        decisions.extend(self._phase(comparison))

        decisions.extend(self._transients(comparison))

        categorized = [
            self._categorize(
                decision,
                intent=intent,
            )
            for decision in comparison.engineer_decisions + decisions
        ]

        comparison.engineer_decisions = sorted(
            categorized,
            key=self._priority,
            reverse=True,
        )

        return comparison

    def build_prompt(
        self,
        comparison: ReferenceComparison,
        *,
        intent: ReferenceIntent | None = None,
    ) -> str:
        """
        Build a reference-specific prompt for future LLM integration.

        The prompt includes intent context, per-metric deltas, segment
        deviations, and per-reference similarity scores.
        """

        parts: list[str] = [
            "You are a senior mix engineer comparing a current mix to reference tracks.",
        ]

        if intent is not None:

            context_parts: list[str] = []

            if intent.genre:
                context_parts.append(f"Genre: {intent.genre}")

            if intent.mood:
                context_parts.append(f"Mood: {intent.mood}")

            if intent.target:
                context_parts.append(f"Delivery target: {intent.target}")

            if intent.focus_areas:
                context_parts.append(f"Focus areas: {', '.join(intent.focus_areas)}")

            if context_parts:
                parts.append("Intent context:\n" + "\n".join(context_parts))

        parts.append(f"Overall similarity: {comparison.similarity:.2f}%")
        parts.append(f"Confidence: {comparison.confidence:.2f}")

        if comparison.reference_similarities:

            parts.append("Per-reference similarity:")

            for (
                path,
                similarity,
            ) in comparison.reference_similarities.items():

                parts.append(f"  - {path}: {similarity:.2f}%")

        if comparison.metric_variance:

            parts.append("Metric variance across references:")

            for metric, value in comparison.metric_variance.items():

                parts.append(f"  - {metric}: {value:.4f}")

        if comparison.segment_deviations:

            parts.append("Segment deviations:")

            for seg in comparison.segment_deviations[:10]:

                parts.append(
                    f"  - {seg.start_time:.1f}s-{seg.end_time:.1f}s "
                    f"{seg.metric}: ref={seg.reference_value:.2f} "
                    f"cur={seg.current_value:.2f} ({seg.severity})"
                )

        if comparison.metrics:

            parts.append("Metric deltas:")

            for metric in comparison.metrics[:20]:

                parts.append(
                    f"  - {metric.name}: "
                    f"ref={metric.reference:.2f} "
                    f"cur={metric.current:.2f} "
                    f"Δ={metric.difference:.2f}"
                )

        return "\n\n".join(parts)

    def _categorize(
        self,
        decision: EngineerDecision,
        *,
        intent: ReferenceIntent | None = None,
    ) -> EngineerDecision:

        focus_areas = intent.focus_areas if intent is not None else []

        focus_hit = any(
            focus.lower() in decision.category.value.lower()
            or focus.lower() in decision.title.lower()
            for focus in focus_areas
        )

        if focus_hit:
            decision_type = DecisionType.STYLISTIC_DIFFERENCE
            confidence = min(decision.confidence * 1.05, 0.99)

        elif decision.confidence < 0.85:
            decision_type = DecisionType.INSUFFICIENT_EVIDENCE
            confidence = decision.confidence

        else:
            decision_type = DecisionType.TECHNICAL_ISSUE
            confidence = decision.confidence

        return EngineerDecision(
            title=decision.title,
            description=decision.description,
            category=decision.category,
            severity=decision.severity,
            confidence=round(confidence, 4),
            recommendation=decision.recommendation,
            plugin=decision.plugin,
            parameters=decision.parameters,
            decision_type=decision_type,
        )

    def _frequency(
        self,
        comparison: ReferenceComparison,
    ) -> list[EngineerDecision]:

        result = []

        for band in comparison.band_differences:

            if abs(band.difference_db) < 1.5:

                continue

            plugin = "FabFilter Pro-Q 4"

            if band.difference_db > 0:

                recommendation = f"Reduce {band.band} by " f"{abs(band.difference_db):.1f} dB"

            else:

                recommendation = f"Boost {band.band} by " f"{abs(band.difference_db):.1f} dB"

            result.append(
                EngineerDecision(
                    title=f"{band.band} Balance",
                    description=(f"{band.band} differs " "from the reference."),
                    category=Category.FREQUENCY,
                    severity=band.severity,
                    confidence=0.93,
                    recommendation=recommendation,
                    plugin=plugin,
                    parameters={
                        "band": band.band,
                        "start_hz": band.start_hz,
                        "end_hz": band.end_hz,
                        "difference_db": band.difference_db,
                    },
                )
            )

        return result

    def _loudness(
        self,
        comparison: ReferenceComparison,
    ):

        if comparison.loudness_score >= 95:

            return []

        return [
            EngineerDecision(
                title="Loudness",
                description=("Overall loudness " "differs from reference."),
                category=Category.LOUDNESS,
                severity=Severity.MEDIUM,
                confidence=0.90,
                recommendation=("Adjust limiter target LUFS."),
                plugin="FabFilter Pro-L 2",
            )
        ]

    def _dynamics(
        self,
        comparison: ReferenceComparison,
    ):

        if comparison.dynamic_score >= 95:

            return []

        return [
            EngineerDecision(
                title="Dynamics",
                description=("Dynamic profile " "is different."),
                category=Category.DYNAMICS,
                severity=Severity.MEDIUM,
                confidence=0.91,
                recommendation=("Review bus compression."),
                plugin="FabFilter Pro-C 2",
            )
        ]

    def _stereo(
        self,
        comparison: ReferenceComparison,
    ):

        if comparison.stereo_score >= 95:

            return []

        return [
            EngineerDecision(
                title="Stereo Image",
                description=("Stereo image differs."),
                category=Category.STEREO,
                severity=Severity.LOW,
                confidence=0.88,
                recommendation=("Adjust stereo width."),
                plugin="iZotope Ozone Imager",
            )
        ]

    def _phase(
        self,
        comparison: ReferenceComparison,
    ):

        if comparison.phase_score >= 95:

            return []

        return [
            EngineerDecision(
                title="Phase",
                description=("Possible phase issues."),
                category=Category.PHASE,
                severity=Severity.HIGH,
                confidence=0.94,
                recommendation=("Inspect mono compatibility."),
            )
        ]

    def _transients(
        self,
        comparison: ReferenceComparison,
    ):

        if comparison.transient_score >= 95:

            return []

        return [
            EngineerDecision(
                title="Transient",
                description=("Transient response " "is different."),
                category=Category.TRANSIENT,
                severity=Severity.MEDIUM,
                confidence=0.89,
                recommendation=("Review transient shaping."),
                plugin="SPL Transient Designer",
            )
        ]

    def _priority(
        self,
        decision: EngineerDecision,
    ) -> int:

        table = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }

        return table[decision.severity]
