from __future__ import annotations

from .report_models import ComparisonReport


class ComparisonReportBuilder:

    def build(
        self,
        report: ComparisonReport,
    ) -> str:

        lines = []

        lines.append(
            "========== Reference Comparison =========="
        )

        lines.append("")

        lines.append(
            f"Overall Match : {report.overall_score:.2f}%"
        )

        lines.append("")

        lines.append("Summary")
        lines.append("------------------------")
        lines.append(report.summary)
        lines.append("")

        if report.strengths:

            lines.append("Strengths")
            lines.append("------------------------")

            for item in report.strengths:

                lines.append(
                    f"✓ {item.title}"
                )

                lines.append(
                    f"  Status : {item.status}"
                )

                lines.append(
                    f"  {item.description}"
                )

                lines.append("")

        if report.warnings:

            lines.append("Warnings")
            lines.append("------------------------")

            for item in report.warnings:

                lines.append(
                    f"⚠ {item.title}"
                )

                lines.append(
                    f"  Status : {item.status}"
                )

                lines.append(
                    f"  {item.description}"
                )

                if item.recommendation:

                    lines.append(
                        f"  Recommendation : {item.recommendation}"
                    )

                lines.append("")

        if report.recommendations:

            lines.append("Recommendations")
            lines.append("------------------------")

            for item in report.recommendations:

                lines.append(
                    f"- {item}"
                )

        return "\n".join(lines)