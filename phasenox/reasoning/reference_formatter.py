from __future__ import annotations

from .reference_models import ReferenceReasoningContext


class ReferenceReasoningFormatter:

    def build(
        self,
        context: ReferenceReasoningContext,
    ) -> str:

        lines: list[str] = []

        lines.extend(
            self._reference_section(
                context,
            )
        )

        lines.append("")

        lines.extend(
            self._current_section(
                context,
            )
        )

        lines.append("")

        lines.extend(
            self._comparison_section(
                context,
            )
        )

        lines.append("")

        lines.extend(
            self._question_section(
                context,
            )
        )

        return "\n".join(lines)

    def _reference_section(
        self,
        context: ReferenceReasoningContext,
    ) -> list[str]:

        a = context.reference

        return [

            "### Reference Track",

            f"Tempo: {a.tempo:.2f} BPM",

            f"Key: {a.key}",

            f"LUFS: {a.lufs:.2f}",

            f"Peak: {a.peak:.4f}",

            f"Dynamic Range: {a.dynamic_range:.2f}",

            f"Stereo Width: {a.stereo_width:.4f}",

            f"Phase: {a.phase:.4f}",

            f"Spectral Centroid: {a.spectral_centroid:.2f}",

            f"Spectral Bandwidth: {a.spectral_bandwidth:.2f}",

            f"Spectral Rolloff: {a.spectral_rolloff:.2f}",

            f"Spectral Contrast: {a.spectral_contrast:.2f}",

            "",

            "Additional Metrics",

            f"RMS: {a.rms:.4f}",

            f"Crest Factor: {a.crest_factor:.2f}",

            f"Pitch: {a.pitch:.2f}",

            f"Spectral Flatness: {a.spectral_flatness:.6f}",

            f"Zero Crossing Rate: {a.zero_crossing_rate:.6f}",

            f"MFCC Count: {len(a.mfcc)}",

            f"Chroma Count: {len(a.chroma)}",

            f"Onsets: {a.onset_count}",

        ]

    def _current_section(
        self,
        context: ReferenceReasoningContext,
    ) -> list[str]:

        a = context.current

        return [

            "### Current Mix",

            f"Tempo: {a.tempo:.2f} BPM",

            f"Key: {a.key}",

            f"LUFS: {a.lufs:.2f}",

            f"Peak: {a.peak:.4f}",

            f"Dynamic Range: {a.dynamic_range:.2f}",

            f"Stereo Width: {a.stereo_width:.4f}",

            f"Phase: {a.phase:.4f}",

            f"Spectral Centroid: {a.spectral_centroid:.2f}",

            f"Spectral Bandwidth: {a.spectral_bandwidth:.2f}",

            f"Spectral Rolloff: {a.spectral_rolloff:.2f}",

            f"Spectral Contrast: {a.spectral_contrast:.2f}",

            "",

            "Additional Metrics",

            f"RMS: {a.rms:.4f}",

            f"Crest Factor: {a.crest_factor:.2f}",

            f"Pitch: {a.pitch:.2f}",

            f"Spectral Flatness: {a.spectral_flatness:.6f}",

            f"Zero Crossing Rate: {a.zero_crossing_rate:.6f}",

            f"MFCC Count: {len(a.mfcc)}",

            f"Chroma Count: {len(a.chroma)}",

            f"Onsets: {a.onset_count}",

        ]

    def _comparison_section(
        self,
        context: ReferenceReasoningContext,
    ) -> list[str]:

        report = context.comparison

        lines = [

            "### Comparison",

            f"Overall Match: {report.overall_score:.2f}%",
            "",
            "Explain why the mixes differ. Focus on engineering decisions rather than repeating measurements.",

            "",

            "Summary:",

            report.summary,

            "",

            "Strengths:",

        ]

        if report.strengths:

            for item in report.strengths:

                lines.append(

                    f"- {item.title}: {item.description}"

                )

        else:

            lines.append(

                "- None"

            )

        lines.append("")

        lines.append("Warnings:")

        if report.warnings:

            for item in report.warnings:

                lines.append(

                    f"- {item.title}: {item.description}"

                )

                if item.recommendation:

                    lines.append(

                        f"  Recommendation: {item.recommendation}"

                    )

        else:

            lines.append(

                "- None"

            )

        if report.recommendations:

            lines.append("")
            lines.append("Engineer Recommendations:")

            for recommendation in report.recommendations:

                lines.append(

                    f"- {recommendation}"

                )

        return lines

    def _question_section(
        self,
        context: ReferenceReasoningContext,
    ) -> list[str]:

        return [

            "### Instructions",

            "Analyze the reference and current mix.",

            "Explain engineering reasoning instead of repeating metrics.",

            "Describe likely engineering decisions.",

            "Provide practical recommendations.",

            "",

            "### User Request",

            context.question,

        ]