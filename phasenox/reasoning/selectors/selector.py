from __future__ import annotations

from .models import PromptFeatures


class PromptSelector:

    def select(
        self,
        question: str,
    ) -> PromptFeatures:

        q = question.lower()

        features = PromptFeatures()

        # ---------------------------------
        # Loudness
        # ---------------------------------

        if any(
            word in q
            for word in [
                "loud",
                "lufs",
                "volume",
                "gain",
                "peak",
                "rms",
            ]
        ):

            features.sections = [
                "loudness",
                "dynamic",
            ]

            return features

        # ---------------------------------
        # Stereo
        # ---------------------------------

        if any(
            word in q
            for word in [
                "stereo",
                "mono",
                "phase",
                "width",
                "pan",
            ]
        ):

            features.sections = [
                "stereo",
            ]

            return features

        # ---------------------------------
        # Tone / EQ
        # ---------------------------------

        if any(
            word in q
            for word in [
                "eq",
                "tone",
                "bright",
                "dark",
                "mud",
                "harsh",
                "frequency",
            ]
        ):

            features.sections = [
                "spectral",
            ]

            return features

        # ---------------------------------
        # Tempo
        # ---------------------------------

        if any(
            word in q
            for word in [
                "tempo",
                "bpm",
                "timing",
                "rhythm",
            ]
        ):

            features.sections = [
                "tempo",
            ]

            return features

        # ---------------------------------
        # Pitch / Key
        # ---------------------------------

        if any(
            word in q
            for word in [
                "pitch",
                "key",
                "note",
                "tuning",
            ]
        ):

            features.sections = [
                "pitch",
            ]

            return features

        # ---------------------------------
        # Default
        # ---------------------------------

        features.sections = [
            "summary",
        ]

        return features