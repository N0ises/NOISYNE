from __future__ import annotations

from noisyne.audio.context.models import AudioContext
from noisyne.audio.mix.models import MixIntelligenceResult

from .chain_builder import PluginChainBuilder
from .models import PluginIntelligenceResult
from .validator import PluginIntelligenceValidator


class PluginIntelligenceService:
    """Facade that composes the plugin chain builder and validator."""

    def __init__(
        self,
        chain_builder: PluginChainBuilder | None = None,
        validator: PluginIntelligenceValidator | None = None,
    ) -> None:
        if chain_builder is None:
            self._chain_builder = PluginChainBuilder()
        else:
            self._chain_builder = chain_builder

        if validator is None:
            self._validator = PluginIntelligenceValidator()
        else:
            self._validator = validator

    def analyze(
        self,
        mix_result: MixIntelligenceResult,
        context: AudioContext,
    ) -> PluginIntelligenceResult:
        result = self._chain_builder.build(mix_result, context)
        return self._validator.validate(result)
