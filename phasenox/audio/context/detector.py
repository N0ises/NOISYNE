from __future__ import annotations

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.intelligence import (
    AudioIntelligenceAnalyzer,
)

from .classifier import AudioClassifier
from .models import AudioContext
from .rules import ContextRuleEngine


class AudioContextDetector:


    def __init__(
        self,
    ) -> None:


        self._rules = ContextRuleEngine()


        self._classifier = AudioClassifier()


        self._intelligence = (
            AudioIntelligenceAnalyzer()
        )



    def detect(
        self,
        analysis: AnalysisResult,
        audio=None,
    ) -> AudioContext:


        context = self._rules.detect(
            analysis,
        )


        semantic = None


        if audio is not None:

            semantic = (
                self._intelligence.analyze(
                    audio
                )
            )


        return self._classifier.classify(
            analysis,
            context,
            semantic,
        )