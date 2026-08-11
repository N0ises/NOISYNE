from __future__ import annotations


from .models import ReasoningContext



class ReasoningFormatter:
    """
    Converts internal analysis objects into structured
    verified facts for the reasoning LLM.

    This layer does not interpret audio.
    It only exposes existing verified information.
    """



    def build(
        self,
        context: ReasoningContext,
    ) -> str:


        sections: list[str] = []


        sections.append(
            "Verified Audio Facts"
        )

        sections.append(
            "===================="
        )

        sections.append(
            ""
        )


        sections.extend(
            self._context_section(
                context
            )
        )


        sections.append(
            ""
        )


        sections.extend(
            self._measurement_section(
                context
            )
        )


        sections.append(
            ""
        )


        sections.extend(
            self._engineer_section(
                context
            )
        )


        sections.append(
            ""
        )


        sections.extend(
            self._semantic_section(
                context
            )
        )


        sections.append(
            ""
        )


        sections.append(
            "Question"
        )

        sections.append(
            "--------"
        )

        sections.append(
            context.question
        )


        return "\n".join(
            sections
        )



    def _context_section(
        self,
        context: ReasoningContext,
    ) -> list[str]:


        audio = context.audio_context


        return [

            "Audio Context",

            "-------------",

            f"Type: {audio.audio_type}",

            f"Source: {audio.source_type}",

            f"Instrument: {audio.instrument}",

            f"Full Mix: {audio.is_full_mix}",

            f"Confidence: {audio.confidence:.2f}",

        ]



    def _measurement_section(
        self,
        context: ReasoningContext,
    ) -> list[str]:


        a = context.analysis


        lines = [

            "Measurements",

            "------------",

        ]


        fields = [

            ("Tempo", "tempo", "BPM", ".2f"),

            ("Pitch", "pitch", "Hz", ".2f"),

            ("Key", "key", "", ""),

            ("LUFS", "lufs", "LUFS", ".2f"),

            ("Peak", "peak", "linear", ".4f"),

            ("RMS", "rms", "", ".4f"),

            ("Dynamic Range", "dynamic_range", "dB", ".2f"),

            ("Crest Factor", "crest_factor", "dB", ".2f"),

            ("Stereo Width", "stereo_width", "", ".4f"),

            ("Phase Correlation", "phase", "", ".4f"),

            ("Spectral Centroid", "spectral_centroid", "Hz", ".2f"),

            ("Spectral Bandwidth", "spectral_bandwidth", "Hz", ".2f"),

            ("Spectral Rolloff", "spectral_rolloff", "Hz", ".2f"),

            ("Spectral Flatness", "spectral_flatness", "", ".6f"),

            ("Spectral Contrast", "spectral_contrast", "", ".2f"),

            ("Zero Crossing Rate", "zero_crossing_rate", "", ".6f"),

            ("MFCC Count", "mfcc", "", ""),

            ("Chroma Count", "chroma", "", ""),

            ("Onsets", "onset_count", "", ""),

        ]


        for name, attribute, unit, fmt in fields:


            value = getattr(
                a,
                attribute,
                None,
            )


            if value is None:

                continue



            if isinstance(value, list):

                if not value:

                    continue

                value = f"len={len(value)}, mean={sum(value) / len(value):.4f}"

                lines.append(
                    f"{name}: {value}"
                )

                continue


            if fmt:

                value = format(
                    value,
                    fmt,
                )


            if unit:

                lines.append(
                    f"{name}: {value} {unit}"
                )

            else:

                lines.append(
                    f"{name}: {value}"
                )



        return lines



    def _engineer_section(
        self,
        context: ReasoningContext,
    ) -> list[str]:


        engineer = context.engineer


        lines = [

            "Engineer Findings",

            "------------------",

            f"Score: {engineer.score:.1f}/100",

            "",

            "Strengths",

        ]


        for item in engineer.strengths:

            lines.append(
                f"- {item}"
            )


        lines.append(
            ""
        )

        lines.append(
            "Issues"
        )


        for issue in engineer.issues:


            lines.append(
                f"- {issue.title}"
            )


            lines.append(
                f"  Severity: {issue.severity}"
            )


            lines.append(
                f"  Description: {issue.description}"
            )


            lines.append(
                f"  Recommendation: {issue.recommendation}"
            )


        return lines



    def _semantic_section(
        self,
        context: ReasoningContext,
    ) -> list[str]:


        audio = context.audio_context


        lines = [

            "Semantic Understanding",

            "----------------------",

        ]


        if not audio.semantic_labels:

            lines.append(
                "No semantic labels available."
            )

            return lines



        for item in audio.semantic_labels:

            lines.append(

                f"- {item.name}: {item.confidence:.2f}"

            )


        return lines