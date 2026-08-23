from __future__ import annotations

import re


class OutputGuard:
    """
    Cleans LLM reasoning output.

    Removes unsupported additions that are not
    present in verified audio facts.
    """


    def filter(
        self,
        response: str,
    ) -> str:


        filtered = response


        blocked_patterns = [

            # External standards

            r".{0,80}-1 dBTP.{0,80}\.",

            r".{0,80}professional standards.{0,80}\.",

            r".{0,80}industry standards.{0,80}\.",


            # Platform assumptions

            r".{0,80}streaming platforms.{0,80}\.",

            r".{0,80}most platforms.{0,80}\.",


            # Listener assumptions

            r".{0,80}comfortable listening.{0,80}\.",

            r".{0,80}pleasant listening.{0,80}\.",


            # Unsupported mastering advice

            r".{0,80}apply limiting.{0,80}\.",

            r".{0,80}use a limiter.{0,80}\.",


        ]


        for pattern in blocked_patterns:

            filtered = re.sub(
                pattern,
                "",
                filtered,
                flags=re.IGNORECASE,
            )


        filtered = re.sub(
            r"\n\s*\n\s*\n+",
            "\n\n",
            filtered,
        )


        return filtered.strip()