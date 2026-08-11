from __future__ import annotations

import re


class ReportValidator:
    def validate(
        self,
        summary: str,
    ) -> str:
        if not summary:
            return summary

        result = summary

        replacements = {
            r"high risk of clipping": "possible clipping risk",
            r"critical clipping risk": "possible clipping risk",
            r"immediate action is required": "review is recommended",
            r"professional standard": "technical measurement",
        }

        for pattern, replacement in replacements.items():
            result = re.sub(
                pattern,
                replacement,
                result,
                flags=re.IGNORECASE,
            )

        remove_patterns = [
            r"without being overly wide or narrow",
            r"sounds good across all playback systems",
            r"often features dense transients",
            r"listener fatigue",
            r"across all playback systems",
        ]

        for pattern in remove_patterns:
            result = re.sub(
                pattern,
                "",
                result,
                flags=re.IGNORECASE,
            )

        # Collapse leftover multiple spaces, but keep markdown structure intact.
        result = re.sub(r" {2,}", " ", result)
        result = re.sub(r"\n\s*\n\s*\n+", "\n\n", result)

        return result.strip()
