from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisResult:

    tempo: float

    pitch: float | str

    key: str

    lufs: float

    peak: float

    rms: float

    dynamic_range: float

    crest_factor: float

    stereo_width: float

    phase: float

    spectral_centroid: float

    spectral_bandwidth: float

    spectral_rolloff: float

    spectral_flatness: float

    spectral_contrast: float

    zero_crossing_rate: float

    mfcc: list[float]

    chroma: list[float]

    onset_count: int