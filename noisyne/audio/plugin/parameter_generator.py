from __future__ import annotations

from .models import ParameterRecommendation, ProcessingGoal
from .taxonomy import (
    CATEGORY_CLIP,
    CATEGORY_COMPRESSOR,
    CATEGORY_EQ,
    CATEGORY_GAIN,
    CATEGORY_IMAGER,
    CATEGORY_LIMITER,
    CATEGORY_SATURATION,
    CATEGORY_TRANSIENT_SHAPER,
)


class ParameterGenerator:
    """Rule-based parameter recommendations for a processing goal and category."""

    def generate(
        self,
        goal: ProcessingGoal,
        category: str,
    ) -> list[ParameterRecommendation]:
        if category == CATEGORY_EQ:
            return self._eq_parameters(goal)
        if category == CATEGORY_COMPRESSOR:
            return self._compressor_parameters(goal)
        if category == CATEGORY_LIMITER:
            return self._limiter_parameters(goal)
        if category == CATEGORY_GAIN:
            return self._gain_parameters(goal)
        if category == CATEGORY_CLIP:
            return self._clip_parameters(goal)
        if category == CATEGORY_IMAGER:
            return self._imager_parameters(goal)
        if category == CATEGORY_TRANSIENT_SHAPER:
            return self._transient_parameters(goal)
        if category == CATEGORY_SATURATION:
            return self._saturation_parameters(goal)
        return []

    @staticmethod
    def _goal_text(goal: ProcessingGoal) -> str:
        """Concatenate goal fields into a searchable lowercase string."""
        parts = [
            goal.description or "",
            goal.action or "",
            goal.target or "",
            goal.root_cause or "",
        ]
        return " ".join(parts).lower()

    @staticmethod
    def _contains(text: str, *keywords: str) -> bool:
        return any(keyword in text for keyword in keywords)

    def _eq_parameters(self, goal: ProcessingGoal) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "mud", "muddy", "low", "bass", "boom", "rumble"):
            frequency = 250.0
            gain = -3.0
            reason_freq = "Target low-mid mud region"
            reason_gain = "Gentle reduction to reduce muddiness"
        elif self._contains(text, "harsh", "high", "sibilance", "brightness", "shrill"):
            frequency = 3000.0
            gain = -2.0
            reason_freq = "Target 2–5 kHz harshness region"
            reason_gain = "Gentle reduction to reduce harshness"
        else:
            frequency = 1000.0
            gain = -1.5
            reason_freq = "General tonal shaping"
            reason_gain = "Subtle corrective EQ"

        return [
            ParameterRecommendation(
                name="frequency",
                value=frequency,
                unit="Hz",
                range_min=20.0,
                range_max=20000.0,
                confidence=0.85,
                reason=reason_freq,
            ),
            ParameterRecommendation(
                name="gain",
                value=gain,
                unit="dB",
                range_min=-24.0,
                range_max=24.0,
                confidence=0.80,
                reason=reason_gain,
            ),
            ParameterRecommendation(
                name="q",
                value=1.4,
                range_min=0.1,
                range_max=10.0,
                confidence=0.85,
                reason="Moderate bandwidth for surgical cut",
            ),
        ]

    def _compressor_parameters(
        self,
        goal: ProcessingGoal,
    ) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "punch", "attack", "transient"):
            attack = 5.0
            ratio = 4.0
            reason_attack = "Fast attack to tame sharp transients while preserving punch"
        elif self._contains(text, "glue", "bus", "smooth"):
            attack = 20.0
            ratio = 2.0
            reason_attack = "Gentle attack for bus glue and smooth dynamics"
        else:
            attack = 10.0
            ratio = 3.0
            reason_attack = "Moderate attack to control peaks without crushing the mix"

        return [
            ParameterRecommendation(
                name="threshold",
                value=-18.0,
                unit="dB",
                range_min=-60.0,
                range_max=0.0,
                confidence=0.82,
                reason="Control peaks without crushing the mix",
            ),
            ParameterRecommendation(
                name="ratio",
                value=ratio,
                unit=":1",
                range_min=1.0,
                range_max=20.0,
                confidence=0.80,
                reason="Moderate gain reduction for dynamics",
            ),
            ParameterRecommendation(
                name="attack",
                value=attack,
                unit="ms",
                range_min=0.01,
                range_max=1000.0,
                confidence=0.78,
                reason=reason_attack,
            ),
            ParameterRecommendation(
                name="release",
                value=100.0,
                unit="ms",
                range_min=1.0,
                range_max=5000.0,
                confidence=0.78,
                reason="Natural recovery",
            ),
        ]

    def _limiter_parameters(self, goal: ProcessingGoal) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "safety", "clip", "peak"):
            ceiling = -1.5
            reason = "Safety headroom to prevent inter-sample peaks"
        else:
            ceiling = -1.0
            reason = "Prevent inter-sample peaks for streaming"

        return [
            ParameterRecommendation(
                name="ceiling",
                value=ceiling,
                unit="dB",
                range_min=-3.0,
                range_max=-0.1,
                confidence=0.88,
                reason=reason,
            ),
            ParameterRecommendation(
                name="release",
                value=50.0,
                unit="ms",
                range_min=1.0,
                range_max=5000.0,
                confidence=0.80,
                reason="Transparent loudness target",
            ),
            ParameterRecommendation(
                name="lookahead",
                value=5.0,
                unit="ms",
                range_min=0.0,
                range_max=20.0,
                confidence=0.75,
                reason="Catch peaks before they clip",
            ),
        ]

    def _imager_parameters(self, goal: ProcessingGoal) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "mono", "phase", "compatibility"):
            width = 100.0
            mono_below_hz = 80.0
            reason_width = "Restore mono compatibility without widening"
            reason_mono = "Focus bass mono compatibility below kick region"
        else:
            width = 125.0
            mono_below_hz = 120.0
            reason_width = "Widen narrow stereo image"
            reason_mono = "Improve mono compatibility below bass region"

        return [
            ParameterRecommendation(
                name="width",
                value=width,
                unit="%",
                range_min=0.0,
                range_max=200.0,
                confidence=0.75,
                reason=reason_width,
            ),
            ParameterRecommendation(
                name="mono_below_hz",
                value=mono_below_hz,
                unit="Hz",
                range_min=20.0,
                range_max=500.0,
                confidence=0.70,
                reason=reason_mono,
            ),
        ]

    def _transient_parameters(self, goal: ProcessingGoal) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "punch", "attack", "sharp"):
            attack = 20.0
            sustain = -10.0
            reason_attack = "Add punch to dull transients"
        elif self._contains(text, "smooth", "soft", "round"):
            attack = -10.0
            sustain = 10.0
            reason_attack = "Soften aggressive transients"
        else:
            attack = 20.0
            sustain = -10.0
            reason_attack = "Add punch to dull transients"

        return [
            ParameterRecommendation(
                name="attack",
                value=attack,
                unit="%",
                range_min=-100.0,
                range_max=100.0,
                confidence=0.75,
                reason=reason_attack,
            ),
            ParameterRecommendation(
                name="sustain",
                value=sustain,
                unit="%",
                range_min=-100.0,
                range_max=100.0,
                confidence=0.70,
                reason="Control decay",
            ),
        ]

    def _saturation_parameters(self, goal: ProcessingGoal) -> list[ParameterRecommendation]:
        text = self._goal_text(goal)

        if self._contains(text, "warmth", "warm"):
            drive = 15.0
            mix = 25.0
            reason = "Gentle harmonic warmth for a warmer tone"
        elif self._contains(text, "distort", "edge", "grit"):
            drive = 30.0
            mix = 30.0
            reason = "Add edge and grit with higher saturation"
        else:
            drive = 15.0
            mix = 25.0
            reason = "Add harmonic warmth"

        return [
            ParameterRecommendation(
                name="drive",
                value=drive,
                unit="%",
                range_min=0.0,
                range_max=100.0,
                confidence=0.70,
                reason=reason,
            ),
            ParameterRecommendation(
                name="mix",
                value=mix,
                unit="%",
                range_min=0.0,
                range_max=100.0,
                confidence=0.75,
                reason="Blend saturation with dry signal",
            ),
        ]
