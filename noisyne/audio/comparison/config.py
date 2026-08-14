from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricRule:

    weight: float

    tolerance: float


METRIC_RULES = {

    "lufs": MetricRule(
        weight=15.0,
        tolerance=1.0,
    ),

    "peak": MetricRule(
        weight=15.0,
        tolerance=0.5,
    ),

    "rms": MetricRule(
        weight=8.0,
        tolerance=0.05,
    ),

    "dynamic_range": MetricRule(
        weight=12.0,
        tolerance=2.0,
    ),

    "crest_factor": MetricRule(
        weight=10.0,
        tolerance=2.0,
    ),

    "stereo_width": MetricRule(
        weight=10.0,
        tolerance=0.10,
    ),

    "phase": MetricRule(
        weight=12.0,
        tolerance=0.15,
    ),

    "spectral_centroid": MetricRule(
        weight=5.0,
        tolerance=400.0,
    ),

    "spectral_bandwidth": MetricRule(
        weight=3.0,
        tolerance=500.0,
    ),

    "spectral_rolloff": MetricRule(
        weight=3.0,
        tolerance=700.0,
    ),

    "spectral_flatness": MetricRule(
        weight=2.0,
        tolerance=0.002,
    ),

    "spectral_contrast": MetricRule(
        weight=2.0,
        tolerance=3.0,
    ),

    "zero_crossing_rate": MetricRule(
        weight=2.0,
        tolerance=0.02,
    ),

    "tempo": MetricRule(
        weight=1.0,
        tolerance=3.0,
    ),
}