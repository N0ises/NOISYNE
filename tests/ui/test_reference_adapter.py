from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from brain.ui.adapters.v1 import V1ApplicationAdapter
from brain.ui.contracts import ReferenceComparisonCommand


class FakeReferenceService:
    last_request = None

    def analyze(self, request):
        type(self).last_request = request
        metric = SimpleNamespace(
            name="loudness",
            current=-13.25,
            reference=-14.0,
            difference=0.75,
            unit="LUFS",
            tolerance=1.0,
            passed=True,
            severity="low",
            similarity=94.5,
        )
        band = SimpleNamespace(
            band="low",
            start_hz=20.0,
            end_hz=200.0,
            current_energy=1.2,
            reference_energy=1.0,
            difference_db=0.2,
            severity="info",
        )
        finding = SimpleNamespace(
            title="Low band",
            description="Current energy differs.",
            category="frequency",
            severity="medium",
            confidence=0.8,
            recommendation="Review low-band balance.",
            decision_type="technical_issue",
        )
        segment = SimpleNamespace(
            start_time=1.0,
            end_time=2.0,
            metric="loudness",
            current_value=-13.0,
            reference_value=-14.0,
            severity="low",
        )
        comparison = SimpleNamespace(
            similarity=88.75,
            confidence=0.91,
            frequency_score=80.0,
            dynamic_score=81.0,
            stereo_score=82.0,
            loudness_score=83.0,
            transient_score=84.0,
            phase_score=85.0,
            tonal_score=86.0,
            semantic_score=87.0,
            metrics=[metric],
            band_differences=[band],
            engineer_decisions=[finding],
            reference_similarities={"first.wav": 87.5, "second.wav": 90.0},
            metric_variance={"loudness": 0.125},
            segment_deviations=[segment],
        )
        return SimpleNamespace(status="ok", warnings=[], comparison=comparison)


def test_v1_reference_adapter_maps_real_multi_reference_contract(
    tmp_path, product_metadata
) -> None:
    output = tmp_path / "reports"
    output.mkdir()
    (output / "reference_report.json").write_text("{}", encoding="utf-8")
    (output / "reference_report.md").write_text("# Report", encoding="utf-8")
    references = (Path("first.wav"), Path("second.wav"))
    command = ReferenceComparisonCommand(
        Path("current.wav"),
        references,
        genre="electronic",
        mood="focused",
        target="streaming",
        focus_areas=("loudness", "stereo"),
        output_directory=output,
    )
    adapter = V1ApplicationAdapter(
        metadata=product_metadata,
        service_factory=FakeReferenceService,
    )

    result = adapter.compare_references(command)

    request = FakeReferenceService.last_request
    assert request.reference_path == list(references)
    assert request.reference_genre == "electronic"
    assert request.reference_mood == "focused"
    assert request.reference_target == "streaming"
    assert request.reference_focus == ["loudness", "stereo"]
    assert result.similarity == 88.75
    assert result.metrics[0].difference == 0.75
    assert result.metrics[0].unit == "LUFS"
    assert result.band_differences[0].difference_db == 0.2
    assert result.findings[0].recommendation == "Review low-band balance."
    assert result.segment_deviations[0].start_time == 1.0
    assert result.metric_variances[0].value == 0.125
    assert [item.format for item in result.reports] == ["json", "markdown"]


def test_v1_reference_adapter_preserves_graceful_warning(product_metadata) -> None:
    class DegradedService:
        def analyze(self, request):
            return SimpleNamespace(
                status="degraded",
                warnings=["Reference comparison failed: unavailable"],
                comparison=None,
            )

    adapter = V1ApplicationAdapter(
        metadata=product_metadata,
        service_factory=DegradedService,
    )

    result = adapter.compare_references(
        ReferenceComparisonCommand(Path("current.wav"), (Path("reference.wav"),))
    )

    assert result.similarity is None
    assert result.status == "degraded"
    assert result.warnings == ("Reference comparison failed: unavailable",)
