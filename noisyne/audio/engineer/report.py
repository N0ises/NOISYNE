from __future__ import annotations

from .models import EngineerResult


class EngineerReport:

    def build(
        self,
        result: EngineerResult,
        *,
        sections: list[str] | None = None,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "========== SoundBrain Engineer =========="
        )

        lines.append("")

        lines.append(
            f"Overall Score : {result.score:.1f}/100"
        )

        lines.append("")


        # -------------------------
        # Strengths
        # -------------------------

        if result.strengths:

            lines.append(
                "Strengths"
            )

            lines.append(
                "-----------"
            )

            for item in result.strengths:

                lines.append(
                    f"✓ {item}"
                )

            lines.append("")


        # -------------------------
        # Issues
        # -------------------------

        if result.issues:

            lines.append(
                "Issues"
            )

            lines.append(
                "------"
            )

            for issue in result.issues:

                lines.append(
                    f"[{issue.severity.upper()}] {issue.title}"
                )

                lines.append(
                    f"  {issue.description}"
                )

                lines.append("")


        # -------------------------
        # Recommendations
        # -------------------------

        if result.recommendations:

            lines.append(
                "Recommendations"
            )

            lines.append(
                "----------------"
            )

            for item in result.recommendations:

                lines.append(
                    f"• {item.title}"
                )

                lines.append(
                    f"  Reason: {item.reason}"
                )

                lines.append(
                    f"  Action: {item.action}"
                )

                lines.append("")


        lines.append(
            "========================================="
        )


        return "\n".join(lines)