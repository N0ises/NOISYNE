from __future__ import annotations

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext

from .models import EngineerResult
from .rules import RuleEngine


class AudioEngineer:

    def __init__(self) -> None:

        self._rules = RuleEngine()

    def analyze(
        self,
        analysis: AnalysisResult,
        *,
        context: AudioContext | None = None,
    ) -> EngineerResult:

        (
            strengths,
            issues,
            recommendations,
            score,
        ) = self._rules.evaluate(
            analysis=analysis,
            context=context,
        )

        return EngineerResult(
            score=score,
            strengths=strengths,
            issues=issues,
            recommendations=recommendations,
        )