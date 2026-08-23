from __future__ import annotations

from .models import ComparisonResult
from .report_models import (
    ComparisonReport,
    ReportSection,
)


class ComparisonInterpreter:

    def build(
        self,
        result: ComparisonResult,
    ) -> ComparisonReport:

        report = ComparisonReport(
            overall_score=result.score,
            summary="",
        )

        if result.score >= 95:

            report.summary = (
                "The current mix is extremely close to the reference."
            )

        elif result.score >= 85:

            report.summary = (
                "The current mix is generally close to the reference with a few differences."
            )

        elif result.score >= 70:

            report.summary = (
                "The mix differs noticeably from the reference and requires refinement."
            )

        else:

            report.summary = (
                "The mix differs significantly from the reference."
            )

        for metric in result.metrics:

            if metric.percent < 5:

                report.strengths.append(

                    ReportSection(

                        title=metric.name,

                        status="Excellent",

                        description="Very close to the reference.",

                    )

                )

                continue

            if metric.percent < 15:

                report.strengths.append(

                    ReportSection(

                        title=metric.name,

                        status="Good",

                        description="Acceptably close to the reference.",

                    )

                )

                continue

            recommendation = None

            if metric.name == "Stereo Width":

                recommendation = (
                    "Increase stereo width slightly."
                )

            elif metric.name == "Peak":

                recommendation = (
                    "Reduce output gain."
                )

            elif metric.name == "LUFS":

                recommendation = (
                    "Adjust integrated loudness."
                )

            report.warnings.append(

                ReportSection(

                    title=metric.name,

                    status="Needs Attention",

                    description="Difference exceeds the preferred range.",

                    recommendation=recommendation,

                )

            )

        report.recommendations.extend(
            result.recommendations
        )

        return report