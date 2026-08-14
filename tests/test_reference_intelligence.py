from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from noisyne.audio.analysis.models import AnalysisResult
from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.reference.models import (
    Category,
    DecisionType,
    EngineerDecision,
    ReferenceIntent,
    SegmentDeviation,
    Severity,
)
from noisyne.reference.reasoner import ReferenceReasoner
from noisyne.reference.service import ReferenceService

AUDIO_PATH = Path("tests/assets/test.wav")


def _analysis(
    *,
    lufs: float = -14.0,
    peak: float = -1.0,
    rms: float = -20.0,
) -> AnalysisResult:
    return AnalysisResult(
        tempo=120.0,
        pitch=440.0,
        key="C major",
        lufs=lufs,
        peak=peak,
        rms=rms,
        dynamic_range=8.0,
        crest_factor=10.0,
        stereo_width=0.8,
        phase=0.1,
        spectral_centroid=2000.0,
        spectral_bandwidth=1500.0,
        spectral_rolloff=8000.0,
        spectral_flatness=0.2,
        spectral_contrast=15.0,
        zero_crossing_rate=0.05,
        mfcc=[0.0] * 13,
        chroma=[0.0] * 12,
        onset_count=100,
    )


@dataclass
class FakeEngineeringEngine:

    def process(self, metrics):
        return type(
            "Result",
            (),
            {"recommendations": []},
        )()


@dataclass
class FakeAudioAnalyzer:

    results: dict[str, AnalysisResult]

    def analyze(self, audio: AudioData) -> AnalysisResult:
        return self.results[audio.metadata.filename]


def _audio_data(name: str = "audio.wav", duration: float = 10.0) -> AudioData:
    return AudioData(
        samples=None,
        metadata=AudioMetadata(
            path=Path("tests") / name,
            filename=name,
            extension="wav",
            format="wav",
            codec=None,
            sample_rate=44100,
            channels=2,
            duration=duration,
            bit_depth=16,
            file_size=1000,
        ),
    )


def test_multi_reference_computes_similarity_and_variance():
    ref_a = _analysis(lufs=-12.0, peak=-1.0)
    ref_b = _analysis(lufs=-10.0, peak=-2.0)
    ref_c = _analysis(lufs=-14.0, peak=-3.0)
    current = _analysis(lufs=-16.0, peak=-4.0)

    service = ReferenceService(
        analyzer=FakeAudioAnalyzer(
            {
                "reference_a.wav": ref_a,
                "reference_b.wav": ref_b,
                "reference_c.wav": ref_c,
                "current.wav": current,
            }
        ),
        engineering=FakeEngineeringEngine(),
    )

    report = service.compare_multiple(
        references=[
            _audio_data("reference_a.wav"),
            _audio_data("reference_b.wav"),
            _audio_data("reference_c.wav"),
        ],
        current=_audio_data("current.wav"),
        reference_paths=["reference_a.wav", "reference_b.wav", "reference_c.wav"],
    )

    assert report.comparison.references == [
        "reference_a.wav",
        "reference_b.wav",
        "reference_c.wav",
    ]
    assert len(report.comparison.reference_similarities) == 3
    assert all(0.0 <= sim <= 100.0 for sim in report.comparison.reference_similarities.values())

    lufs_metric = next(metric for metric in report.comparison.metrics if metric.name == "lufs")
    # With multi-reference aggregation the closest reference is used as the
    # primary comparison target. Current LUFS is -16.0; ref_c at -14.0 is closest.
    assert lufs_metric.reference == -14.0
    assert report.comparison.metric_variance["lufs"] > 0.0
    assert report.comparison.segment_deviations

    # The per-reference similarity map should report every reference.
    similarities = report.comparison.reference_similarities
    assert set(similarities.keys()) == {
        "reference_a.wav",
        "reference_b.wav",
        "reference_c.wav",
    }
    assert similarities["reference_c.wav"] == max(similarities.values())


def test_segment_deviation_structure_for_failed_metric():
    reference = _analysis(lufs=-14.0)
    current = _analysis(lufs=-22.0)

    service = ReferenceService(
        analyzer=FakeAudioAnalyzer(
            {
                "reference.wav": reference,
                "current.wav": current,
            }
        ),
        engineering=FakeEngineeringEngine(),
    )

    report = service.compare(
        reference=_audio_data("reference.wav", duration=15.0),
        current=_audio_data("current.wav", duration=15.0),
    )

    assert report.comparison.segment_deviations
    first = report.comparison.segment_deviations[0]
    assert isinstance(first, SegmentDeviation)
    assert first.start_time == 0.0
    assert first.end_time == 15.0
    assert first.metric
    assert first.severity


def test_reference_intent_categorization_with_focus_areas():
    reasoner = ReferenceReasoner()

    decision = EngineerDecision(
        title="Loudness Adjustment",
        description="LUFS differs.",
        category=Category.LOUDNESS,
        severity=Severity.MEDIUM,
        confidence=0.90,
        recommendation="Adjust limiter.",
    )

    intent = ReferenceIntent(
        genre="pop",
        target="streaming",
        focus_areas=["loudness"],
    )

    categorized = reasoner._categorize(decision, intent=intent)

    assert categorized.decision_type == DecisionType.STYLISTIC_DIFFERENCE
    assert categorized.confidence > decision.confidence


def test_reference_intent_categorization_without_focus():
    reasoner = ReferenceReasoner()

    decision = EngineerDecision(
        title="Phase Issue",
        description="Phase differs.",
        category=Category.PHASE,
        severity=Severity.HIGH,
        confidence=0.95,
        recommendation="Check mono.",
    )

    categorized = reasoner._categorize(decision, intent=None)

    assert categorized.decision_type == DecisionType.TECHNICAL_ISSUE


def test_low_confidence_decision_is_insufficient_evidence():
    reasoner = ReferenceReasoner()

    decision = EngineerDecision(
        title="Transient",
        description="Maybe different.",
        category=Category.TRANSIENT,
        severity=Severity.LOW,
        confidence=0.80,
        recommendation="Investigate.",
    )

    categorized = reasoner._categorize(decision, intent=None)

    assert categorized.decision_type == DecisionType.INSUFFICIENT_EVIDENCE


# Regression tests for V1 reference comparison stabilization

from noisyne.reference.comparator import ReferenceComparator
from noisyne.reference.report_builder import ReferenceReportBuilder


def test_reference_metric_includes_severity():
    comparator = ReferenceComparator()
    reference = {"lufs": -14.0}
    current = {"lufs": -22.0}

    comparison = comparator.compare_metrics(reference, current)

    assert comparison.metrics
    metric = comparison.metrics[0]
    assert metric.severity is not None
    assert metric.severity in (Severity.HIGH, Severity.CRITICAL)


def test_per_metric_tolerances_are_used():
    comparator = ReferenceComparator()
    reference = {"lufs": -14.0, "spectral_centroid": 2000.0}
    current = {"lufs": -14.5, "spectral_centroid": 2050.0}

    comparison = comparator.compare_metrics(reference, current)

    lufs = next(metric for metric in comparison.metrics if metric.name == "lufs")
    centroid = next(
        metric for metric in comparison.metrics if metric.name == "spectral_centroid"
    )

    assert lufs.tolerance == 1.0
    assert lufs.unit == "LU"
    assert lufs.passed is True

    assert centroid.tolerance == 100.0
    assert centroid.unit == "Hz"
    assert centroid.passed is True


def test_phase_tolerance_uses_normalized_scale():
    comparator = ReferenceComparator()
    reference = {"phase": 0.0}
    current = {"phase": 0.09}

    comparison = comparator.compare_metrics(reference, current)

    phase = next(metric for metric in comparison.metrics if metric.name == "phase")
    assert phase.tolerance == 0.1
    assert phase.unit == "normalized"
    assert phase.passed is True


def test_category_scores_use_category_means():
    comparator = ReferenceComparator()
    reference = {
        "lufs": -14.0,
        "peak": -1.0,
        "spectral_centroid": 2000.0,
    }
    current = {
        "lufs": -15.0,
        "peak": -1.5,
        "spectral_centroid": 3000.0,
    }

    comparison = comparator.compare_metrics(reference, current)

    # Tolerance-aware similarity:
    #   LUFS diff 1 / tolerance 1 -> normalized 1 -> similarity 50.
    #   peak diff 0.5 / tolerance 1 -> normalized 0.5 -> similarity 75.
    # Both are loudness, so loudness_score should be their mean: 62.5.
    assert comparison.loudness_score == 62.5
    # Spectral centroid diff 1000 / tolerance 100 -> normalized 10 -> similarity 0.
    assert comparison.frequency_score == 0.0


def test_report_builder_replaces_nonfinite_floats(tmp_path: Path):
    from noisyne.reference.models import ReferenceComparison, ReferenceReport

    comparison = ReferenceComparison(
        similarity=float("nan"),
        confidence=float("inf"),
        frequency_score=88.0,
        dynamic_score=87.0,
        stereo_score=90.0,
        loudness_score=86.0,
        transient_score=87.0,
        phase_score=92.0,
        tonal_score=88.0,
        semantic_score=85.0,
        band_differences=[],
        engineer_decisions=[],
        metrics=[],
    )
    report = ReferenceReport(
        comparison=comparison,
        summary="Test",
        strengths=[],
        weaknesses=[],
        priorities=[],
        next_actions=[],
    )

    output = tmp_path / "report.json"
    builder = ReferenceReportBuilder()
    builder.save_json(report, output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["comparison"]["similarity"] is None
    assert data["comparison"]["confidence"] is None
    assert data["comparison"]["frequency_score"] == 88.0


def test_similarity_is_tolerance_aware_at_boundary():
    """A difference exactly equal to tolerance must PASS with non-catastrophic similarity/severity."""
    comparator = ReferenceComparator()
    comparison = comparator.compare_metrics(
        reference={"lufs": -14.0},
        current={"lufs": -15.0},
    )

    metric = comparison.metrics[0]
    assert metric.passed is True
    assert metric.severity == Severity.LOW
    assert metric.similarity == pytest.approx(50.0)


def test_similarity_and_severity_beyond_tolerance():
    """A difference of 2x tolerance must FAIL with 0 similarity and elevated severity."""
    comparator = ReferenceComparator()
    comparison = comparator.compare_metrics(
        reference={"lufs": -14.0},
        current={"lufs": -16.0},
    )

    metric = comparison.metrics[0]
    assert metric.passed is False
    assert metric.severity == Severity.MEDIUM
    assert metric.similarity == pytest.approx(0.0)


def test_bpm_tolerance_aware():
    """BPM uses its own 1-BPM tolerance, not the universal raw scale."""
    comparator = ReferenceComparator()
    # Exactly at tolerance -> pass, similarity 50.
    comparison = comparator.compare_metrics(
        reference={"tempo": 120.0},
        current={"tempo": 121.0},
    )
    metric = comparison.metrics[0]
    assert metric.tolerance == 1.0
    assert metric.unit == "BPM"
    assert metric.passed is True
    assert metric.similarity == pytest.approx(50.0)
    assert metric.severity == Severity.LOW

    # Well within tolerance -> high similarity.
    comparison = comparator.compare_metrics(
        reference={"tempo": 120.0},
        current={"tempo": 120.5},
    )
    metric = comparison.metrics[0]
    assert metric.passed is True
    assert metric.similarity == pytest.approx(75.0)
    assert metric.severity == Severity.INFO


def test_hz_metric_tolerance_aware():
    """A Hz metric difference within tolerance should pass with reasonable similarity."""
    comparator = ReferenceComparator()
    comparison = comparator.compare_metrics(
        reference={"spectral_centroid": 2000.0},
        current={"spectral_centroid": 2050.0},
    )

    metric = comparison.metrics[0]
    assert metric.tolerance == 100.0
    assert metric.unit == "Hz"
    assert metric.passed is True
    assert metric.similarity == pytest.approx(75.0)
    assert metric.severity == Severity.INFO


def test_normalized_metric_tolerance_aware():
    """Normalized metrics (e.g., stereo_width) use their own small tolerance."""
    comparator = ReferenceComparator()
    comparison = comparator.compare_metrics(
        reference={"stereo_width": 0.5},
        current={"stereo_width": 0.54},
    )

    metric = comparison.metrics[0]
    assert metric.tolerance == 0.1
    assert metric.unit == "normalized"
    assert metric.passed is True
    assert metric.similarity == pytest.approx(80.0)
    assert metric.severity == Severity.INFO
