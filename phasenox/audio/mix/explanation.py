from __future__ import annotations

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext
from phasenox.audio.engineer.models import EngineerResult

from .models import ProcessingStep, RootCause


class ExplanationBuilder:
    """
    Produce concise, deterministic engineering explanations.

    Sprint 5 uses templates only. No LLM is required.
    """

    def build(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        engineer: EngineerResult,
        root_causes: list[RootCause],
        processing_chain: list[ProcessingStep],
    ) -> list[str]:
        explanations: list[str] = []

        if context.is_full_mix:
            explanations.append(
                f"The full mix scores {engineer.score:.0f}/100. "
                f"Analysis confidence is {context.confidence:.0%}."
            )
        else:
            explanations.append(
                f"The audio scores {engineer.score:.0f}/100. "
                f"Analysis confidence is {context.confidence:.0%}."
            )

        if analysis.lufs < -16.0 and context.is_full_mix:
            explanations.append(
                f"The mix is {abs(analysis.lufs + 14):.1f} dB below a typical "
                "streaming target, likely due to conservative limiting or gain staging."
            )
        elif analysis.lufs > -8.0 and context.is_full_mix:
            explanations.append(
                f"The mix is loud ({analysis.lufs:.1f} LUFS); check for distortion "
                "or lost dynamics on streaming platforms."
            )

        if analysis.dynamic_range < 6.0:
            explanations.append(
                f"Dynamic range is {analysis.dynamic_range:.1f} dB, which suggests "
                "heavy compression or limiting."
            )

        if analysis.spectral_centroid > 5000.0:
            explanations.append(
                "The spectral centroid is high, indicating a bright or potentially harsh mix."
            )

        for cause in root_causes[:3]:
            explanations.append(
                f"{cause.symptom.capitalize()} — likely cause(s): "
                f"{', '.join(cause.likely_causes)}."
            )

        for step in processing_chain[:3]:
            explanations.append(
                f"Step {step.order}: use a {step.plugin_type} to target {step.target} "
                f"({step.estimated_impact} impact)."
            )

        if not explanations:
            explanations.append("No strong engineering issues detected; the mix appears balanced.")

        return explanations
