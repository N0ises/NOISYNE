from __future__ import annotations

from phasenox.application.phasenox_service import (
    AnalysisRequest,
    AnalysisResponse,
    PhasenoxService,
)

# Transitional R2 compatibility aliases. There is only one implementation.
NoisyneService = PhasenoxService
SoundBrainService = PhasenoxService

__all__ = [
    "AnalysisRequest",
    "AnalysisResponse",
    "NoisyneService",
    "PhasenoxService",
    "SoundBrainService",
]
