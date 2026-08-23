"""NØISYNE application service layer.

Sprint 15 exposes the V2 application surface directly. V1 services remain
available lazily via ``__getattr__`` so that importing ``phasenox.application``
does not initialize torch, ONNX, LLM clients, network, Qt, or audio devices.
"""

from __future__ import annotations

from phasenox.application.contracts import (
    APPLICATION_SCHEMA_VERSION,
    ApplicationError,
    ApplicationRequest,
    ApplicationResult,
    ApplicationResultStatus,
    CapabilitySnapshotEntry,
    CapabilitySnapshotResult,
    MachineAvailability,
    OperationType,
    StageOutcome,
    StageState,
)
from phasenox.application.errors import ApplicationErrorCode
from phasenox.application.service import NoisyneV2Service

__all__ = [
    "APPLICATION_SCHEMA_VERSION",
    "ApplicationError",
    "ApplicationErrorCode",
    "ApplicationRequest",
    "ApplicationResult",
    "ApplicationResultStatus",
    "CapabilitySnapshotEntry",
    "CapabilitySnapshotResult",
    "MachineAvailability",
    "NoisyneV2Service",
    "OperationType",
    "StageOutcome",
    "StageState",
]


def __getattr__(name: str):
    """Lazily re-export V1 service aliases without heavy imports."""
    if name in ("AnalysisRequest", "AnalysisResponse", "NoisyneService"):
        from phasenox.application import noisyne_service as _noisyne_service

        return getattr(_noisyne_service, name)
    if name == "SoundBrainService":
        from phasenox.application import soundbrain_service as _soundbrain_service

        return getattr(_soundbrain_service, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
