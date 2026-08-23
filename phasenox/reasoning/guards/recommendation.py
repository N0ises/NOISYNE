from __future__ import annotations

import re

from phasenox.audio.context.models import AudioContext


class RecommendationGuard:

    def filter(
        self,
        response: str,
        context: AudioContext | None,
    ) -> str:

        if context is None:
            return response


        if context.is_full_mix:
            return response


        filtered = response


        blocked_patterns = [

            r"Consider expanding the stereo image.*?\.",

            r"consider expanding the stereo image.*?\.",


            r"Consider widening the stereo image.*?\.",

            r"consider widening the stereo image.*?\.",


            r"Monitor the balance with other stems.*?\.",

            r"monitor the balance with other stems.*?\.",


            r"Use reference tracks.*?\.",

            r"use reference tracks.*?\.",


            r"consider broadening it.*?\.",
        ]


        for pattern in blocked_patterns:

            filtered = re.sub(
                pattern,
                "",
                filtered,
                flags=re.IGNORECASE,
            )


        # Clean empty bullet points

        filtered = re.sub(
            r"-\s*\.",
            "",
            filtered,
        )


        filtered = re.sub(
            r"\n\s*\n\s*\n",
            "\n\n",
            filtered,
        )


        return filtered.strip()