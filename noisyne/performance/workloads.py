from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception.auditory import AuditoryFrontend
from noisyne.perception.descriptors import PerceptualDescriptorFoundation
from noisyne.perception.reference_contracts import (
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceProvenance,
    ReferenceRole,
    ReferenceTrackIdentity,
)
from noisyne.perception.reference_intelligence import ObjectiveReferenceComparator

from .contracts import PerformanceWorkload


def make_synthetic_audio(
    duration_seconds: float,
    sample_rate: int = 44100,
    channels: int = 1,
    frequency_hz: float = 440.0,
    amplitude: float = 0.5,
) -> AudioData:
    """Create deterministic synthetic audio for controlled benchmarking."""
    sample_count = int(duration_seconds * sample_rate)
    if sample_count <= 0:
        raise ValueError("duration must produce at least one sample")
    time = np.arange(sample_count, dtype=np.float64) / sample_rate
    mono = amplitude * np.sin(2.0 * np.pi * frequency_hz * time)
    if channels == 1:
        samples = mono[:, np.newaxis]
    else:
        samples = np.stack([mono] * channels, axis=1)
    if not np.all(np.isfinite(samples)):
        raise ValueError("synthetic audio must be finite")
    samples.setflags(write=False)
    metadata = AudioMetadata(
        path=Path("synthetic.wav"),
        filename="synthetic.wav",
        extension="wav",
        format="WAV",
        codec=None,
        sample_rate=sample_rate,
        channels=channels,
        duration=duration_seconds,
        bit_depth=24,
        file_size=samples.nbytes,
    )
    return AudioData(samples=samples, metadata=metadata)


def _auditory_workload(duration_seconds: float) -> PerformanceWorkload:
    return PerformanceWorkload(
        workload_id=f"auditory_frontend_{int(duration_seconds)}s",
        workload_type="auditory_frontend",
        description="Sprint 2 deterministic spectral/ERB frontend",
        duration_seconds=duration_seconds,
        sample_count=1,
        deterministic=True,
        limitations=["Synthetic sine input; not representative of full music content"],
    )


def _brightness_workload(duration_seconds: float) -> PerformanceWorkload:
    return PerformanceWorkload(
        workload_id=f"brightness_correlate_{int(duration_seconds)}s",
        workload_type="brightness_correlate",
        description="Sprint 5 power-spectral-centroid brightness correlate",
        duration_seconds=duration_seconds,
        sample_count=1,
        deterministic=True,
        limitations=["Brightness correlate only; not universal perceived brightness"],
    )


def _reference_workload(duration_seconds: float) -> PerformanceWorkload:
    return PerformanceWorkload(
        workload_id=f"reference_comparison_{int(duration_seconds)}s",
        workload_type="reference_comparison",
        description="Sprint 9 whole-programme objective reference comparison",
        duration_seconds=duration_seconds,
        sample_count=1,
        deterministic=True,
        limitations=["Identical source/reference; measures runtime overhead only"],
    )


class AuditoryFrontendWorkload:
    """Benchmarkable wrapper around the Sprint 2 auditory frontend."""

    def __init__(self, duration_seconds: float, sample_rate: int = 44100) -> None:
        self.workload = _auditory_workload(duration_seconds)
        self.audio = make_synthetic_audio(duration_seconds, sample_rate=sample_rate)
        self.engine = AuditoryFrontend()

    def run(self) -> Any:
        return self.engine.analyze(self.audio)


class BrightnessDescriptorWorkload:
    """Benchmarkable wrapper around the Sprint 5 brightness correlate."""

    def __init__(self, duration_seconds: float, sample_rate: int = 44100) -> None:
        self.workload = _brightness_workload(duration_seconds)
        self.audio = make_synthetic_audio(duration_seconds, sample_rate=sample_rate)
        self.engine = PerceptualDescriptorFoundation()

    def run(self) -> Any:
        return self.engine.analyze(self.audio)


class ReferenceComparisonWorkload:
    """Benchmarkable wrapper around the Sprint 9 reference comparator."""

    def __init__(self, duration_seconds: float, sample_rate: int = 44100) -> None:
        self.workload = _reference_workload(duration_seconds)
        self.source = make_synthetic_audio(duration_seconds, sample_rate=sample_rate)
        self.reference = make_synthetic_audio(duration_seconds, sample_rate=sample_rate)
        self.engine = ObjectiveReferenceComparator()
        self.reference_identity = ReferenceTrackIdentity(
            reference_id="synthetic_reference",
            version="1.0.0",
            display_name="Synthetic reference",
            provenance=ReferenceProvenance.USER_SUPPLIED,
            source="synthetic",
            sample_rate_hz=sample_rate,
            channel_count=1,
            duration_seconds=duration_seconds,
            declared_role=ReferenceRole.GENERAL_REFERENCE,
        )

    def run(self) -> Any:
        return self.engine.compare(
            self.source,
            self.reference,
            self.reference_identity,
            config=ReferenceComparisonConfig(mode=ReferenceComparisonMode.RAW_LEVEL),
        )


def build_workload_callables() -> dict[str, tuple[PerformanceWorkload, Callable[[], Any]]]:
    """Return a small set of short, deterministic NØISYNE workload callables.

    Only short-duration workloads are included here so that normal unit tests
    stay fast.  Longer benchmarks are available through the workload classes
    directly and should be run explicitly, not in CI.
    """
    auditory = AuditoryFrontendWorkload(10.0)
    brightness = BrightnessDescriptorWorkload(10.0)
    reference = ReferenceComparisonWorkload(10.0)
    return {
        auditory.workload.workload_id: (auditory.workload, auditory.run),
        brightness.workload.workload_id: (brightness.workload, brightness.run),
        reference.workload.workload_id: (reference.workload, reference.run),
    }


__all__ = [
    "AuditoryFrontendWorkload",
    "BrightnessDescriptorWorkload",
    "ReferenceComparisonWorkload",
    "build_workload_callables",
    "make_synthetic_audio",
]
