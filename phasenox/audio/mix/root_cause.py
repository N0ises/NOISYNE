from __future__ import annotations

import re

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext
from phasenox.audio.engineer.models import EngineerResult

from .models import RootCause, RootCauseResult


class RootCauseAnalyzer:
    """
    Lightweight rule-based root-cause analyzer for mix issues.

    Sprint 5 uses deterministic heuristics only. No models are loaded.
    """

    def analyze(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        engineer: EngineerResult,
    ) -> RootCauseResult:
        causes: list[RootCause] = []
        scores: dict[str, float] = {
            "measurement_confidence": 0.90,
            "rule_confidence": 0.85,
            "context_confidence": context.confidence,
        }

        issue_titles = {issue.title.lower() for issue in engineer.issues}

        if self._harsh_highs(analysis, context, issue_titles):
            causes.append(
                RootCause(
                    symptom="harsh or fatiguing high end",
                    likely_causes=[
                        "excessive 2–5 kHz energy",
                        "aggressive EQ or saturation on vocals/instruments",
                    ],
                    priority="medium",
                    confidence=0.82,
                )
            )

        if self._over_compression(analysis, context, issue_titles):
            causes.append(
                RootCause(
                    symptom="flat or lifeless dynamics",
                    likely_causes=[
                        "over-compression on the mix bus or individual tracks",
                        "excessive limiting",
                    ],
                    priority="high",
                    confidence=0.85,
                )
            )

        if self._loudness_shortfall(analysis, context, issue_titles):
            causes.append(
                RootCause(
                    symptom="mix is quieter than the delivery target",
                    likely_causes=[
                        "insufficient limiting",
                        "conservative gain staging",
                    ],
                    priority="high",
                    confidence=0.80,
                )
            )

        if self._loudness_excess(analysis, context, issue_titles):
            causes.append(
                RootCause(
                    symptom="mix is louder than the delivery target",
                    likely_causes=[
                        "excessive limiting",
                        "aggressive gain staging",
                    ],
                    priority="high",
                    confidence=0.80,
                )
            )

        if self._narrow_or_phase_issues(analysis, context, issue_titles):
            causes.append(
                RootCause(
                    symptom="narrow or unstable stereo image",
                    likely_causes=[
                        "overly narrow panning",
                        "phase cancellation between tracks",
                    ],
                    priority="medium",
                    confidence=0.78,
                )
            )

        if not causes:
            causes.append(
                RootCause(
                    symptom="no strong root-cause indicators detected",
                    likely_causes=["measurements are within typical ranges"],
                    priority="low",
                    confidence=0.70,
                )
            )

        scores["final_confidence"] = sum(scores.values()) / len(scores) if scores else 0.0

        return RootCauseResult(
            causes=causes,
            confidence_scores=scores,
        )

    def _harsh_highs(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        issue_titles: set[str],
    ) -> bool:
        return self._whole_word_match(issue_titles, ("harsh", "sibilance", "brightness")) or (
            analysis.spectral_centroid > 5000.0 and any("harsh" in note.lower() for note in context.notes)
        )

    def _over_compression(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        issue_titles: set[str],
    ) -> bool:
        return {"dynamic range", "dynamics"} & issue_titles or (
            analysis.dynamic_range < 6.0 and analysis.lufs > -12.0
        )

    def _loudness_shortfall(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        issue_titles: set[str],
    ) -> bool:
        return "loudness too quiet" in issue_titles or (
            context.is_full_mix and analysis.lufs < -16.0
        )

    def _loudness_excess(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        issue_titles: set[str],
    ) -> bool:
        return "loudness too loud" in issue_titles or (
            context.is_full_mix and analysis.lufs > -8.0
        )

    def _narrow_or_phase_issues(
        self,
        analysis: AnalysisResult,
        context: AudioContext,
        issue_titles: set[str],
    ) -> bool:
        return self._whole_word_match(
            issue_titles, ("phase correlation", "stereo width", "mono", "width")
        ) or (analysis.stereo_width < 0.3 and analysis.phase < 0.5)

    @staticmethod
    def _whole_word_match(titles: set[str], words: tuple[str, ...]) -> bool:
        return any(
            re.search(rf"\b{re.escape(word)}\b", title) for title in titles for word in words
        )
