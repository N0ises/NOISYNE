from __future__ import annotations

from phasenox.application.noisyne_service import (
    AnalysisRequest,
    AnalysisResponse,
    NoisyneService,
)

# Backward-compatible alias preserved for Phase 1.
SoundBrainService = NoisyneService

__all__ = [
    "AnalysisRequest",
    "AnalysisResponse",
    "NoisyneService",
    "SoundBrainService",
]
