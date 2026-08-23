"""Compatibility exports for the former V1 service module path.

The implementation lives in :mod:`phasenox.application.phasenox_service`.
"""

from __future__ import annotations

from phasenox.application.phasenox_service import (
    AnalysisRequest,
    AnalysisResponse,
    PhasenoxService,
)

NoisyneService = PhasenoxService

__all__ = [
    "AnalysisRequest",
    "AnalysisResponse",
    "NoisyneService",
    "PhasenoxService",
]
