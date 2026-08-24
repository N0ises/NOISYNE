from __future__ import annotations

from typing import Any

from phasenox.audio.analysis.models import AnalysisResult

from .classifier import AudioClassifier
from .models import AudioContext
from .rules import ContextRuleEngine


class AudioContextDetector:
    """Detect deterministic context and opt into semantic analysis explicitly."""

    def __init__(self, *, intelligence: Any | None = None) -> None:
        self._rules = ContextRuleEngine()
        self._classifier = AudioClassifier()
        self._intelligence = intelligence

    def detect(
        self,
        analysis: AnalysisResult,
        audio: Any | None = None,
    ) -> AudioContext:
        context = self._rules.detect(analysis)
        semantic = None
        if audio is not None:
            semantic = self._semantic_analyzer().analyze(audio)
        return self._classifier.classify(analysis, context, semantic)

    def _semantic_analyzer(self) -> Any:
        if self._intelligence is None:
            from phasenox.audio.intelligence import AudioIntelligenceAnalyzer

            self._intelligence = AudioIntelligenceAnalyzer()
        return self._intelligence
