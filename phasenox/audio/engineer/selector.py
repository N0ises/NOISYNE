from __future__ import annotations


class EngineerSelector:

    def select(
        self,
        question: str,
    ) -> list[str]:

        q = question.lower()


        # -------------------------
        # Loudness
        # -------------------------

        if any(
            word in q
            for word in [
                "loud",
                "lufs",
                "volume",
                "gain",
                "level",
                "quiet",
            ]
        ):

            return [
                "loudness",
                "dynamic",
            ]


        # -------------------------
        # Stereo
        # -------------------------

        if any(
            word in q
            for word in [
                "stereo",
                "width",
                "phase",
                "mono",
                "pan",
            ]
        ):

            return [
                "stereo",
                "phase",
            ]


        # -------------------------
        # Tone / EQ
        # -------------------------

        if any(
            word in q
            for word in [
                "tone",
                "eq",
                "bright",
                "dark",
                "mud",
                "harsh",
                "frequency",
            ]
        ):

            return [
                "spectral",
                "tone",
            ]


        # -------------------------
        # Dynamics
        # -------------------------

        if any(
            word in q
            for word in [
                "compression",
                "compressor",
                "dynamic",
                "transient",
                "punch",
            ]
        ):

            return [
                "dynamic",
            ]


        # -------------------------
        # Default
        # -------------------------

        return [
            "summary",
        ]