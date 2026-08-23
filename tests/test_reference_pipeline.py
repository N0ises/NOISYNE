from __future__ import annotations

from pathlib import Path

from phasenox.reference.models import (
    ReferenceComparison,
    ReferenceReport,
)
from phasenox.reference.pipeline import ReferencePipeline


class FakeEngine:

    def compare_files(
        self,
        reference_audio,
        current_audio,
        intent=None,
    ):

        comparison = ReferenceComparison(
            similarity=91.2,
            confidence=0.97,
            frequency_score=90,
            dynamic_score=89,
            stereo_score=95,
            loudness_score=88,
            transient_score=92,
            phase_score=96,
            tonal_score=91,
            semantic_score=90,
            band_differences=[],
            engineer_decisions=[],
            metrics=[],
        )

        return ReferenceReport(
            comparison=comparison,
            summary="Test",
            strengths=[],
            weaknesses=[],
            priorities=[],
            next_actions=[],
        )


class FakeReasoner:

    def reason(
        self,
        comparison,
        intent=None,
    ):
        return comparison


class FakeReportBuilder:

    def save_json(
        self,
        report,
        output,
    ):
        Path(output).write_text(
            "{}",
            encoding="utf-8",
        )

    def save_markdown(
        self,
        report,
        output,
    ):
        Path(output).write_text(
            "# Report",
            encoding="utf-8",
        )


def test_reference_pipeline(tmp_path: Path):

    pipeline = ReferencePipeline(
        engine=FakeEngine(),
        reasoner=FakeReasoner(),
        report_builder=FakeReportBuilder(),
    )

    output = tmp_path / "output"

    report = pipeline.run(
        "reference.wav",
        "mix.wav",
        output,
    )

    assert report.comparison.similarity == 91.2

    assert (output / "reference_report.json").exists()

    assert (output / "reference_report.md").exists()


def test_compare():

    pipeline = ReferencePipeline(
        engine=FakeEngine(),
        reasoner=FakeReasoner(),
        report_builder=FakeReportBuilder(),
    )

    report = pipeline.compare(
        "reference.wav",
        "mix.wav",
    )

    assert report.summary == "Test"


def test_compare_and_export(tmp_path: Path):

    pipeline = ReferencePipeline(
        engine=FakeEngine(),
        reasoner=FakeReasoner(),
        report_builder=FakeReportBuilder(),
    )

    output = tmp_path / "output2"

    report = pipeline.compare_and_export(
        "reference.wav",
        "mix.wav",
        output,
    )

    assert report.comparison.confidence == 0.97

    assert (output / "reference_report.json").exists()

    assert (output / "reference_report.md").exists()
