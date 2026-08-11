from __future__ import annotations

import math

from brain.audio.analysis.models import AnalysisResult
from brain.audio.context.models import AudioContext

from .models import (
    Issue,
    Recommendation,
)


class RuleEngine:

    CLIPPING_THRESHOLD = 0.99997

    def evaluate(
        self,
        *,
        analysis: AnalysisResult,
        context: AudioContext | None = None,
    ) -> tuple[
        list[str],
        list[Issue],
        list[Recommendation],
        float,
    ]:

        if self._is_silent(analysis):

            strengths = []
            issues = [
                Issue(
                    title="Silence",
                    severity="high",
                    description="The signal is effectively silent or has no measurable loudness.",
                    recommendation="Verify the source audio is not empty or muted before mastering.",
                ),
            ]
            recommendations = []
            score = 5.0

            if context and not context.is_full_mix:
                strengths.append("Stem loudness is informational because the input is silent.")

            return (
                strengths,
                issues,
                recommendations,
                score,
            )

        if context and not context.is_full_mix:

            return self._evaluate_stem(
                analysis
            )

        return self._evaluate_mix(
            analysis
        )

    @staticmethod
    def _is_silent(
        analysis: AnalysisResult,
    ) -> bool:

        if analysis.rms <= 1e-6:
            return True

        if math.isinf(analysis.lufs) or math.isnan(analysis.lufs):
            return True

        return False

    # =====================================
    # Full Mix / Master Rules
    # =====================================

    def _evaluate_mix(
        self,
        analysis: AnalysisResult,
    ):

        strengths = []
        issues = []
        recommendations = []

        score = 100.0


        # -------------------------
        # Loudness
        # -------------------------

        if math.isnan(analysis.lufs) or math.isinf(analysis.lufs):

            strengths.append(
                "Loudness could not be measured; skipping loudness scoring."
            )

        elif -14.5 <= analysis.lufs <= -9.0:

            strengths.append(
                "Loudness is well balanced."
            )

        elif analysis.lufs < -14.5:

            score -= 8

            issues.append(
                Issue(
                    title="Loudness too quiet",
                    severity="medium",
                    description=(
                        "Integrated loudness is below the expected range "
                        "for a full mix."
                    ),
                    recommendation=(
                        "Increase gain and apply tasteful limiting."
                    ),
                )
            )

        else:

            score -= 8

            issues.append(
                Issue(
                    title="Loudness too loud",
                    severity="medium",
                    description=(
                        "Integrated loudness is above the expected range "
                        "for a full mix."
                    ),
                    recommendation=(
                        "Reduce output gain; do not add more limiting."
                    ),
                )
            )


        # -------------------------
        # Dynamic Range
        # -------------------------

        if analysis.dynamic_range >= 8:

            strengths.append(
                "Dynamic range is healthy."
            )

        else:

            score -= 10

            issues.append(
                Issue(
                    title="Dynamic Range",
                    severity="medium",
                    description=(
                        "Dynamic range is limited."
                    ),
                    recommendation=(
                        "Review compression and limiting."
                    ),
                )
            )


        # -------------------------
        # Peak / Clipping
        # -------------------------

        if analysis.peak >= self.CLIPPING_THRESHOLD:

            score -= 10

            issues.append(
                Issue(
                    title="Clipping",
                    severity="high",
                    description=(
                        "Peak level is at or near 0 dBFS. "
                        "Possible digital clipping or "
                        "inter-sample peak distortion."
                    ),
                    recommendation=(
                        "Reduce output gain and check true peak levels."
                    ),
                )
            )

        else:

            strengths.append(
                "No digital clipping detected."
            )


        # -------------------------
        # Phase Correlation
        # -------------------------

        if math.isnan(analysis.phase):

            strengths.append(
                "Mono/stereo metrics not applicable."
            )

        elif analysis.phase >= 0.7:

            strengths.append(
                "Stereo phase correlation is strong."
            )


        elif analysis.phase >= 0.3:

            issues.append(
                Issue(
                    title="Phase Correlation",
                    severity="low",
                    description=(
                        "Stereo correlation is moderate. "
                        "Review mono compatibility if required."
                    ),
                    recommendation=(
                        "Check mono compatibility during final review."
                    ),
                )
            )

        else:

            score -= 8

            issues.append(
                Issue(
                    title="Phase Correlation",
                    severity="high",
                    description=(
                        "Low stereo correlation detected. "
                        "Possible phase cancellation issues."
                    ),
                    recommendation=(
                        "Review stereo processing and polarity."
                    ),
                )
            )


        # -------------------------
        # Stereo Width
        # -------------------------

        if math.isnan(analysis.stereo_width):

            strengths.append(
                "Mono/stereo metrics not applicable."
            )

        elif analysis.stereo_width >= 0.10:

            strengths.append(
                "Stereo image is acceptable."
            )

        else:

            score -= 5

            issues.append(
                Issue(
                    title="Stereo Width",
                    severity="low",
                    description=(
                        "Stereo image is narrow."
                    ),
                    recommendation=(
                        "Review stereo enhancement decisions."
                    ),
                )
            )


        return (
            strengths,
            issues,
            recommendations,
            max(score, 0),
        )


    # =====================================
    # Stem / Instrument Rules
    # =====================================

    def _evaluate_stem(
        self,
        analysis: AnalysisResult,
    ):

        strengths = []
        issues = []
        recommendations = []

        score = 100.0


        strengths.append(
            "Loudness treated as informational because this is an isolated stem."
        )


        if analysis.dynamic_range >= 8:

            strengths.append(
                "Dynamic behavior is healthy."
            )

        else:

            score -= 5

            issues.append(
                Issue(
                    title="Dynamics",
                    severity="low",
                    description=(
                        "Stem has limited dynamic variation."
                    ),
                    recommendation=(
                        "Check compression or performance dynamics."
                    ),
                )
            )


        if analysis.peak < self.CLIPPING_THRESHOLD:

            strengths.append(
                "No digital clipping detected."
            )

        else:

            score -= 10

            issues.append(
                Issue(
                    title="Clipping",
                    severity="high",
                    description=(
                        "Signal exceeds digital peak limits."
                    ),
                    recommendation=(
                        "Reduce gain."
                    ),
                )
            )


        strengths.append(
            "Tonal characteristics detected."
        )


        return (
            strengths,
            issues,
            recommendations,
            max(score, 0),
        )
