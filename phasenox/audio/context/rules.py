from __future__ import annotations

import math

from phasenox.audio.analysis.models import AnalysisResult

from .models import AudioContext


class ContextRuleEngine:

    def detect(
        self,
        analysis: AnalysisResult,
    ) -> AudioContext:

        notes: list[str] = []

        elements: list[str] = []


        audio_type = "unknown"

        source_type = "unknown"

        is_full_mix = True

        confidence = 0.5


        # -------------------------
        # Stereo
        # -------------------------

        stereo_width_defined = (
            not math.isnan(analysis.stereo_width)
            and not math.isinf(analysis.stereo_width)
        )

        if stereo_width_defined and analysis.stereo_width < 0.15:

            notes.append(
                "Very narrow stereo image detected."
            )

            confidence += 0.1


        # -------------------------
        # Dynamics
        # -------------------------

        if analysis.dynamic_range < 5:

            notes.append(
                "Low dynamic variation detected."
            )


        # -------------------------
        # Onsets
        # -------------------------

        if analysis.onset_count < 20:

            notes.append(
                "Low transient activity."
            )


        elif analysis.onset_count > 100:

            notes.append(
                "High transient density."
            )


        # -------------------------
        # Context Detection
        # -------------------------

        # Stem classification requires strong, simultaneous stem indicators.
        # NaN/undefined stereo width is treated as mono/undefined and must not
        # force a stem classification.
        strong_stem_indicators = (
            analysis.onset_count < 40
            and analysis.spectral_centroid < 1200
            and stereo_width_defined
            and analysis.stereo_width < 0.05
        )

        if strong_stem_indicators:

            audio_type = "stem"

            source_type = "isolated_audio"

            is_full_mix = False

            confidence += 0.15

            notes.append(
                "Likely isolated instrument or stem."
            )


        else:

            audio_type = "mix"

            source_type = "full_track"

            is_full_mix = True

            confidence += 0.2

            notes.append(
                "Likely full mix or complete track."
            )


        confidence = min(
            confidence,
            1.0,
        )


        return AudioContext(
            audio_type=audio_type,
            source_type=source_type,
            detected_elements=elements,
            is_full_mix=is_full_mix,
            confidence=confidence,
            notes=notes,
        )
